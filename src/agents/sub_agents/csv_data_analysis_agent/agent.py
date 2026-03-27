"""
CSV Data Analysis Agent

CSV 파일을 읽고, 데이터 분석 코드를 생성하고 실행하여 결과를 분석하는 LangGraph 기반 Agent

워크플로우:
1. CSV 파일 읽기 및 구조 파악
2. 데이터 분석 코드 생성 (LLM)
   - Human-in-the-Loop: 코드 생성 후 사용자 승인 요청
3. 생성된 코드 실행
   - Human-in-the-Loop: 코드 실행 전 사용자 승인 요청
4. 실행 결과 분석
5. 최종 분석 보고서 생성

Gemini CLI, Claude Code와 같은 접근 방식:
- 파일 읽기 → 코드 생성 → [승인] → 코드 실행 → [승인] → 결과 분석

Human-in-the-Loop 기능:
- 코드 생성 후 승인/수정/거부 가능
- 코드 실행 전 승인/거부 가능
- Checkpointer를 통한 상태 저장 및 재개
"""

import os
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.token_usage_tracker import TokenUsageTracker
from src.utils.errors import (
    ExecutionError,
    format_error_message,
    format_error_for_state,
    increment_error_count
)
from src.utils.paths import (
    get_project_root,
    get_data_directory,
    get_workspace_directory,
    get_workspace_subdirectories,
    resolve_data_file_path,
    get_docker_image_name,
)
from src.tools.csv_tools import read_csv_metadata_tool
from src.tools.filesystem import read_file_tool
# 새로운 통합 코드 실행 시스템 사용
from src.tools.code_execution import execute_code_in_docker
from src.tools.code_execution.utils import extract_context_from_result

# 코딩 에이전트 import (통합)
try:
    from ..code_generation_agent import create_code_generation_agent
    from ..code_generation_agent.state import CodeGenerationState
    CODE_GENERATION_AGENT_AVAILABLE = True
except ImportError:
    CODE_GENERATION_AGENT_AVAILABLE = False
    print("⚠️ 코딩 에이전트를 import할 수 없습니다. 기존 방식으로 코드 생성합니다.")

# 리팩토링: 유틸리티 모듈 import
from .utils import (
    # 파일 경로 처리
    normalize_csv_path,
    resolve_csv_file_paths,
    resolve_csv_files,
    find_csv_file,
    # 코드 전처리
    add_data_type_preprocessing,
    add_csv_filepath_variables,
    convert_host_paths_to_docker_paths,
    prepare_code_for_execution,
    # 파라미터 추출
    extract_natural_language_query_from_messages,
    extract_parameters_rule_based,
    extract_csv_parameters_from_messages,
    # 워크스페이스 관리
    setup_workspace_directories,
    save_code_to_workspace,
    move_code_file,
)

import re
import json
from pathlib import Path
from datetime import datetime


# CSV Data Analysis Agent State 정의
# MessagesState를 상속하여 LangGraph Studio에서 메시지 타입 선택 UI 제공
class CSVAnalysisState(MessagesState, total=False):
    """CSV Data Analysis Agent의 상태
    
    MessagesState를 상속하여 LangGraph Studio에서 메시지 타입(HUMAN, AI, SYSTEM, Tool, Function) 선택 UI 제공
    messages는 Required, 나머지 필드는 Optional
    
    필드 분류:
    - 사용자 입력 가능: CSV_file_path, query (messages에서 자동 추출 가능하지만 직접 제공도 가능)
    - 내부 전용 (제거 불가): 나머지 모든 필드 (내부 워크플로우에 필수)
    """
    
    # ========== 사용자 입력 가능 (Optional, messages에서 자동 추출 가능) ==========
    CSV_file_path: Optional[str]  # CSV 파일 경로 (단일 파일 모드, 하위 호환성)
    CSV_file_paths: Optional[List[str]]  # CSV 파일 경로 목록 (다중 파일 모드)
    query: Optional[str]  # 사용자 요청 (고급 사용자용 직접 입력)
    
    # ========== 내부 워크플로우용 (제거 불가, 내부에서 자동 생성/사용) ==========
    CSV_metadata: Optional[str]  # CSV 메타데이터 (단일 파일 또는 통합 메타데이터)
    CSV_metadata_dict: Optional[Dict[str, str]]  # [사용 중단] CSV_metadata에 통합되어 더 이상 저장하지 않음 (토큰 절약을 위해 중복 제거)
    generated_code: Optional[str]  # 생성된 분석 코드 (내부 생성, 파일 저장 전)
    generated_code_file: Optional[str]  # 생성된 코드 파일 경로 (Phase 1)
    executed_code_file: Optional[str]  # 실행 완료된 코드 파일 경로 (Phase 1)
    environment_validated: Optional[bool]  # 환경 검증 완료 여부 (Phase 3 이전)
    environment_validation_result: Optional[str]  # 환경 검증 결과 (Phase 3 이전)
    execution_result: Optional[str]  # 코드 실행 결과 (내부 생성)
    docker_execution_result: Optional[Dict[str, Any]]  # 도커 실행 결과 (상세 정보)
    docker_session_id: Optional[str]  # Docker 세션 ID (하위 호환성용, 현재 사용되지 않음)
    analysis_result: Optional[str]  # 실행 결과 분석 (내부 생성, generate_final_report에 통합 예정)
    final_report: Optional[str]  # 최종 보고서 (내부 생성, 결과 반환용)
    
    # ========== 반복적 분석을 위한 필드 (Phase 1 개선) ==========
    analysis_iteration_count: Optional[int]  # 분석 반복 횟수 (기본값: 0)
    max_analysis_iterations: Optional[int]  # 최대 분석 반복 횟수 (기본값: 3)
    execution_result_valid: Optional[bool]  # 실행 결과 유효성 검증 결과
    retry_needed: Optional[bool]  # 재시도 필요 여부
    retry_reason: Optional[str]  # 재시도 이유
    next_action: Optional[str]  # 다음 액션 ("continue_analysis", "clean_data", "visualize", "generate_report")
    insights: Optional[List[str]]  # 발견된 인사이트 목록
    accumulated_insights: Optional[List[str]]  # 누적된 인사이트 목록
    suggestions: Optional[str]  # 다음 분석 제안 (analyze_execution_result에서 생성)
    code_syntax_valid: Optional[bool]  # 코드 문법 검증 결과
    syntax_errors: Optional[List[str]]  # 문법 오류 목록
    
    # ========== CodeGeneration Agent 통합 필드 (Subgraph 통합용) ==========
    # CodeGenerationState의 필드를 통합하여 subgraph로 직접 사용 가능하도록 함
    task_description: Optional[str]  # 보강된 프롬프트 (Orchestrator가 생성, CSV 분석 에이전트 내부 및 CodeGeneration Agent에 전달, requirements로 자동 사용됨)
    requirements: Optional[str]  # [사용 중단] 필드 제거됨 (CodeGeneration Agent의 analyze_requirements_node가 task_description을 requirements로 자동 사용)
    context: Optional[Dict[str, Any]]  # 컨텍스트 (도메인별: csv_analysis 등)
    
    # Planning (작업 계획 수립)
    planning_result: Optional[str]  # Planning Tool 결과 (JSON 형식)
    planning_todos: Optional[List[Dict[str, Any]]]  # Todo 리스트
    current_subtask: Optional[int]  # 현재 진행 중인 하위 작업 인덱스
    
    # 동적 작업 추적: 작업 제목 및 설명 (자가 주도적 워크플로우)
    current_task_title: Optional[str]  # 현재 작업 제목 (예: "DESeq2 데이터 필터링 및 기본 분석")
    current_task_description: Optional[str]  # 현재 작업 설명 (예: "데이터 구조를 확인했습니다. 이제 padj < 0.05 및 |log2FoldChange| > 1 조건으로 DEG를 필터링하고 분석해보겠습니다.")
    task_history: Optional[List[Dict[str, Any]]]  # 작업 이력 [{"title": "...", "description": "...", "iteration": 1, "planning_todos": [...]}, ...]
    analysis_stage: Optional[int]  # 현재 분석 단계 (1-4)
    stage_name: Optional[str]  # 단계 이름 (예: "데이터 구조 확인")
    
    # Filesystem (파일 관리)
    files_created: Optional[List[str]]  # 생성된 파일 목록
    files_edited: Optional[List[str]]  # 편집된 파일 목록
    files_read: Optional[List[str]]  # 읽은 파일 목록
    
    # 코드 검증 (CodeGeneration Agent와 공유)
    code_valid: Optional[bool]  # 코드 유효성
    validation_errors: Optional[List[str]]  # 검증 오류 목록
    auto_fixed: Optional[bool]  # 프로그램으로 자동 수정 성공 여부
    
    # 코드 실행 (CodeGeneration Agent와 공유)
    execution_errors: Optional[List[str]]  # 실행 오류 목록
    
    # 코드 수정
    fixed_code: Optional[str]  # 수정된 코드
    fix_iterations: Optional[int]  # 수정 반복 횟수
    previous_fix_errors: Optional[List[str]]  # 이전 수정 시 발견된 오류 목록
    
    # CodeGeneration Agent 제어 및 상태 추적
    target_filepath: Optional[str]  # 목표 파일 경로 (Planning 기반)
    max_iterations: Optional[int]  # 최대 반복 횟수 (기본값: 3)
    tool_call_count: Optional[int]  # Tool 호출 횟수 (통계/디버깅용)
    
    # ========== 내부 상태 추적/디버깅용 (제거 불가, 내부 상태 관리) ==========
    status: Optional[str]  # 현재 워크플로우 상태 (디버깅/추적용)
    errors: Optional[List[str]]  # 에러 목록 (에러 처리용)
    error_count: Optional[int]  # 연속 에러 발생 횟수 (3회 이상 시 interrupt 호출)
    call_count: Optional[int]  # LLM 호출 횟수 (통계/디버깅용)
    code_approved: Optional[bool]  # 코드 승인 여부 (Human-in-the-Loop 내부 상태)
    execution_approved: Optional[bool]  # 실행 승인 여부 (Human-in-the-Loop 내부 상태)
    token_usage: Optional[Dict[str, Any]]  # 토큰 사용량 정보


# ========== 동적 작업 추적: 헬퍼 함수 ==========

def extract_task_title(response_text: str) -> str:
    """응답에서 작업 제목 추출 (동적 작업 추적)
    
    Args:
        response_text: LLM 응답 텍스트
        
    Returns:
        추출된 작업 제목
    """
    # 따옴표 제거
    title = response_text.strip().strip('"').strip("'")
    
    # 여러 줄인 경우 첫 번째 줄만 사용
    title = title.split('\n')[0].strip()
    
    # 작업 제목: 로 시작하는 경우 제거
    if title.startswith("작업 제목:"):
        title = title.replace("작업 제목:", "").strip()
    
    return title


# ========== Workspace 디렉토리 관리 함수 ==========
# 리팩토링: 워크스페이스 관리 함수는 utils/workspace.py로 이동됨


# ========== Workspace 디렉토리 관리 함수 ==========
# 리팩토링: 워크스페이스 관리 함수는 utils/workspace.py로 이동됨
# 리팩토링: 코드 전처리 함수들은 utils/code_processing.py로 이동됨


def _validate_environment_for_pandas_analysis() -> Dict[str, Any]:
    """Docker 이미지 환경에서 pandas 분석 가능 여부 확인
    
    Docker 이미지(csv-sandbox:test) 내부의 패키지 설치 상태를 확인합니다.
    
    Returns:
        검증 결과 딕셔너리
    """
    validation_result = {
        "success": False,
        "packages": {},
        "test_result": None,
        "errors": [],
        "docker_image": None,
        "docker_available": False
    }
    
    # 필수 패키지 목록
    required_packages = {
        "pandas": "데이터 분석",
        "numpy": "수치 연산",
        "matplotlib": "시각화",
        "seaborn": "고급 시각화"
    }
    
    # Docker 이미지 이름 가져오기
    from src.utils.paths import get_docker_image_name
    docker_image = get_docker_image_name()
    validation_result["docker_image"] = docker_image
    
    print(f"🔍 [Environment Validation] Docker 이미지 환경 검증 중... (이미지: {docker_image})")
    
    # Docker Python SDK 사용
    try:
        import docker
        client = docker.from_env()
        client.ping()
        validation_result["docker_available"] = True
        print(f"  ✅ Docker 연결 성공")
    except ImportError:
        validation_result["errors"].append("docker 모듈이 설치되지 않았습니다. 'pip install docker'로 설치하세요.")
        print(f"  ❌ docker 모듈 없음")
        return validation_result
    except Exception as e:
        validation_result["errors"].append(f"Docker 연결 실패: {str(e)}")
        validation_result["errors"].append("Docker 데몬이 실행 중인지 확인하세요.")
        print(f"  ❌ Docker 연결 실패: {str(e)}")
        return validation_result
    
    # Docker 이미지 존재 여부 확인
    try:
        client.images.get(docker_image)
        print(f"  ✅ Docker 이미지 확인: {docker_image}")
    except docker.errors.ImageNotFound:
        validation_result["errors"].append(f"Docker 이미지 '{docker_image}'를 찾을 수 없습니다.")
        validation_result["errors"].append(f"다음 명령으로 이미지를 빌드하세요: docker build -t {docker_image} -f tests/Dockerfile.sandbox tests/")
        print(f"  ❌ Docker 이미지 없음: {docker_image}")
        return validation_result
    
    # Docker 컨테이너에서 패키지 확인
    print(f"  🔍 Docker 컨테이너에서 패키지 확인 중...")
    
    for package_name, description in required_packages.items():
        try:
            # Docker 컨테이너에서 패키지 버전 확인
            check_command = f"python -c \"import {package_name}; print({package_name}.__version__)\""
            result = client.containers.run(
                docker_image,
                check_command,
                remove=True,
                stderr=True,
                stdout=True,
            )
            
            stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            version = stdout.strip()
            
            validation_result["packages"][package_name] = {
                "installed": True,
                "version": version,
                "description": description
            }
            print(f"  ✅ {package_name} {version} 설치됨 (Docker 이미지)")
        except docker.errors.ContainerError as e:
            # 패키지가 없거나 import 실패
            stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else str(e)
            validation_result["packages"][package_name] = {
                "installed": False,
                "version": None,
                "description": description
            }
            validation_result["errors"].append(f"{package_name}이(가) Docker 이미지에 설치되지 않았습니다.")
            print(f"  ❌ {package_name} 설치되지 않음 (Docker 이미지): {stderr[:100]}")
        except Exception as e:
            validation_result["packages"][package_name] = {
                "installed": False,
                "version": None,
                "description": description
            }
            validation_result["errors"].append(f"{package_name} 확인 중 오류: {str(e)}")
            print(f"  ⚠️ {package_name} 확인 실패: {str(e)}")
    
    # pandas가 설치되어 있으면 간단한 테스트 실행
    if validation_result["packages"].get("pandas", {}).get("installed", False):
        try:
            # 테스트 코드를 파일로 저장하여 실행 (따옴표 문제 방지)
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
                test_code = """import pandas as pd
import numpy as np

# 간단한 테스트 데이터 생성
df = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50]
})

# 기본 연산 테스트
result = df['A'].sum()
print(f"✅ Pandas 기본 연산 테스트 성공: {result}")

# CSV 읽기 시뮬레이션 (실제 파일 없이)
from io import StringIO
test_csv = "col1,col2\\n1,2\\n3,4"
df_test = pd.read_csv(StringIO(test_csv))
print(f"✅ CSV 읽기 테스트 성공: {len(df_test)} 행")
"""
                tmp_file.write(test_code)
                tmp_file_path = tmp_file.name
            
            # 임시 파일을 Docker 컨테이너에 마운트하여 실행
            result = client.containers.run(
                docker_image,
                f"python /tmp/test_validation.py",
                volumes={tmp_file_path: {"bind": "/tmp/test_validation.py", "mode": "ro"}},
                remove=True,
                stderr=True,
                stdout=True,
            )
            
            # 임시 파일 삭제
            import os
            os.unlink(tmp_file_path)
            
            stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            if "✅" in stdout and "성공" in stdout:
                validation_result["test_result"] = "success"
                validation_result["success"] = True
                print("  ✅ 환경 테스트 통과 (Docker 이미지)")
            else:
                validation_result["test_result"] = f"테스트 실행 실패: {stdout}"
                validation_result["errors"].append(f"환경 테스트 실패: {stdout[:200]}")
                print(f"  ⚠️ 환경 테스트 결과: {stdout[:100]}...")
        except docker.errors.ContainerError as e:
            stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else str(e)
            validation_result["test_result"] = f"테스트 실행 실패: {stderr}"
            validation_result["errors"].append(f"테스트 실행 중 오류: {stderr[:200]}")
            print(f"  ❌ 테스트 실행 실패: {stderr[:100]}")
        except Exception as e:
            validation_result["test_result"] = f"테스트 실행 실패: {str(e)}"
            validation_result["errors"].append(f"테스트 실행 중 오류: {str(e)}")
            print(f"  ❌ 테스트 실행 실패: {str(e)}")
    else:
        validation_result["errors"].append("pandas가 Docker 이미지에 설치되지 않아 테스트를 실행할 수 없습니다.")
    
    # 결과 요약
    if validation_result["success"]:
        print(f"✅ Docker 이미지 환경 검증 완료: pandas 분석 가능 ({docker_image})")
    else:
        print(f"⚠️ Docker 이미지 환경 검증 실패: 일부 패키지가 없거나 테스트 실패 ({docker_image})")
        if validation_result["errors"]:
            print("  오류:")
            for error in validation_result["errors"]:
                print(f"    - {error}")
    
    return validation_result


# 리팩토링: 파라미터 추출 함수들은 utils/parameter_extraction.py로 이동됨
# 리팩토링: 파일 경로 정규화 함수는 utils/file_path.py로 이동됨

# 기존 함수들은 모두 utils/ 모듈로 이동되었습니다.


def create_csv_data_analysis_agent(
    model: str = "ollama:gpt-oss:120b-cloud",
    code_generation_model: str = "ollama:codegemma:latest",
    enable_hitl: bool = True
):
    """CSV Data Analysis Agent 생성
    
    Orchestrator-Worker 패턴:
    - Orchestrator (상위 LLM): GPT-OSS - 메타데이터 분석, 프롬프트 향상, 최종 보고서 생성
    - Worker (하위 LLM): CodeGemma - 코드 생성만 담당
    
    Args:
        model: Orchestrator 모델 (프롬프트 향상, 보고서 작성) - 기본값: gpt-oss:120b-cloud
        code_generation_model: Worker 모델 (코드 생성) - 기본값: codegemma:latest
        enable_hitl: Human-in-the-Loop 활성화 여부 (기본값: True)
        
    Returns:
        LangGraph CompiledStateGraph (Checkpointer 포함)
    """
    # 환경변수 로드
    load_dotenv()
    
    # LangSmith 비활성화
    setup_langsmith_disabled()
    
    # API 키 가져오기
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    if not ollama_api_key:
        raise ValueError(
            "OLLAMA_API_KEY가 환경변수에 설정되지 않았습니다. "
            ".env 파일에 OLLAMA_API_KEY를 설정하세요."
        )
    
    # 모델 이름 정규화
    model = model.strip() if model else "ollama:gpt-oss:120b-cloud"
    code_generation_model = code_generation_model.strip() if code_generation_model else "ollama:codegemma:latest"
    
    if not model.startswith("ollama:"):
        model = f"ollama:{model}"
    if not code_generation_model.startswith("ollama:"):
        code_generation_model = f"ollama:{code_generation_model}"
    
    # Orchestrator 모델 초기화 (상위 LLM: 프롬프트 향상, 보고서 작성)
    orchestrator_model = init_chat_model_helper(
        model_name=model,
        api_key=ollama_api_key,
        temperature=0.7
    )
    
    if not orchestrator_model:
        raise ValueError(f"Orchestrator 모델 초기화 실패: {model}")
    
    print(f"✅ Orchestrator 모델 로드 완료: {model}")
    
    # 코딩 에이전트 생성 (코드 생성 위임)
    code_generation_agent = None
    worker_model = None  # 폴백용
    
    if CODE_GENERATION_AGENT_AVAILABLE:
        try:
            code_generation_agent = create_code_generation_agent(
                enable_planning=True,  # Planning Tool 활성화: Orchestrator의 전략적 계획을 구체적 플랜으로 변환
                enable_filesystem_tools=True,  # 파일 저장 필요
                enable_execution=False  # CSV agent의 execute_code를 사용하므로 비활성화
            )
            print("✅ 코딩 에이전트 생성 완료 (Subgraph로 통합, Planning Tool 활성화, Execution 비활성화)")
        except Exception as e:
            import traceback
            print(f"⚠️ 코딩 에이전트 생성 실패: {str(e)}")
            print("   상세 에러:")
            traceback.print_exc()
            print("   기존 방식(Worker 모델 직접 사용)으로 폴백합니다.")
            code_generation_agent = None
    
    # Worker 모델 초기화 (폴백용 또는 코딩 에이전트 사용 불가 시)
    if code_generation_agent is None:
        worker_model = init_chat_model_helper(
            model_name=code_generation_model,
            api_key=ollama_api_key,
            temperature=0.3  # 코드 생성은 낮은 temperature
        )
        
        if not worker_model:
            raise ValueError(f"Worker 모델 초기화 실패: {code_generation_model}")
        
        print(f"✅ Worker 모델 로드 완료: {code_generation_model} (폴백 모드)")
    
    # 하위 호환성을 위해 기존 변수명 유지 (내부에서 사용)
    main_chat_model = orchestrator_model
    code_chat_model = worker_model  # 폴백용 또는 None
    
    # Checkpointer 생성 (Human-in-the-Loop을 위해 필수)
    # LangGraph Studio (`langgraph dev`)에서는 자동으로 persistence를 처리하므로
    # 커스텀 checkpointer를 제공하면 에러가 발생함
    # 따라서 LangGraph Studio 환경에서는 checkpointer를 None으로 설정
    
    # LangGraph Studio 환경 감지
    # langgraph dev로 실행될 때는 langgraph_api 모듈이 로드되어 있음
    is_langgraph_studio = False
    try:
        import sys
        # 방법 1: sys.modules에서 langgraph_api 확인
        if "langgraph_api" in sys.modules:
            is_langgraph_studio = True
        # 방법 2: 환경 변수 확인
        if os.getenv("LANGGRAPH_API") or os.getenv("LANGGRAPH_STUDIO"):
            is_langgraph_studio = True
        # 방법 3: 실행 인자 확인 (langgraph dev)
        if any("langgraph" in str(arg).lower() for arg in sys.argv):
            is_langgraph_studio = True
    except Exception:
        pass
    
    if is_langgraph_studio:
        # LangGraph Studio 환경에서는 checkpointer를 사용하지 않음 (자동 처리됨)
        checkpointer = None
        print("⚠️  LangGraph Studio 환경 감지: 커스텀 checkpointer 비활성화 (자동 persistence 사용)")
        print("   Human-in-the-Loop은 LangGraph Studio의 자동 persistence를 통해 지원됩니다.")
    else:
        # 일반 Python 실행 환경에서는 checkpointer 사용
        checkpointer = MemorySaver() if enable_hitl else None
        if checkpointer:
            print("✅ Checkpointer 활성화 (Human-in-the-Loop 지원)")
    
    # 노드 함수들 정의 (Phase 3: 노드 분리)
    from .nodes import (
        create_validate_environment_node,
        create_read_csv_metadata_node,
    )
    
    # 노드 생성 (의존성 주입)
    validate_environment_node = create_validate_environment_node()
    read_csv_metadata_node = create_read_csv_metadata_node(orchestrator_model)
    
    # 나머지 노드들은 아직 분리 전이므로 기존 코드 유지
    # Phase 3 진행 중: 점진적으로 분리 예정
    
    def augment_prompt_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """프롬프트 보강 노드: Orchestrator가 메타데이터를 분석하고 향상된 프롬프트 생성
        
        단일 파일 또는 여러 파일을 지원합니다.
        Orchestrator (상위 LLM)가 Worker (하위 LLM)에게 전달할 job을 생성합니다.
        도커 환경에 설치된 패키지만 사용하도록 지시합니다.
        """
        print("🔍 [Augment Prompt] 프롬프트 보강 중... (Orchestrator: GPT-OSS)")
        
        CSV_metadata = state.get("CSV_metadata", "")
        query = state.get("query", "")
        CSV_file_path = state.get("CSV_file_path", "")
        CSV_file_paths = state.get("CSV_file_paths", [])
        environment_validation_result = state.get("environment_validation_result", "")
        
        # Phase 1 개선: 반복적 분석을 위한 컨텍스트 추가
        analysis_iteration_count = state.get("analysis_iteration_count", 0)
        accumulated_insights = state.get("accumulated_insights", [])
        previous_execution_result = state.get("execution_result", "")
        analysis_result = state.get("analysis_result", "")
        retry_reason = state.get("retry_reason", "")
        suggestions = state.get("suggestions", "")
        
        if not CSV_metadata:
            return {
                "errors": ["CSV 메타데이터가 없습니다. 먼저 메타데이터를 읽어주세요."],
                "status": "error"
            }
        
        # 동적 작업 추적: 작업 제목 및 설명 생성 (LLM 기반 동적 결정)
        task_history = state.get("task_history", [])
        task_title = None
        task_description_text = None
        user_message = None
        
        try:
            from .prompts import (
                ORCHESTRATOR_SYSTEM_PROMPT,
                create_orchestrator_user_prompt,
                create_task_title_prompt,
                create_task_description_prompt
            )
            
            # 작업 제목 생성
            print("📝 [동적 작업 추적] 작업 제목 생성 중...")
            title_prompt = create_task_title_prompt(
                csv_metadata=CSV_metadata[:1000] if CSV_metadata else "",
                previous_results=previous_execution_result,
                query=query,
                iteration_count=analysis_iteration_count,
                task_history=task_history
            )
            
            title_response = orchestrator_model.invoke([
                SystemMessage(content="당신은 데이터 분석 작업의 제목을 정의하는 전문가입니다. 데이터 타입과 이전 결과를 분석하여 적절한 작업 제목을 생성하세요."),
                HumanMessage(content=title_prompt)
            ], config={"callbacks": [TokenUsageTracker().get_callback()]})
            
            task_title = extract_task_title(title_response.content if hasattr(title_response, 'content') else str(title_response))
            print(f"✅ 작업 제목 생성 완료: {task_title}")
            
            # 작업 설명 생성
            print("📝 [동적 작업 추적] 작업 설명 생성 중...")
            description_prompt = create_task_description_prompt(
                task_title=task_title,
                csv_metadata=CSV_metadata[:1000] if CSV_metadata else "",
                previous_results=previous_execution_result,
                query=query,
                iteration_count=analysis_iteration_count
            )
            
            description_response = orchestrator_model.invoke([
                SystemMessage(content="당신은 데이터 분석 작업을 사용자에게 설명하는 전문가입니다. 작업 제목과 이전 결과를 바탕으로 자연스럽고 명확한 설명을 생성하세요."),
                HumanMessage(content=description_prompt)
            ], config={"callbacks": [TokenUsageTracker().get_callback()]})
            
            task_description_text = description_response.content if hasattr(description_response, 'content') else str(description_response)
            print(f"✅ 작업 설명 생성 완료: {task_description_text[:100]}...")
            
            # 작업 이력 업데이트
            task_history.append({
                "title": task_title,
                "description": task_description_text,
                "iteration": analysis_iteration_count + 1,
                "planning_todos": []  # 나중에 Planning 결과로 채워짐
            })
            
            # 사용자에게 메시지 전달
            user_message = AIMessage(
                content=f"{task_description_text}\n\n**작업**: {task_title}"
            )
            
        except ImportError as e:
            print(f"⚠️ 동적 작업 추적 프롬프트 import 실패: {e}")
        except Exception as e:
            print(f"⚠️ 동적 작업 추적 작업 제목/설명 생성 실패: {e}")
            # 실패해도 계속 진행 (선택적 기능)
        
        # Orchestrator가 메타데이터를 분석하고 향상된 프롬프트 생성
        # 프롬프트를 별도 모듈에서 가져옴 (프롬프트 분리)
        try:
            from .prompts import (
                ORCHESTRATOR_SYSTEM_PROMPT,
                create_orchestrator_user_prompt
            )
            system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
            # 여러 파일 모드 또는 단일 파일 모드
            if CSV_file_paths and len(CSV_file_paths) > 1:
                user_prompt = create_orchestrator_user_prompt(
                    csv_file_paths=CSV_file_paths,
                    csv_metadata=CSV_metadata,
                    query=query,
                    environment_info=environment_validation_result
                )
            else:
                file_path = CSV_file_paths[0] if CSV_file_paths else CSV_file_path
                user_prompt = create_orchestrator_user_prompt(
                    csv_file_path=file_path,
                    csv_metadata=CSV_metadata,
                    query=query,
                    environment_info=environment_validation_result
                )
        except ImportError:
            # 폴백: 기존 하드코딩된 프롬프트 사용
            system_prompt = """당신은 데이터 분석 전문가이자 작업 관리자(Orchestrator)입니다. 
CSV 파일의 메타데이터를 분석하고, 사용자의 요청에 맞는 향상된 코드 생성 프롬프트를 작성하세요.

**당신의 역할:**
1. CSV 메타데이터를 분석하여 데이터 구조 파악
   - 컬럼 타입, 데이터 크기, 통계 정보 분석
   - 데이터의 특성과 패턴 파악

2. 사용자 요청을 분석하여 필요한 분석 방법 파악
   - 요청의 의도 파악
   - 필요한 분석 기법 제안

3. **중요: 도커 환경에 설치된 패키지만 사용하도록 지시**
   - 환경 검증 결과에서 설치된 패키지 목록 확인
   - 설치된 패키지만 사용하여 분석 방법 제안
   - 설치되지 않은 패키지(sklearn, scipy 등)는 절대 사용하지 말 것

4. 코드 생성 Worker에게 전달할 구체적인 작업 지시사항 작성
   - 컬럼 타입에 따른 분석 방법 제안 (설치된 패키지로만)
   - 데이터 크기 고려한 최적화 제안
   - 구체적인 코드 생성 가이드라인 제공
   - **반드시 설치된 패키지만 import하고 사용하도록 명시**

**출력 형식:**
코드 생성 Worker가 바로 사용할 수 있도록 구체적이고 명확한 프롬프트를 작성하세요.
프롬프트에는 다음이 포함되어야 합니다:
- 데이터 구조 요약
- 분석 목표
- **설치된 패키지 목록 및 사용 가능한 분석 방법**
- 필요한 분석 방법 (설치된 패키지로만)
- 코드 생성 가이드라인 (설치된 패키지만 사용하도록 명시)"""

            user_prompt = f"""CSV 파일 정보:
파일 경로: {CSV_file_path}

CSV 메타데이터:
{CSV_metadata}

사용자 요청:
{query}

도커 환경 정보:
{environment_validation_result if environment_validation_result else "기본 패키지 (pandas, numpy, matplotlib, seaborn) 사용 가능"}

**중요 제약사항:**
- 도커 환경에 설치된 패키지만 사용 가능
- 설치되지 않은 패키지(sklearn, scipy 등)는 절대 사용하지 마세요
- 설치된 패키지만 import하고 사용하도록 코드를 생성하세요

위 정보를 바탕으로 코드 생성 Worker에게 전달할 향상된 프롬프트를 생성하세요.
이 프롬프트는 Worker가 데이터 분석 코드를 생성하는 데 필요한 모든 정보를 포함해야 합니다.
**반드시 설치된 패키지만 사용하여 분석 방법을 제안하세요.**"""

        try:
            # 토큰 추적 추가
            tracker = TokenUsageTracker()
            callback = tracker.get_callback()
            
            response = orchestrator_model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ], config={"callbacks": [callback]})
            
            # 토큰 사용량 업데이트
            current_token_usage = state.get("token_usage", {})
            if not current_token_usage:
                current_token_usage = {
                    "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    "by_model": {}
                }
            updated_token_usage = tracker.update_token_usage(
                current_token_usage,
                response if isinstance(response, AIMessage) else AIMessage(content=response.content if hasattr(response, 'content') else str(response)),
                model_name=model
            )
            
            task_description = response.content if hasattr(response, 'content') else str(response)
            
            # Phase 1 개선: 반복적 분석 시 이전 인사이트와 제안 반영
            if analysis_iteration_count > 0:
                print(f"🔄 반복 분석 ({analysis_iteration_count}회차) - 이전 인사이트 반영 중...")
                
                # 이전 인사이트 추가
                if accumulated_insights:
                    insights_context = "\n\n이전 분석에서 발견된 인사이트:\n" + "\n".join([f"- {insight}" for insight in accumulated_insights])
                    task_description += insights_context
                
                # 재시도 이유 및 제안 추가
                if retry_reason:
                    task_description += f"\n\n⚠️ 이전 분석 문제점: {retry_reason}\n이 문제를 해결하는 코드를 생성하세요."
                
                if suggestions:
                    task_description += f"\n\n💭 다음 분석 제안: {suggestions}\n이 제안을 반영하여 더 깊이 있는 분석을 수행하세요."
                
                if previous_execution_result:
                    task_description += f"\n\n이전 실행 결과 (참고용):\n{previous_execution_result[:500]}..."
                
                task_description += "\n\n이전 분석 결과를 바탕으로 더 깊이 있고 의미 있는 분석을 수행하세요."
            
            print(f"✅ 프롬프트 보강 완료 ({len(task_description)} 문자)")
            if analysis_iteration_count > 0:
                print(f"🔄 반복 분석 모드: {analysis_iteration_count}회차")
            print(f"📋 생성된 프롬프트 미리보기: {task_description[:200]}...")
            
            # CodeGeneration Agent subgraph 통합을 위한 상태 매핑
            # task_description으로 통일 (중복 제거)
            context_dict = {
                "domain": "csv_analysis",
                "csv_file_path": CSV_file_path,
                "csv_file_paths": CSV_file_paths,
                "csv_metadata": CSV_metadata,
                "query": query,
                "environment_validation_result": environment_validation_result
            }
            
            result = {
                "task_description": task_description,  # 통일된 필드명 사용 (CSV 분석 에이전트 내부 및 CodeGeneration Agent 공통)
                # requirements 필드 제거: CodeGeneration Agent의 analyze_requirements_node가 task_description을 requirements로 자동 사용
                "context": context_dict,  # CodeGeneration Agent용
                "status": "prompt_augmented",
                "call_count": state.get("call_count", 0) + 1,
                "token_usage": updated_token_usage,
                # 동적 작업 추적: 작업 제목 및 설명 추가
                "current_task_title": task_title,
                "current_task_description": task_description_text,
                "task_history": task_history
            }
            
            # 사용자 메시지가 있으면 추가
            if user_message:
                result["messages"] = add_messages(state.get("messages", []), [user_message])
            
            return result
        except Exception as e:
            error_msg = f"프롬프트 보강 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "status": "error"
            }
    
    def generate_analysis_code_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """노드 2: 데이터 분석 코드 생성 (Human-in-the-Loop 포함)"""
        print("💻 [Node 2] 데이터 분석 코드 생성 중...")
        
        CSV_file_path = state.get("CSV_file_path", "")
        CSV_file_paths = state.get("CSV_file_paths", [])
        CSV_metadata = state.get("CSV_metadata", "")
        query = state.get("query", "")
        
        # Human-in-the-Loop: 재개 시 승인 응답 확인
        # interrupt 후 재개되면 노드가 처음부터 다시 실행되므로,
        # 이미 생성된 코드가 있고 승인 대기 중인지 확인
        # 주의: interrupt 호출 전에 코드를 state에 저장해야 함
        # 중요: 이미 생성된 코드가 있어도 문법 검증을 먼저 수행해야 함
        if enable_hitl and state.get("generated_code") and not state.get("code_approved", False):
            # 이미 생성된 코드가 있고 승인 대기 중 (재개된 경우)
            generated_code = state.get("generated_code")
            generated_code_file = state.get("generated_code_file")
            code_file = Path(generated_code_file) if generated_code_file else None
            
            # 중요: 이미 생성된 코드가 있어도 문법 검증을 먼저 수행
            # 이전 실행에서 실패한 코드일 수 있으므로 재검증 필요
            print("🔍 [재검증] 이미 생성된 코드의 문법 검증 수행 중...")
            code_to_validate = generated_code
            if not code_to_validate and code_file and code_file.exists():
                try:
                    code_to_validate = code_file.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"⚠️ 코드 파일 읽기 실패: {str(e)}")
            
            if code_to_validate:
                # 문법 검증 수행
                syntax_errors = []
                try:
                    import ast
                    ast.parse(code_to_validate)
                    print("✅ 기존 코드 문법 검증 통과")
                except SyntaxError as e:
                    error_msg = f"문법 오류 (라인 {e.lineno}): {e.msg}"
                    if e.text:
                        error_msg += f"\n  코드: {e.text.strip()}"
                    syntax_errors.append(error_msg)
                    print(f"❌ 기존 코드에 문법 오류 발견: {error_msg}")
                    print("⚠️ 기존 코드에 문법 오류가 있어 새로 생성합니다.")
                    # 문법 오류가 있으면 기존 코드를 무시하고 새로 생성
                    generated_code = None
                    code_file = None
                except Exception as e:
                    print(f"⚠️ 문법 검증 중 예외 발생: {str(e)}")
                    # 예외 발생 시에도 기존 코드 사용 (하지만 경고)
            
            # 문법 오류가 없거나 HITL이 비활성화된 경우에만 승인 처리
            if generated_code and not syntax_errors:
                print("⏸️  [Human-in-the-Loop] 코드 승인 대기 중 (재개됨)...")
                
                # interrupt로 승인 요청 (재개 시 전달된 값이 반환됨)
                # interrupts가 비활성화되어 있으면 자동으로 승인 처리
                try:
                    approval_response = interrupt({
                        "type": "code_review",
                        "code": generated_code,
                        "code_file": str(code_file) if code_file else None,
                        "message": "생성된 코드를 검토하고 승인해주세요.",
                        "options": ["approve", "edit", "reject"]
                    })
                except Exception:
                    # interrupts가 비활성화되어 있으면 자동 승인
                    print("✅ interrupts 비활성화됨 - 자동 승인")
                    approval_response = "approve"
            else:
                # 문법 오류가 있으면 기존 코드를 무시하고 새로 생성
                print("⚠️ 기존 코드에 문제가 있어 새로 생성합니다.")
                generated_code = None
                code_file = None
                approval_response = None  # 새로 생성하도록 함
            
            # 재개 시 전달된 값 처리
            # LangGraph Studio에서 Resume 버튼을 누르면 기본적으로 승인으로 처리
            if isinstance(approval_response, dict):
                action = approval_response.get("action", "approve")
                
                if action == "approve" or action is None:
                    # approve이거나 action이 없으면 기본 승인
                    final_code = generated_code
                    print("✅ 코드 승인됨")
                    
                    # 코드는 generated_code 디렉토리에 그대로 유지 (실행 시 사용)
                    # approved_code로 이동하지 않음
                    
                    return {
                        "generated_code": final_code,
                        "generated_code_file": str(code_file) if code_file else None,
                        "status": "code_approved",
                        "code_approved": True,
                        "call_count": state.get("call_count", 0) + 1
                    }
                elif action == "edit":
                    edited_code = approval_response.get("edited_code", generated_code)
                    print("✏️  코드 수정됨")
                    
                    # 수정된 코드를 새 파일로 저장 (generated_code 디렉토리에)
                    edited_file = None
                    try:
                        # 기존 파일이 있으면 덮어쓰기
                        if code_file and code_file.exists():
                            code_file.write_text(edited_code, encoding='utf-8')
                            edited_file = code_file
                            print(f"✅ 수정된 코드 파일 저장: {edited_file}")
                        else:
                            # 새 파일 생성
                            edited_file = save_code_to_workspace(
                                code=edited_code,
                                directory="generated_code",
                                prefix="analysis_edited"
                            )
                            print(f"✅ 수정된 코드 파일 저장: {edited_file}")
                    except Exception as e:
                        print(f"⚠️ 수정된 코드 파일 저장 실패: {str(e)}")
                    
                    return {
                        "generated_code": edited_code,
                        "generated_code_file": str(edited_file) if edited_file else str(code_file) if code_file else None,
                        "status": "code_approved",
                        "code_approved": True,
                        "call_count": state.get("call_count", 0) + 1
                    }
                else:  # reject
                    print("❌ 코드 거부됨")
                    return {
                        "errors": ["코드가 사용자에 의해 거부되었습니다."],
                        "status": "error",
                        "code_approved": False,
                        "call_count": state.get("call_count", 0) + 1
                    }
            else:
                # 문자열로 직접 재개된 경우 또는 None인 경우 (기본 승인)
                # LangGraph Studio에서 Resume 버튼을 누르면 기본적으로 승인으로 처리
                final_code = approval_response if isinstance(approval_response, str) and approval_response else generated_code
                print("✅ 코드 승인됨 (기본 승인)")
                
                # 코드는 generated_code 디렉토리에 그대로 유지 (실행 시 사용)
                
                return {
                    "generated_code": final_code,
                    "generated_code_file": str(code_file) if code_file else None,
                    "status": "code_approved",
                    "code_approved": True,
                    "call_count": state.get("call_count", 0) + 1
                }
        
        # 코딩 에이전트 사용 여부 결정
        use_code_generation_agent = (
            CODE_GENERATION_AGENT_AVAILABLE and 
            code_generation_agent is not None
        )
        
        if use_code_generation_agent:
            # 코딩 에이전트를 사용하여 코드 생성
            print("🔧 [통합] 코딩 에이전트를 사용하여 코드 생성 중...")
            try:
                # Orchestrator로부터 받은 향상된 프롬프트 사용 (task_description으로 통일)
                task_description = state.get("task_description", "")
                
                # Planning Tool 활성화 시: Orchestrator의 전략적 계획을 구체적 플랜으로 변환
                task_description_for_planning = task_description if task_description else (query or f"CSV 파일 분석: {CSV_file_path}")
                
                if task_description:
                    print("📋 [Planning] Orchestrator의 전략적 계획을 구체적 플랜으로 변환 중...")
                    print(f"   전략적 계획 미리보기: {task_description[:200]}...")
                
                # CSV 상태를 코딩 에이전트 상태로 변환
                # requirements 필드 제거: CodeGeneration Agent의 analyze_requirements_node가 task_description을 requirements로 자동 사용
                code_agent_state: CodeGenerationState = {
                    "messages": [],
                    "task_description": task_description_for_planning,  # Planning Tool이 이를 기반으로 하위 작업 분해 (requirements로 자동 사용됨)
                    # requirements 필드 제거: CodeGeneration Agent의 analyze_requirements_node가 task_description을 requirements로 자동 사용
                    "context": {
                        "domain": "csv_analysis",
                        "csv_file_path": CSV_file_path,
                        "csv_file_paths": CSV_file_paths,
                        "csv_metadata": CSV_metadata,
                        "query": query
                    },
                    "target_filepath": None,  # 코딩 에이전트가 자동으로 생성
                    "status": "analyzing"
                }
                
                # 코딩 에이전트 실행
                code_agent_result = code_generation_agent.invoke(code_agent_state)
                
                # Planning 결과 확인 및 로그 출력
                planning_result = code_agent_result.get("planning_result", "")
                planning_todos = code_agent_result.get("planning_todos", [])
                if planning_result or planning_todos:
                    print(f"✅ [Planning] Planning 완료: {len(planning_todos)}개의 하위 작업 생성")
                    if planning_todos:
                        print("   하위 작업 목록:")
                        for i, todo in enumerate(planning_todos[:5], 1):  # 최대 5개만 출력
                            todo_desc = todo.get("description", todo.get("task", str(todo)))
                            print(f"     {i}. {todo_desc}")
                        if len(planning_todos) > 5:
                            print(f"     ... 외 {len(planning_todos) - 5}개")
                    
                    # 동적 작업 추적: Planning 결과를 작업 이력에 추가
                    task_history = state.get("task_history", [])
                    if task_history:
                        # 마지막 작업에 Planning 결과 추가
                        task_history[-1]["planning_todos"] = planning_todos
                        task_history[-1]["planning_result"] = planning_result
                        print(f"✅ [동적 작업 추적] Planning 결과를 작업 이력에 추가 완료")
                
                # 코딩 에이전트 결과 추출
                generated_code = code_agent_result.get("generated_code", "")
                generated_code_file_from_agent = code_agent_result.get("generated_code_file", "")
                code_syntax_valid_from_agent = code_agent_result.get("code_syntax_valid", None)
                syntax_errors_from_agent = code_agent_result.get("syntax_errors", [])
                validation_errors_from_agent = code_agent_result.get("validation_errors", [])
                
                # 핵심 확인 1: 코드가 생성되었는지 확인
                if not generated_code:
                    print("❌ 코딩 에이전트가 코드를 생성하지 못했습니다. 기존 방식으로 폴백합니다.")
                    use_code_generation_agent = False
                else:
                    print(f"✅ 코딩 에이전트로 코드 생성 완료 ({len(generated_code)} 문자)")
                    
                    # 핵심 확인 2: 코드 검증 상태 확인
                    if code_syntax_valid_from_agent is True:
                        print("✅ 코딩 에이전트에서 코드 검증 완료 (문법 오류 없음)")
                        # 코딩 에이전트가 이미 검증 완료 → CSV 분석 에이전트에서 재검증 불필요
                        code_needs_validation = False
                    elif code_syntax_valid_from_agent is False:
                        print(f"⚠️ 코딩 에이전트에서 코드 검증 실패 (문법 오류 {len(syntax_errors_from_agent)}개)")
                        if syntax_errors_from_agent:
                            print(f"   문법 오류: {syntax_errors_from_agent[:3]}")  # 최대 3개만 출력
                        # 코딩 에이전트가 검증 실패 → CSV 분석 에이전트에서 수정 시도 필요
                        code_needs_validation = True
                    else:
                        print("⚠️ 코딩 에이전트에서 코드 검증 상태 불명확 (None)")
                        # 검증 상태가 불명확 → CSV 분석 에이전트에서 검증 필요
                        code_needs_validation = True
                    
                    # CSV 특화 처리: 파일 경로 변수 추가 및 호스트 경로를 도커 경로로 변환
                    generated_code = add_csv_filepath_variables(
                        generated_code, CSV_file_path, CSV_file_paths
                    )
                    
                    # 핵심: 호스트 경로를 도커 경로로 변환 (코딩 에이전트가 호스트 경로를 사용한 경우 대비)
                    generated_code = convert_host_paths_to_docker_paths(
                        generated_code, CSV_file_path, CSV_file_paths
                    )
                    
                    # IPython 모드: 파일 저장하지 않음 (IPython에서 직접 실행)
                    code_file = None
                    print("📝 IPython 모드: 코드는 파일로 저장하지 않고 IPython에서 직접 실행됩니다")
                    
                    # Human-in-the-Loop 처리 (코드 생성 후 승인 요청)
                    # 첫 번째 실행: state에 코드가 없으면 먼저 업데이트
                    if enable_hitl and not state.get("generated_code"):
                        print("⏸️  [Human-in-the-Loop] 코드 생성 완료, 승인 대기 중...")
                        # Command를 사용하여 state를 먼저 업데이트
                        return Command(
                            update={
                                "generated_code": generated_code,
                                "generated_code_file": str(code_file) if code_file else None,
                                "status": "code_generated_pending_approval",
                                "code_syntax_valid": code_syntax_valid_from_agent if code_syntax_valid_from_agent is not None else None,
                                "syntax_errors": syntax_errors_from_agent if syntax_errors_from_agent else [],  # 빈 리스트로 명확히 표시 (검증 수행됨)
                                "validation_errors": validation_errors_from_agent if validation_errors_from_agent else []  # 빈 리스트로 명확히 표시 (검증 수행됨)
                            }
                        )
                    
                    # HITL 비활성화 시 자동 승인
                    # 코딩 에이전트가 이미 검증 완료한 경우 그 결과를 신뢰하고 재검증 스킵
                    # 코딩 에이전트의 토큰 사용량도 State에서 가져와서 유지
                    code_agent_token_usage = code_agent_result.get("token_usage", {})
                    current_token_usage = state.get("token_usage", {})
                    if not current_token_usage:
                        current_token_usage = {
                            "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                            "by_model": {}
                        }
                    # 코딩 에이전트의 토큰 사용량이 있으면 집계
                    if code_agent_token_usage:
                        tracker = TokenUsageTracker()
                        # 코딩 에이전트의 토큰 사용량을 현재 State에 집계
                        for model_name, model_usage in code_agent_token_usage.get("by_model", {}).items():
                            current_token_usage = tracker.aggregate_usage(
                                current_token_usage,
                                {
                                    "input_tokens": model_usage.get("input_tokens", 0),
                                    "output_tokens": model_usage.get("output_tokens", 0),
                                    "total_tokens": model_usage.get("total_tokens", 0)
                                },
                                model_name=model_name
                            )
                    
                    return {
                        "generated_code": generated_code,
                        "generated_code_file": str(code_file) if code_file else None,
                        "status": "code_generated_and_validated" if code_syntax_valid_from_agent is True else "code_generated_need_validation",
                        "code_approved": not enable_hitl,  # HITL 비활성화 시 자동 승인
                        "code_syntax_valid": code_syntax_valid_from_agent,  # 코딩 에이전트의 검증 결과 사용
                        "syntax_errors": syntax_errors_from_agent if syntax_errors_from_agent else [],  # 빈 리스트로 명확히 표시 (검증 수행됨)
                        "validation_errors": validation_errors_from_agent if validation_errors_from_agent else [],  # 빈 리스트로 명확히 표시 (검증 수행됨)
                        "call_count": state.get("call_count", 0) + 1,
                        "token_usage": current_token_usage
                    }
                    
            except Exception as e:
                print(f"⚠️ 코딩 에이전트 실행 중 오류 발생: {str(e)}")
                print("   기존 방식으로 폴백합니다.")
                import traceback
                traceback.print_exc()
                use_code_generation_agent = False
        
        # 기존 방식: Worker 모델 직접 사용 (폴백)
        if not use_code_generation_agent:
            # Orchestrator로부터 받은 향상된 프롬프트 사용 (task_description으로 통일)
            task_description = state.get("task_description", "")
            
            if task_description:
                # Orchestrator가 생성한 향상된 프롬프트 사용
                print("📝 Orchestrator로부터 받은 향상된 프롬프트 사용")
                # 프롬프트를 별도 모듈에서 가져옴 (프롬프트 분리)
                try:
                    from .prompts import (
                        get_worker_system_prompt,
                        create_worker_user_prompt
                    )
                    system_prompt = get_worker_system_prompt()
                    # 여러 파일 모드 또는 단일 파일 모드
                    if CSV_file_paths and len(CSV_file_paths) > 1:
                        user_prompt = create_worker_user_prompt(
                            task_description,
                            csv_file_paths=CSV_file_paths
                        )
                    else:
                        file_path = CSV_file_paths[0] if CSV_file_paths else CSV_file_path
                        user_prompt = create_worker_user_prompt(
                            task_description,
                            csv_file_path=file_path
                        )
                except ImportError:
                    # 폴백: 기존 하드코딩된 프롬프트 사용
                    system_prompt = """당신은 데이터 분석 코드 생성 전문가(Worker)입니다. 
Orchestrator로부터 받은 작업 지시사항을 바탕으로 완전하고 실행 가능한 Python 코드를 생성하세요.

**요구사항:**
1. pandas를 사용하여 CSV 파일을 읽으세요
2. Orchestrator의 지시사항을 정확히 따르세요
3. 분석 결과를 print()로 출력하세요
4. 시각화가 필요하면 matplotlib 또는 seaborn을 사용하세요
5. 코드는 완전하고 실행 가능해야 합니다

**중요:**
- 파일 경로는 변수로 사용하세요 (예: filepath = "경로")
- import 문을 포함하세요
- 모든 출력은 print()로 표시하세요
- 코드만 생성하고 설명은 추가하지 마세요"""

                    user_prompt = f"""Orchestrator로부터 받은 작업 지시사항:
{task_description}

CSV 파일 경로: {CSV_file_path}

위 지시사항을 바탕으로 데이터 분석 코드를 생성하세요. 코드는 완전하고 실행 가능해야 합니다."""
            else:
                # 폴백: 기존 방식 (task_description이 없는 경우)
                print("⚠️ 향상된 프롬프트 없음, 기존 방식 사용 (폴백)")
                system_prompt = """당신은 데이터 분석 전문가입니다. CSV 파일을 분석하는 Python 코드를 생성하세요.

**요구사항:**
1. pandas를 사용하여 CSV 파일을 읽으세요
2. 사용자의 요청에 맞는 분석을 수행하세요
3. 분석 결과를 print()로 출력하세요
4. 시각화가 필요하면 matplotlib 또는 seaborn을 사용하세요
5. 코드는 완전하고 실행 가능해야 합니다

**중요:**
- 파일 경로는 변수로 사용하세요 (예: filepath = "경로")
- import 문을 포함하세요
- 모든 출력은 print()로 표시하세요
- 코드만 생성하고 설명은 추가하지 마세요"""

                user_prompt = f"""CSV 파일 정보:
파일 경로: {CSV_file_path}

CSV 메타데이터:
{CSV_metadata}

사용자 요청:
{query}

위 정보를 바탕으로 데이터 분석 코드를 생성하세요. 코드는 완전하고 실행 가능해야 합니다."""

            try:
                # Worker 모델을 사용하여 코드 생성 (폴백 모드)
                if worker_model is None:
                    raise ValueError("Worker 모델이 초기화되지 않았습니다.")
                
                print(f"🤖 Worker 모델 ({code_generation_model})로 코드 생성 중... (폴백 모드)")
                # 토큰 추적 추가
                tracker = TokenUsageTracker()
                callback = tracker.get_callback()
                
                response = worker_model.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ], config={"callbacks": [callback]})
                
                # 토큰 사용량 업데이트
                current_token_usage = state.get("token_usage", {})
                if not current_token_usage:
                    current_token_usage = {
                        "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "by_model": {}
                    }
                updated_token_usage = tracker.update_token_usage(
                    current_token_usage,
                    response if isinstance(response, AIMessage) else AIMessage(content=response.content if hasattr(response, 'content') else str(response)),
                    model_name=code_generation_model
                )
                
                generated_code = response.content if hasattr(response, 'content') else str(response)
                
                # 코드 블록 추출 (```python ... ``` 형식)
                if "```python" in generated_code:
                    code_start = generated_code.find("```python") + 9
                    code_end = generated_code.find("```", code_start)
                    generated_code = generated_code[code_start:code_end].strip()
                elif "```" in generated_code:
                    code_start = generated_code.find("```") + 3
                    code_end = generated_code.find("```", code_start)
                    generated_code = generated_code[code_start:code_end].strip()
                
                # 파일 경로 변수 추가 (없는 경우)
                # 주의: 도커 실행 시 컨테이너 내부 경로로 변환되므로 여기서는 원본 경로 사용
                # 실제 도커 경로 변환은 execute_code_node에서 수행
                import re
                
                # 여러 파일 모드
                if CSV_file_paths and len(CSV_file_paths) > 1:
                    # 여러 파일 경로 변수가 있는지 확인
                    has_filepath_vars = any(f'filepath_{i+1}' in generated_code or (i == 0 and 'filepath' in generated_code) 
                                           for i in range(len(CSV_file_paths)))
                    
                    if not has_filepath_vars:
                        # 여러 파일 경로 변수 추가
                        filepath_vars = []
                        for i, file_path in enumerate(CSV_file_paths):
                            var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
                            filepath_vars.append(f'{var_name} = "{file_path}"')
                        generated_code = '\n'.join(filepath_vars) + '\n' + generated_code
                else:
                    # 단일 파일 모드 (하위 호환성)
                    file_path = CSV_file_paths[0] if CSV_file_paths else CSV_file_path
                    if 'filepath' not in generated_code and 'pd.read_csv' in generated_code:
                        # pd.read_csv에 직접 경로가 있는 경우 변수로 변경
                        pattern = r"pd\.read_csv\(['\"]([^'\"]+)['\"]"
                        if re.search(pattern, generated_code):
                            # 원본 경로 사용 (execute_code_node에서 도커 경로로 변환)
                            generated_code = f'filepath = "{file_path}"\n' + generated_code
                            generated_code = re.sub(pattern, 'pd.read_csv(filepath)', generated_code)
                
                print(f"✅ IPython 코드 생성 완료 ({len(generated_code)} 문자)")
                
                # IPython 모드: 파일 저장하지 않음 (IPython에서 직접 실행)
                code_file = None
                print("📝 IPython 모드: 코드는 파일로 저장하지 않고 IPython에서 직접 실행됩니다")
                
            except Exception as e:
                error_msg = f"코드 생성 실패: {str(e)}"
                print(f"❌ {error_msg}")
                return {
                    "errors": [error_msg],
                    "status": "error"
                }
        
        # Human-in-the-Loop: 코드 생성 후 승인 요청
        # interrupt() 호출은 try-except 블록 밖에서 처리해야 함
        # interrupt()는 정상적인 흐름 제어 메커니즘이므로 예외로 처리되면 안 됨
        if enable_hitl:
            # interrupt 호출 전에 state에 코드와 파일 정보를 저장해야 함
            # 재개 시 노드가 처음부터 다시 실행되므로, state에 저장된 정보를 확인하여
            # 코드를 다시 생성하지 않도록 해야 함
            #
            # Command를 사용하여 state를 먼저 업데이트하고 반환
            # 그 다음 재개 시 처리 로직(1110번 라인)에서 interrupt 호출
            # 하지만 Command를 사용하면 노드가 반환되므로, interrupt를 호출할 수 없음
            #
            # 해결책: 먼저 state를 업데이트하고 반환 (Command 사용)
            # 재개 시 처리 로직에서 state를 확인하고 interrupt 호출
            # 하지만 재개 시 처리 로직은 이미 state에 코드가 있을 때만 실행되므로,
            # 첫 번째 실행 시에는 state를 먼저 업데이트해야 함
            #
            # 최종 해결책: 
            # 1. 코드 생성 후 state에 코드가 없으면 먼저 state를 업데이트하고 반환 (Command 사용)
            # 2. 재개 시 처리 로직에서 state를 확인하고 interrupt 호출
            # 3. interrupt 호출 후 사용자 응답 처리
            
            # 첫 번째 실행: state에 코드가 없으면 먼저 업데이트
            if not state.get("generated_code"):
                print("⏸️  [Human-in-the-Loop] 코드 생성 완료, 승인 대기 중...")
                # Command를 사용하여 state를 먼저 업데이트
                return Command(
                    update={
                        "generated_code": generated_code,
                        "generated_code_file": str(code_file) if code_file else None,
                        "status": "code_generated_pending_approval"
                    }
                )
            
            # 재개 시: state에 코드가 있으면 interrupt 호출 (위의 재개 처리 로직에서 처리됨)
            # 이 코드는 실행되지 않아야 하지만, 안전을 위해 유지
            # interrupts가 비활성화되어 있으면 자동 승인 처리
            if not state.get("code_approved", False):
                print("⏸️  [Human-in-the-Loop] 코드 승인 대기 중...")
                try:
                    approval_response = interrupt({
                        "type": "code_review",
                        "code": generated_code,
                        "code_file": str(code_file) if code_file else None,
                        "message": "생성된 코드를 검토하고 승인해주세요.",
                        "options": ["approve", "edit", "reject"]
                    })
                except Exception:
                    # interrupts가 비활성화되어 있으면 자동 승인
                    print("✅ interrupts 비활성화됨 - 자동 승인")
                    approval_response = "approve"
                
                # 승인 처리
                if isinstance(approval_response, dict):
                    action = approval_response.get("action", "approve")
                else:
                    action = approval_response if isinstance(approval_response, str) else "approve"
                
                if action == "approve" or action is None:
                    print("✅ 코드 승인됨")
                    return {
                        "generated_code": generated_code,
                        "generated_code_file": str(code_file) if code_file else None,
                        "status": "code_approved",
                        "code_approved": True,
                        "call_count": state.get("call_count", 0) + 1,
                        "token_usage": state.get("token_usage", {})
                    }
                elif action == "edit":
                    edited_code = approval_response.get("edited_code", generated_code) if isinstance(approval_response, dict) else generated_code
                    print("✏️  코드 수정됨")
                    # 수정된 코드 저장 로직은 재개 처리 로직에서 처리됨
                    return {
                        "generated_code": edited_code,
                        "generated_code_file": str(code_file) if code_file else None,
                        "status": "code_approved",
                        "code_approved": True,
                        "call_count": state.get("call_count", 0) + 1,
                        "token_usage": state.get("token_usage", {})
                    }
                else:  # reject
                    print("❌ 코드 거부됨")
                    return {
                        "errors": ["코드가 사용자에 의해 거부되었습니다."],
                        "status": "error",
                        "code_approved": False,
                        "call_count": state.get("call_count", 0) + 1
                    }
        else:
            # HITL 비활성화 시 바로 반환 (파일은 저장됨)
            # 토큰 사용량은 이미 업데이트됨 (worker_model 호출 시)
            return {
                "generated_code": generated_code,
                "generated_code_file": str(code_file) if code_file else None,
                "status": "code_generated",
                "code_approved": True,
                "call_count": state.get("call_count", 0) + 1,
                "token_usage": updated_token_usage if 'updated_token_usage' in locals() else state.get("token_usage", {})
            }
    
    def validate_code_syntax_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """코드 문법 검증 노드: 생성된 코드의 문법 오류를 실행 전에 검증
        
        Python의 ast 모듈을 사용하여 문법 검증을 수행합니다.
        문법 오류가 발견되면 Worker에게 수정 요청을 보냅니다.
        
        주의: 코드 생성 에이전트를 사용한 경우 이미 검증이 완료되었을 수 있으므로,
        code_syntax_valid가 이미 설정되어 있으면 스킵합니다.
        """
        print("🔍 [Validate Syntax] 코드 문법 검증 중...")
        
        # 코드 생성 에이전트가 이미 검증을 완료했다고 해도, 실제 파일을 다시 검증해야 함
        # (코드 생성 에이전트가 검증한 코드와 실제 저장된 파일이 다를 수 있음)
        code_syntax_valid_existing = state.get("code_syntax_valid", None)
        if code_syntax_valid_existing is not None:
            if code_syntax_valid_existing:
                print("⚠️ 코드 생성 에이전트에서 검증 완료됨 - 하지만 실제 파일을 재검증합니다")
            else:
                print("⚠️ 코드 생성 에이전트에서 검증 실패 - 재검증 수행")
                # 검증 실패한 경우 재검증 수행
        
        generated_code = state.get("generated_code", "")
        generated_code_file = state.get("generated_code_file", "")
        
        # 코드 가져오기
        code_to_validate = generated_code
        if not code_to_validate and generated_code_file:
            code_file_path = Path(generated_code_file)
            if code_file_path.exists():
                try:
                    code_to_validate = code_file_path.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"⚠️ 코드 파일 읽기 실패: {str(e)}")
                    return {
                        "code_syntax_valid": False,
                        "syntax_errors": [f"코드 파일 읽기 실패: {str(e)}"],
                        "status": "syntax_validation_failed"
                    }
        
        if not code_to_validate:
            return {
                "code_syntax_valid": False,
                "syntax_errors": ["검증할 코드가 없습니다."],
                "status": "syntax_validation_failed"
            }
        
        # Python 문법 검증 및 변수 정의 검증
        syntax_errors = []
        try:
            import ast
            # AST 파싱으로 문법 검증
            try:
                tree = ast.parse(code_to_validate)
                print("✅ 코드 문법 검증 통과")
                
                # 변수 정의 검증 (정적 분석)
                # filepath, filepath_2 등이 사용되지만 정의되지 않은 경우 확인
                defined_vars = set()
                used_vars = set()
                
                # 변수 정의 수집
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defined_vars.add(target.id)
                
                # 변수 사용 수집
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        used_vars.add(node.id)
                
                # filepath 관련 변수 확인 (핵심: 정의되지 않은 변수 사용 시 에러로 처리)
                filepath_vars = {var for var in used_vars if var.startswith('filepath')}
                undefined_filepath_vars = filepath_vars - defined_vars
                
                if undefined_filepath_vars:
                    var_list = ', '.join(sorted(undefined_filepath_vars))
                    error_msg = f"변수 정의 오류: {var_list} 변수가 사용되지만 정의되지 않았습니다. 코드에서 이 변수들을 정의하거나 올바른 변수명을 사용하세요."
                    syntax_errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    # ✅ 핵심 수정: 경고가 아닌 에러로 처리하여 사전에 차단
                    return {
                        "code_syntax_valid": False,
                        "syntax_errors": syntax_errors,
                        "status": "syntax_validation_failed"
                    }
                
                return {
                    "code_syntax_valid": True,
                    "syntax_errors": [],
                    "status": "syntax_validated"
                }
            except SyntaxError as e:
                error_msg = f"문법 오류 (라인 {e.lineno}): {e.msg}"
                if e.text:
                    error_msg += f"\n  코드: {e.text.strip()}"
                    if e.offset:
                        error_msg += f"\n  위치: {' ' * (e.offset - 1)}^"
                syntax_errors.append(error_msg)
                print(f"❌ 문법 오류 발견: {error_msg}")
        except Exception as e:
            # ast 모듈 사용 실패 시 compile() 사용
            try:
                compile(code_to_validate, '<string>', 'exec')
                print("✅ 코드 문법 검증 통과 (compile 사용)")
                return {
                    "code_syntax_valid": True,
                    "syntax_errors": [],
                    "status": "syntax_validated"
                }
            except SyntaxError as e:
                error_msg = f"문법 오류 (라인 {e.lineno}): {e.msg}"
                if e.text:
                    error_msg += f"\n  코드: {e.text.strip()}"
                    if e.offset:
                        error_msg += f"\n  위치: {' ' * (e.offset - 1)}^"
                syntax_errors.append(error_msg)
                print(f"❌ 문법 오류 발견: {error_msg}")
            except Exception as compile_error:
                syntax_errors.append(f"코드 검증 중 오류 발생: {str(compile_error)}")
                print(f"❌ 코드 검증 실패: {str(compile_error)}")
        
        # 문법 오류가 발견된 경우 Worker에게 수정 요청
        if syntax_errors:
            print(f"🔧 문법 오류 발견 ({len(syntax_errors)}개) - 코드 수정 요청 중...")
            
            # Worker 모델이 없으면 코드 생성 에이전트를 사용하여 수정
            if worker_model is None:
                if CODE_GENERATION_AGENT_AVAILABLE and code_generation_agent is not None:
                    print("🔧 코드 생성 에이전트를 사용하여 코드 수정 중...")
                    try:
                        # 코드 생성 에이전트에 수정 요청
                        fix_state: CodeGenerationState = {
                            "messages": [],
                            "task_description": f"다음 코드의 문법 오류를 수정하세요:\n{chr(10).join(['- ' + err for err in syntax_errors])}",
                            "requirements": f"다음 코드의 문법 오류를 수정하여 완전하고 실행 가능한 코드를 생성하세요:\n\n```python\n{code_to_validate}\n```\n\n문법 오류:\n{chr(10).join(['- ' + err for err in syntax_errors])}",
                            "context": {
                                "domain": "csv_analysis",
                                "fix_mode": True,
                                "original_code": code_to_validate,
                                "syntax_errors": syntax_errors
                            },
                            "generated_code": code_to_validate,  # 원본 코드
                            "code_syntax_valid": False,  # 검증 실패 상태
                            "syntax_errors": syntax_errors,
                            "status": "fixing"
                        }
                        
                        # 코드 생성 에이전트 실행 (fix_code 노드로 직접 가도록)
                        fixed_result = code_generation_agent.invoke(fix_state)
                        
                        fixed_code = fixed_result.get("generated_code") or fixed_result.get("fixed_code", "")
                        
                        if fixed_code and fixed_code != code_to_validate:
                            print(f"✅ 코드 생성 에이전트로 코드 수정 완료 ({len(fixed_code)} 문자)")
                            
                            # 수정된 코드의 문법 재검증
                            try:
                                import ast
                                ast.parse(fixed_code)
                                print("✅ 수정된 코드 문법 검증 통과")
                                
                                # 수정된 코드를 파일로 저장
                                fixed_code_file = None
                                if generated_code_file:
                                    code_file_path = Path(generated_code_file)
                                    if code_file_path.exists():
                                        try:
                                            code_file_path.write_text(fixed_code, encoding='utf-8')
                                            fixed_code_file = str(code_file_path)
                                            print(f"✅ 수정된 코드 파일 저장: {fixed_code_file}")
                                        except Exception as e:
                                            print(f"⚠️ 코드 파일 저장 실패: {str(e)}")
                                
                                return {
                                    "generated_code": fixed_code,
                                    "generated_code_file": fixed_code_file if fixed_code_file else generated_code_file,
                                    "code_syntax_valid": True,
                                    "syntax_errors": [],
                                    "status": "syntax_fixed_and_validated",
                                    "call_count": state.get("call_count", 0) + 1
                                }
                            except SyntaxError as e:
                                error_msg = f"수정된 코드에도 문법 오류가 있습니다 (라인 {e.lineno}): {e.msg}"
                                print(f"❌ {error_msg}")
                                return {
                                    "code_syntax_valid": False,
                                    "syntax_errors": syntax_errors + [error_msg],
                                    "status": "syntax_validation_failed",
                                    "errors": [f"코드 수정 후에도 문법 오류가 남아있습니다: {error_msg}"],
                                    "call_count": state.get("call_count", 0) + 1
                                }
                        else:
                            print("⚠️ 코드 생성 에이전트가 코드를 수정하지 못했습니다.")
                            return {
                                "code_syntax_valid": False,
                                "syntax_errors": syntax_errors,
                                "status": "syntax_validation_failed",
                                "errors": ["코드 생성 에이전트가 코드를 수정하지 못했습니다."],
                                "call_count": state.get("call_count", 0) + 1
                            }
                    except Exception as e:
                        error_msg = f"코드 생성 에이전트로 수정 실패: {str(e)}"
                        print(f"❌ {error_msg}")
                        return {
                            "code_syntax_valid": False,
                            "syntax_errors": syntax_errors,
                            "status": "syntax_validation_failed",
                            "errors": [error_msg],
                            "call_count": state.get("call_count", 0) + 1
                        }
                else:
                    error_msg = "Worker 모델이 없고 코드 생성 에이전트도 사용할 수 없어 코드를 수정할 수 없습니다."
                    print(f"❌ {error_msg}")
                    return {
                        "code_syntax_valid": False,
                        "syntax_errors": syntax_errors,
                        "status": "syntax_validation_failed",
                        "errors": [error_msg],
                        "call_count": state.get("call_count", 0) + 1
                    }
            
            # Worker에게 문법 오류 수정 요청
            try:
                from .prompts import get_worker_system_prompt
                
                fix_prompt = f"""다음 코드에 문법 오류가 있습니다. 오류를 수정하여 완전하고 실행 가능한 코드를 생성하세요.

**문법 오류:**
{chr(10).join(['- ' + err for err in syntax_errors])}

**원본 코드:**
```python
{code_to_validate}
```

위 오류를 수정하여 완전하고 실행 가능한 Python 코드를 생성하세요. 코드만 생성하고 설명은 추가하지 마세요."""
                
                worker_system_prompt = get_worker_system_prompt()
                # 토큰 추적 추가
                tracker = TokenUsageTracker()
                callback = tracker.get_callback()
                
                response = worker_model.invoke([
                    SystemMessage(content=worker_system_prompt),
                    HumanMessage(content=fix_prompt)
                ], config={"callbacks": [callback]})
                
                # 토큰 사용량 업데이트
                current_token_usage = state.get("token_usage", {})
                if not current_token_usage:
                    current_token_usage = {
                        "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "by_model": {}
                    }
                updated_token_usage = tracker.update_token_usage(
                    current_token_usage,
                    response if isinstance(response, AIMessage) else AIMessage(content=response.content if hasattr(response, 'content') else str(response)),
                    model_name=code_generation_model
                )
                
                fixed_code = response.content if hasattr(response, 'content') else str(response)
                
                # 코드 블록 추출 (마크다운 코드 블록 제거)
                code_block_match = re.search(r'```(?:python)?\n?(.*?)```', fixed_code, re.DOTALL)
                if code_block_match:
                    fixed_code = code_block_match.group(1).strip()
                else:
                    # 코드 블록이 없으면 전체를 코드로 간주
                    fixed_code = fixed_code.strip()
                
                # 수정된 코드의 문법 재검증
                try:
                    import ast
                    ast.parse(fixed_code)
                    print("✅ 코드 수정 완료 및 문법 검증 통과")
                    
                    # 수정된 코드를 파일로 저장
                    fixed_code_file = None
                    if generated_code_file:
                        code_file_path = Path(generated_code_file)
                        if code_file_path.exists():
                            try:
                                code_file_path.write_text(fixed_code, encoding='utf-8')
                                fixed_code_file = str(code_file_path)
                                print(f"✅ 수정된 코드 파일 저장: {fixed_code_file}")
                            except Exception as e:
                                print(f"⚠️ 코드 파일 저장 실패: {str(e)}")
                    
                    return {
                        "generated_code": fixed_code,
                        "generated_code_file": fixed_code_file if fixed_code_file else generated_code_file,
                        "code_syntax_valid": True,
                        "syntax_errors": [],
                        "status": "syntax_fixed_and_validated",
                        "call_count": state.get("call_count", 0) + 1,
                        "token_usage": updated_token_usage
                    }
                except SyntaxError as e:
                    # 수정된 코드에도 여전히 문법 오류가 있는 경우
                    error_msg = f"수정된 코드에도 문법 오류가 있습니다 (라인 {e.lineno}): {e.msg}"
                    print(f"❌ {error_msg}")
                    return {
                        "code_syntax_valid": False,
                        "syntax_errors": syntax_errors + [error_msg],
                        "status": "syntax_validation_failed",
                        "errors": [f"코드 수정 후에도 문법 오류가 남아있습니다: {error_msg}"],
                        "call_count": state.get("call_count", 0) + 1
                    }
            except Exception as e:
                error_msg = f"코드 수정 요청 실패: {str(e)}"
                print(f"❌ {error_msg}")
                return {
                    "code_syntax_valid": False,
                    "syntax_errors": syntax_errors,
                    "status": "syntax_validation_failed",
                    "errors": [error_msg],
                    "call_count": state.get("call_count", 0) + 1
                }
        
        # 예상치 못한 경우
        return {
            "code_syntax_valid": False,
            "syntax_errors": syntax_errors,
            "status": "syntax_validation_failed"
        }
    
    def execute_code_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """노드 3: 생성된 IPython 코드 실행 (Human-in-the-Loop 포함)"""
        print("🚀 [Execute Code] IPython에서 코드 실행 준비 중...")
        
        generated_code = state.get("generated_code", "")
        CSV_file_path = state.get("CSV_file_path", "")
        CSV_file_paths = state.get("CSV_file_paths", [])
        
        if not generated_code:
            return {
                "errors": ["실행할 코드가 없습니다."],
                "status": "error"
            }
        
        # 리팩토링 Phase 2: 파일 경로 처리를 통합 함수로 단순화 (state 기반)
        csv_file_paths_list = resolve_csv_files(state)
        
        # CSV 파일이 없으면 에러 반환
        if not csv_file_paths_list:
            error_msg = f"CSV 파일을 찾을 수 없습니다. 제공된 경로: {CSV_file_paths if CSV_file_paths else CSV_file_path}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "status": "error",
                "execution_result": error_msg
            }
        
        print(f"✅ CSV 파일 확인 완료: {len(csv_file_paths_list)}개 파일")
        for i, fpath in enumerate(csv_file_paths_list, 1):
            print(f"   {i}. {fpath.name} -> {fpath}")
        
        # 리팩토링 Phase 2: 코드 준비를 통합 함수로 단순화
        code_to_execute = prepare_code_for_execution(
            code=generated_code,
            csv_file_paths=csv_file_paths_list
        )
        
        # 데이터 타입 전처리 코드 추가 (수치형 분석 함수 사용 시)
        code_to_execute = add_data_type_preprocessing(code_to_execute)
        
        # 디버깅: 최종 코드 미리보기
        print(f"📝 최종 실행 코드 미리보기:")
        print(f"   길이: {len(code_to_execute)} 문자")
        if 'filepath' in code_to_execute:
            filepath_lines = [line for line in code_to_execute.split('\n') if 'filepath' in line and '=' in line]
            if filepath_lines:
                print(f"   filepath 변수 정의:")
                for line in filepath_lines[:3]:  # 최대 3개만 출력
                    print(f"      - {line.strip()}")
        
        # Human-in-the-Loop: 코드 실행 전 승인 요청
        if enable_hitl:
            print("⏸️  [Human-in-the-Loop] 코드 실행 승인 대기 중...")
            
            # interrupt로 실행 승인 요청
            try:
                execution_approval = interrupt({
                    "type": "execution_review",
                    "code": code_to_execute,
                    "message": "IPython에서 코드 실행을 승인하시겠습니까?",
                    "options": ["approve", "reject"]
                })
            except Exception:
                # interrupts가 비활성화되어 있으면 자동 승인
                print("✅ interrupts 비활성화됨 - 자동 승인")
                execution_approval = "approve"
            
            # Command로 재개된 경우 처리
            if isinstance(execution_approval, dict):
                action = execution_approval.get("action", "approve")
                
                if action == "reject":
                    print("❌ 코드 실행 거부됨")
                    return {
                        "errors": ["코드 실행이 사용자에 의해 거부되었습니다."],
                        "status": "error",
                        "execution_approved": False
                    }
            elif execution_approval is not None and execution_approval != "approve":
                if execution_approval == "reject":
                    print("❌ 코드 실행 거부됨")
                    return {
                        "errors": ["코드 실행이 사용자에 의해 거부되었습니다."],
                        "status": "error",
                        "execution_approved": False
                    }
            
            print("✅ 코드 실행 승인됨")
        
        # Docker에서 코드 실행
        try:
            print(f"🐳 Docker에서 코드 실행 중...")
            
            # 코드를 임시 파일로 저장 (실행용)
            # 또한 영구 파일로도 저장 (디버깅 및 추적용)
            temp_code_file = None
            executed_code_file = None
            try:
                from src.utils.paths import get_workspace_subdirectories, get_docker_image_name
                from datetime import datetime
                directories = get_workspace_subdirectories()
                
                # 임시 파일 (실행용)
                temp_code_file = directories.get("generated_code", Path("/tmp")) / f"temp_code_{os.getpid()}.py"
                temp_code_file.parent.mkdir(parents=True, exist_ok=True)
                temp_code_file.write_text(code_to_execute, encoding='utf-8')
                
                # 영구 파일 (디버깅 및 추적용)
                executed_code_dir = directories.get("generated_code", Path("/tmp"))
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                executed_code_file = executed_code_dir / f"executed_code_{timestamp}_{os.getpid()}.py"
                executed_code_file.write_text(code_to_execute, encoding='utf-8')
                print(f"💾 실행 코드 파일 저장: {executed_code_file}")
                
                # 출력 디렉토리 설정
                output_directory = directories.get("results", None)
                if output_directory:
                    output_directory = str(output_directory)
                
                # 입력 파일 목록 준비
                input_files = [str(f) for f in csv_file_paths_list] if csv_file_paths_list else None
                
                # Docker에서 코드 실행
                execution_result_obj = execute_code_in_docker(
                    code_file=str(temp_code_file),
                    docker_image=get_docker_image_name(),
                    input_files=input_files,
                    output_directory=output_directory,
                    timeout=120  # 2분 타임아웃
                )
                
                # ExecutionResult에서 결과 추출
                execution_result = execution_result_obj.stdout
                if execution_result_obj.stderr:
                    execution_result = (execution_result or "") + "\n" + execution_result_obj.stderr
                
                # Context 추출 (사용자 쿼리 기반)
                user_query = state.get("query", "")
                context = extract_context_from_result(execution_result_obj, user_query=user_query)
                
                # 실행 결과 확인
                # stderr에 Traceback/Error가 있으면 에러로 처리
                stderr_content = execution_result_obj.stderr or ""
                has_python_error = (
                    "Traceback" in stderr_content or
                    "Error:" in stderr_content or
                    "Exception:" in stderr_content or
                    "NameError" in stderr_content or
                    "FileNotFoundError" in stderr_content or
                    "KeyError" in stderr_content or
                    "ValueError" in stderr_content or
                    "TypeError" in stderr_content or
                    "AttributeError" in stderr_content
                )
                
                # execution_result_obj.success가 True여도 stderr에 에러가 있으면 실패로 처리
                actual_success = execution_result_obj.success and not has_python_error
                
                if actual_success:
                    print(f"✅ Docker 코드 실행 완료")
                    print(f"📊 실행 결과 길이: {len(execution_result or '')} 문자")
                    
                    if execution_result and execution_result.strip():
                        print(f"📝 실행 결과 미리보기: {execution_result[:200]}...")
                    else:
                        print("⚠️ 실행 결과가 비어있습니다.")
                    
                    # Context 정보 출력
                    if context.get("insights"):
                        print(f"💡 발견된 인사이트: {len(context['insights'])}개")
                    if context.get("visualizations"):
                        print(f"📈 생성된 시각화: {len(context['visualizations'])}개")
                    
                    # Docker 실행 결과 형식으로 변환
                    docker_execution_result = {
                        "success": True,
                        "stdout": execution_result or "",
                        "stderr": execution_result_obj.stderr or "",
                        "exit_code": execution_result_obj.exit_code,
                        "visualizations": execution_result_obj.metadata.get("visualizations", [])
                    }
                    
                    # 성공 시 error_count 리셋
                    return {
                        "execution_result": execution_result if execution_result else "코드가 실행되었지만 출력이 없습니다.",
                        "docker_execution_result": docker_execution_result,
                        "executed_code_file": str(executed_code_file) if executed_code_file else str(temp_code_file),
                        "executed_code": code_to_execute,  # 실행된 코드 내용 저장
                        "context": context,  # Context 정보 추가
                        "status": "code_executed",
                        "execution_approved": True,
                        "analysis_iteration_count": state.get("analysis_iteration_count", 0) + 1,
                        "error_count": 0  # 성공 시 에러 카운트 리셋
                    }
                else:
                    # 실행 실패
                    error_msg = execution_result_obj.error or execution_result_obj.stderr or "실행 실패"
                    print(f"❌ Docker 실행 실패: {error_msg}")
                    
                    # 상세한 에러 정보 수집
                    stderr = execution_result_obj.stderr or ""
                    stdout = execution_result_obj.stdout or ""
                    mount_info = execution_result_obj.metadata.get("mount_info", {})
                    
                    # 에러 메시지 개선
                    detailed_error = f"코드 실행 중 오류 발생:\n{error_msg}"
                    
                    # FileNotFoundError인 경우 마운트 정보 추가
                    if "FileNotFoundError" in stderr or "No such file or directory" in stderr:
                        detailed_error += "\n\n💡 파일 경로 오류 해결 방법:"
                        detailed_error += "\n- 코드 파일과 같은 디렉토리: /workspace/code/파일명"
                        detailed_error += "\n- 데이터 디렉토리: /workspace/data/파일명"
                        if mount_info:
                            detailed_error += "\n\n📋 마운트된 파일 경로:"
                            for file_name, docker_path in mount_info.items():
                                detailed_error += f"\n  - {file_name} -> {docker_path}"
                        
                        # 생성된 코드에서 파일 경로 확인
                        if 'filepath' in code_to_execute:
                            filepath_lines = [line.strip() for line in code_to_execute.split('\n') 
                                            if 'filepath' in line and '=' in line]
                            if filepath_lines:
                                detailed_error += "\n\n📝 코드에 정의된 filepath 변수:"
                                for line in filepath_lines[:3]:
                                    detailed_error += f"\n  {line}"
                    
                    # stdout이 있으면 추가
                    if stdout:
                        detailed_error += f"\n\n📊 실행 출력 (stdout):\n{stdout[:500]}"
                    
                    docker_execution_result = {
                        "success": False,
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": execution_result_obj.exit_code,
                        "error": error_msg,
                        "mount_info": mount_info
                    }
                    
                    # 에러 발생 시 error_count 증가
                    current_error_count = state.get("error_count", 0)
                    
                    # 실행된 코드 파일 경로 정보 추가
                    if executed_code_file:
                        detailed_error += f"\n\n📄 실행된 코드 파일: {executed_code_file}"
                        detailed_error += f"\n   (임시 파일: {temp_code_file.name})"
                        detailed_error += f"\n\n📝 실행된 코드 내용 (처음 50줄):"
                        code_lines = code_to_execute.split('\n')
                        for i, line in enumerate(code_lines[:50], 1):
                            detailed_error += f"\n   {i:3d}: {line}"
                        if len(code_lines) > 50:
                            detailed_error += f"\n   ... (총 {len(code_lines)}줄, 나머지는 파일 참조)"
                    
                    return {
                        "execution_result": detailed_error,
                        "docker_execution_result": docker_execution_result,
                        "executed_code_file": str(executed_code_file) if executed_code_file else str(temp_code_file),
                        "executed_code": code_to_execute,  # 실행된 코드 내용 저장
                        "status": "code_executed",
                        "execution_approved": True,
                        "analysis_iteration_count": state.get("analysis_iteration_count", 0) + 1,
                        "error_count": current_error_count + 1,
                        "errors": [error_msg]
                    }
            finally:
                # 임시 파일 정리 (성공 시에만 삭제, 에러 발생 시에는 유지)
                # executed_code_file은 항상 유지 (디버깅 및 추적용)
                try:
                    # 실행이 성공했는지 확인 (state에서 확인 불가능하므로 항상 유지)
                    # 대신 오래된 임시 파일만 정리 (나중에 별도 정리 작업으로 처리)
                    # 여기서는 임시 파일을 유지하여 디버깅 가능하도록 함
                    if temp_code_file and temp_code_file.exists():
                        # 임시 파일은 유지 (디버깅용)
                        # 너무 많은 파일이 쌓이면 나중에 별도 정리 작업 필요
                        pass
                except Exception:
                    pass
                
        except Exception as e:
            # 코드 실행 실패 (IPython 또는 일반 실행)
            generated_code = state.get("generated_code", "")
            error = ExecutionError(
                message=f"코드 실행 실패: {str(e)}",
                code=generated_code,
                agent_name="csv_data_analysis_agent",
                node_name="execute_code_node",
                original_error=e
            )
            print(format_error_message(error, include_traceback=True))
            
            docker_execution_result = {
                "success": False,
                "stdout": "",
                "stderr": error.message,
                "exit_code": -1,
                "error": error.message
            }
            
            error_state = format_error_for_state(error)
            error_state["execution_result"] = f"코드 실행 중 오류 발생: {error.message}"
            error_state["docker_execution_result"] = docker_execution_result
            error_state["executed_code_file"] = None
            error_state["status"] = "code_execution_failed"
            error_state["execution_approved"] = True
            increment_error_count(error_state)
            
            return error_state
    
    def validate_execution_result_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """실행 결과 검증 노드: 실행 결과의 품질을 검증하고 재시도 필요 여부 판단
        
        Phase 1 개선: 실행 결과가 비어있거나 불충분하면 재시도
        에러 카운팅: 에러가 3번 이상 발생하면 interrupt 호출하여 중단
        """
        print("🔍 [Validate Result] 실행 결과 검증 중...")
        
        execution_result = state.get("execution_result", "")
        docker_result = state.get("docker_execution_result", {})
        analysis_iteration_count = state.get("analysis_iteration_count", 0)
        max_iterations = state.get("max_analysis_iterations", 3)
        error_count = state.get("error_count", 0)
        
        # 에러가 3번 이상 발생하면 interrupt 호출하여 중단
        if error_count >= 3:
            error_msg = f"연속 에러가 {error_count}번 발생했습니다. 프로세스를 중단합니다."
            print(f"⚠️ {error_msg}")
            
            # interrupt 호출 (사용자에게 중단 여부 확인)
            try:
                interrupt_response = interrupt({
                    "type": "error_threshold_reached",
                    "message": error_msg,
                    "error_count": error_count,
                    "suggestion": "에러가 반복적으로 발생하고 있습니다. 분석을 중단하시겠습니까?"
                })
                print(f"✅ Interrupt 응답: {interrupt_response}")
            except Exception:
                # interrupts가 비활성화되어 있으면 자동으로 중단 처리
                print("✅ interrupts 비활성화됨 - 자동 중단 처리")
            
            return {
                "execution_result_valid": False,
                "retry_needed": False,
                "retry_reason": error_msg,
                "status": "error_threshold_reached",
                "error_count": error_count
            }
        
        # 결과 품질 검증
        has_output = bool(execution_result and execution_result.strip())
        stderr_content = docker_result.get("stderr", "")
        has_errors = bool(stderr_content)
        output_length = len(execution_result) if execution_result else 0
        
        # 1. 먼저 success 필드 확인 (가장 우선순위)
        docker_success = docker_result.get("success", True)  # 기본값 True (하위 호환성)
        
        # 2. stderr에 Python 에러가 있는지 확인
        has_python_error = False
        if stderr_content:
            has_python_error = (
                "Traceback" in stderr_content or
                "Error:" in stderr_content or
                "Exception:" in stderr_content or
                "NameError" in stderr_content or
                "FileNotFoundError" in stderr_content or
                "KeyError" in stderr_content or
                "ValueError" in stderr_content or
                "TypeError" in stderr_content or
                "AttributeError" in stderr_content or
                "IndexError" in stderr_content or
                "ModuleNotFoundError" in stderr_content or
                "ImportError" in stderr_content
            )
        
        # 3. 에러가 있으면 무조건 검증 실패
        if not docker_success or has_python_error:
            error_msg = stderr_content if has_python_error else "코드 실행 실패"
            print(f"❌ 에러 감지: success={docker_success}, python_error={has_python_error}")
            if has_python_error:
                print(f"📋 에러 내용: {stderr_content[:200]}...")
            
            # 에러 발생 시 error_count 증가
            current_error_count = state.get("error_count", 0)
            return {
                "execution_result_valid": False,
                "retry_needed": True,
                "retry_reason": f"코드 실행 중 오류 발생: {error_msg[:100]}",
                "status": "validation_failed",
                "error_count": current_error_count + 1
            }
        
        # 4. 의미 있는 출력인지 확인 (너무 짧거나 에러 메시지만 있는 경우)
        is_meaningful = False
        if has_output:
            # 최소 길이 확인 (100자 이상)
            if output_length >= 100:
                # 에러 메시지만 있는지 확인 (실제 실행 결과와 구분)
                error_keywords = ["error", "exception", "traceback", "failed", "실패"]
                result_lower = execution_result.lower()
                error_keyword_count = sum(1 for keyword in error_keywords if keyword in result_lower)
                # 에러 키워드가 전체의 30% 이상이면 의미 없는 것으로 판단
                if error_keyword_count < len(result_lower.split()) * 0.3:
                    is_meaningful = True
        
        validation_result = {
            "has_output": has_output,
            "has_errors": has_errors or has_python_error or not docker_success,
            "output_length": output_length,
            "is_meaningful": is_meaningful,
            "docker_success": docker_success,
            "has_python_error": has_python_error
        }
        
        print(f"📊 검증 결과: 출력={has_output}, 길이={output_length}, 의미있음={is_meaningful}, 성공={docker_success}, 에러={has_python_error}")
        
        # 결과가 불충분하고 최대 반복 횟수 미만이면 재시도
        if not is_meaningful and analysis_iteration_count < max_iterations:
            retry_reason = "실행 결과가 비어있거나 불충분함" if not has_output else "실행 결과가 의미 없음"
            print(f"⚠️ 재시도 필요: {retry_reason}")
            return {
                "execution_result_valid": False,
                "retry_needed": True,
                "retry_reason": retry_reason,
                "status": "validation_failed",
                "error_count": error_count  # 에러가 아니므로 카운트 유지
            }
        
        # 결과가 충분하거나 최대 반복 횟수 도달
        # 성공 시 error_count 리셋
        print("✅ 실행 결과 검증 통과")
        return {
            "execution_result_valid": True,
            "retry_needed": False,
            "status": "validation_passed",
            "error_count": 0  # 성공 시 에러 카운트 리셋
        }
    
    def analyze_execution_result_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """실행 결과 분석 노드: Orchestrator가 실행 결과를 분석하고 다음 액션 결정
        
        Phase 1 개선: 실행 결과를 분석하여 추가 분석 필요 여부 판단
        """
        print("🧠 [Analyze Result] 실행 결과 분석 중... (Orchestrator: GPT-OSS)")
        
        execution_result = state.get("execution_result", "")
        docker_result = state.get("docker_execution_result", {})
        analysis_iteration_count = state.get("analysis_iteration_count", 0)
        max_iterations = state.get("max_analysis_iterations", 3)
        accumulated_insights = state.get("accumulated_insights", [])
        query = state.get("query", "")
        
        # 핵심 확인: 실행 결과가 제대로 전달되었는지 확인
        if not execution_result or execution_result.strip() == "":
            error_msg = "❌ 실행 결과가 없습니다. 코드 실행이 실패했거나 출력이 없습니다."
            print(error_msg)
            print(f"   Docker 실행 상태: success={docker_result.get('success', False)}, exit_code={docker_result.get('exit_code', 'N/A')}")
            if docker_result.get('stderr'):
                print(f"   Stderr: {docker_result.get('stderr', '')[:500]}")
            return {
                "errors": [error_msg],
                "status": "no_execution_result",
                "next_action": "generate_report",  # 결과가 없어도 보고서 생성으로 진행
                "call_count": state.get("call_count", 0) + 1
            }
        
        # 실행 결과가 있으면 로깅
        print(f"✅ 실행 결과 확인 완료 (길이: {len(execution_result)} 문자)")
        if len(execution_result) > 200:
            print(f"📝 실행 결과 미리보기: {execution_result[:200]}...")
        
        # 최대 반복 횟수 도달 시 보고서 생성
        if analysis_iteration_count >= max_iterations:
            print(f"📊 최대 분석 반복 횟수({max_iterations}) 도달 - 보고서 생성으로 진행")
            return {
                "next_action": "generate_report",
                "status": "max_iterations_reached"
            }
        
        # Orchestrator가 실행 결과를 분석하고 다음 액션 결정
        analysis_prompt = f"""다음 코드 실행 결과를 분석하세요:

실행 결과:
{execution_result[:2000] if len(execution_result) > 2000 else execution_result}

도커 실행 상태:
- 성공: {docker_result.get('success', False)}
- Exit Code: {docker_result.get('exit_code', 0)}
- Stderr: {docker_result.get('stderr', '')[:500] if docker_result.get('stderr') else '없음'}

현재 분석 반복 횟수: {analysis_iteration_count} / {max_iterations}

이전에 발견된 인사이트:
{chr(10).join(['- ' + insight for insight in accumulated_insights]) if accumulated_insights else '없음'}

사용자 요청:
{query}

다음 중 어떤 액션이 필요한지 판단하세요:
1. "continue_analysis" - 추가 분석이 필요함 (더 깊은 분석 코드 생성)
2. "generate_report" - 충분한 정보가 수집되어 보고서 생성 가능

판단 기준:
- 실행 결과가 비어있거나 불충분하면 "continue_analysis"
- 실행 결과에서 새로운 인사이트를 발견할 수 있으면 "continue_analysis"
- 실행 결과가 충분하고 사용자 요청에 대한 답변이 가능하면 "generate_report"
- 최대 반복 횟수에 도달하면 "generate_report"

JSON 형식으로 응답하세요:
{{
    "next_action": "continue_analysis" 또는 "generate_report",
    "reason": "판단 이유",
    "insights": ["발견된 인사이트1", "발견된 인사이트2"],
    "suggestions": "다음 분석에서 집중할 영역"
}}"""

        try:
            # 토큰 추적 추가
            tracker = TokenUsageTracker()
            callback = tracker.get_callback()
            
            response = orchestrator_model.invoke([
                SystemMessage(content="당신은 데이터 분석 결과를 평가하고 다음 단계를 결정하는 전문가입니다."),
                HumanMessage(content=analysis_prompt)
            ], config={"callbacks": [callback]})
            
            # 토큰 사용량 업데이트
            current_token_usage = state.get("token_usage", {})
            if not current_token_usage:
                current_token_usage = {
                    "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    "by_model": {}
                }
            updated_token_usage = tracker.update_token_usage(
                current_token_usage,
                response if isinstance(response, AIMessage) else AIMessage(content=response.content if hasattr(response, 'content') else str(response)),
                model_name=model
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # JSON 파싱 시도
            try:
                # JSON 코드 블록 추출
                json_match = re.search(r'\{[^{}]*"next_action"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                else:
                    # JSON이 없으면 텍스트에서 추출
                    analysis_data = {
                        "next_action": "continue_analysis" if "continue" in response_text.lower() else "generate_report",
                        "reason": response_text[:200],
                        "insights": [],
                        "suggestions": ""
                    }
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 사용
                analysis_data = {
                    "next_action": "continue_analysis" if analysis_iteration_count < max_iterations - 1 else "generate_report",
                    "reason": "JSON 파싱 실패, 기본 로직 사용",
                    "insights": [],
                    "suggestions": ""
                }
            
            next_action = analysis_data.get("next_action", "generate_report")
            insights = analysis_data.get("insights", [])
            suggestions = analysis_data.get("suggestions", "")
            
            # 누적 인사이트 업데이트
            updated_insights = accumulated_insights.copy() if accumulated_insights else []
            for insight in insights:
                if insight and insight not in updated_insights:
                    updated_insights.append(insight)
            
            print(f"✅ 분석 완료: 다음 액션 = {next_action}")
            if insights:
                print(f"💡 발견된 인사이트: {len(insights)}개")
            if suggestions:
                print(f"💭 제안: {suggestions[:100]}...")
            
            return {
                "next_action": next_action,
                "insights": insights,
                "accumulated_insights": updated_insights,
                "suggestions": suggestions,  # 다음 분석 제안 저장
                "analysis_result": f"분석 결과: {analysis_data.get('reason', '')}\n제안: {suggestions}",
                "status": "result_analyzed",
                "call_count": state.get("call_count", 0) + 1,
                "token_usage": updated_token_usage
            }
        except Exception as e:
            error_msg = f"결과 분석 실패: {str(e)}"
            print(f"❌ {error_msg}")
            # 기본값: 최대 반복 횟수 미만이면 계속 분석
            default_action = "continue_analysis" if analysis_iteration_count < max_iterations - 1 else "generate_report"
            return {
                "next_action": default_action,
                "status": "analysis_failed",
                "errors": [error_msg]
            }
    
    def generate_final_report_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """최종 보고서 생성 노드: Orchestrator가 실행 결과를 분석하고 보고서 생성
        
        analyze_results_node의 기능을 통합하여 한 번에 처리합니다.
        """
        print("📝 [Final Report] 최종 보고서 생성 중... (Orchestrator: GPT-OSS)")
        
        CSV_metadata = state.get("CSV_metadata", "")
        execution_result = state.get("execution_result", "")
        analysis_result = state.get("analysis_result", "")
        query = state.get("query", "")
        docker_execution_result = state.get("docker_execution_result", {})
        accumulated_insights = state.get("accumulated_insights", [])
        analysis_iteration_count = state.get("analysis_iteration_count", 0)
        
        # 프롬프트를 별도 모듈에서 가져옴 (프롬프트 분리)
        try:
            from .prompts import (
                REPORT_GENERATION_SYSTEM_PROMPT,
                create_report_generation_user_prompt
            )
            system_prompt = REPORT_GENERATION_SYSTEM_PROMPT
            user_prompt = create_report_generation_user_prompt(
                csv_metadata=CSV_metadata,
                query=query,
                execution_result=execution_result,
                docker_execution_result=docker_execution_result,
                analysis_result=analysis_result,
                accumulated_insights=accumulated_insights,
                analysis_iteration_count=analysis_iteration_count
            )
        except ImportError:
            # 폴백: 기존 하드코딩된 프롬프트 사용
            system_prompt = """당신은 데이터 분석 보고서 작성 전문가입니다. 분석 결과를 바탕으로 종합적인 보고서를 작성하세요.

**보고서 구조:**
1. 데이터 개요
2. 분석 방법
3. 주요 발견사항
4. 인사이트 및 결론
5. 제언 (필요시)

모든 내용은 한글로 작성하세요."""

            user_prompt = f"""사용자 요청:
{query}

CSV 메타데이터:
{CSV_metadata}

코드 실행 결과:
{execution_result}

결과 분석:
{analysis_result}

위 정보를 바탕으로 종합적인 데이터 분석 보고서를 작성하세요."""

        try:
            # Orchestrator 모델을 사용하여 최종 보고서 생성
            print("📝 Orchestrator 모델로 최종 보고서 생성 중...")
            # 토큰 추적 추가
            tracker = TokenUsageTracker()
            callback = tracker.get_callback()
            
            response = orchestrator_model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ], config={"callbacks": [callback]})
            
            # 토큰 사용량 업데이트
            current_token_usage = state.get("token_usage", {})
            if not current_token_usage:
                current_token_usage = {
                    "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    "by_model": {}
                }
            updated_token_usage = tracker.update_token_usage(
                current_token_usage,
                response if isinstance(response, AIMessage) else AIMessage(content=response.content if hasattr(response, 'content') else str(response)),
                model_name=model
            )
            
            final_report = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ 최종 보고서 생성 완료")
            
            return {
                "final_report": final_report,
                "status": "completed",
                "call_count": state.get("call_count", 0) + 1,
                "token_usage": updated_token_usage
            }
        except Exception as e:
            error_msg = f"보고서 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "final_report": f"보고서 생성 실패: {error_msg}",
                "status": "error"
            }
    
    # 조건부 함수: 실행 결과 검증 후 재시도 여부 판단
    def should_retry_after_validation(state: CSVAnalysisState) -> str:
        """실행 결과 검증 후 재시도 여부 판단"""
        retry_needed = state.get("retry_needed", False)
        if retry_needed:
            print("🔄 재시도 필요 - 프롬프트 보강으로 돌아감")
            return "retry"
        print("✅ 검증 통과 - 결과 분석으로 진행")
        return "analyze"
    
    # 조건부 함수: 실행 결과 분석 후 다음 액션 결정
    def should_continue_analysis(state: CSVAnalysisState) -> str:
        """실행 결과 분석 후 추가 분석 필요 여부 판단"""
        next_action = state.get("next_action", "generate_report")
        if next_action == "continue_analysis":
            print("🔄 추가 분석 필요 - 프롬프트 보강으로 돌아가서 더 깊이 있는 분석 수행")
            return "continue_analysis"
        print("✅ 충분한 정보 수집됨 - 보고서 생성으로 진행")
        return "generate_report"
    
    # LangGraph 그래프 구성
    graph = StateGraph(CSVAnalysisState)
    
    # 조건부 함수: 코드 생성 후 검증 필요 여부 판단 (코딩 에이전트가 이미 검증한 경우 스킵)
    def should_validate_code_after_generation(state: CSVAnalysisState) -> str:
        """코드 생성 후 검증 필요 여부 판단
        
        코딩 에이전트가 이미 검증 완료한 경우 재검증 스킵
        """
        status = state.get("status", "")
        code_syntax_valid = state.get("code_syntax_valid", None)
        
        # 코딩 에이전트가 이미 검증 완료한 경우 재검증 스킵
        if status == "code_generated_and_validated" and code_syntax_valid is True:
            print("✅ 코딩 에이전트에서 이미 검증 완료 - 재검증 스킵하고 바로 실행")
            return "execute"
        
        # 검증이 필요한 경우
        print("🔍 코드 검증 필요 - 검증 노드로 진행")
        return "validate"
    
    # 조건부 함수: 코드 문법 검증 후 실행 여부 판단
    def should_execute_after_syntax_validation(state: CSVAnalysisState) -> str:
        """코드 문법 검증 후 실행 여부 판단"""
        code_syntax_valid = state.get("code_syntax_valid", True)
        if code_syntax_valid:
            print("✅ 문법 검증 통과 - 코드 실행으로 진행")
            return "execute"
        print("❌ 문법 검증 실패 - 코드 수정 필요")
        return "fix_syntax"
    
    # 노드 추가
    graph.add_node("validate_environment", validate_environment_node)
    graph.add_node("read_csv_metadata", read_csv_metadata_node)
    graph.add_node("augment_prompt", augment_prompt_node)  # Orchestrator가 프롬프트 보강
    
    # CodeGeneration Agent를 subgraph로 직접 추가 (내부 구조가 LangGraph Studio에서 보임)
    if CODE_GENERATION_AGENT_AVAILABLE and code_generation_agent is not None:
        graph.add_node("code_generation", code_generation_agent)  # 컴파일된 그래프를 subgraph로 직접 추가
        print("✅ CodeGeneration Agent를 subgraph로 추가 완료")
    else:
        # 폴백: 기존 방식 (Worker 모델 직접 사용)
        graph.add_node("generate_analysis_code", generate_analysis_code_node)  # Worker가 코드 생성
        graph.add_node("validate_code_syntax", validate_code_syntax_node)  # 코드 문법 검증
    
    graph.add_node("execute_code", execute_code_node)  # 도커 환경에서 코드 실행
    graph.add_node("validate_execution_result", validate_execution_result_node)  # Phase 1: 실행 결과 검증
    graph.add_node("analyze_execution_result", analyze_execution_result_node)  # Phase 1: 실행 결과 분석 및 다음 액션 결정
    graph.add_node("generate_final_report", generate_final_report_node)  # Orchestrator가 보고서 생성
    
    # 엣지 구성
    # 환경 검증 → CSV 읽기 → 프롬프트 보강(Orchestrator) → 코드 생성(CodeGeneration Agent subgraph) 
    # → 실행(도커) → 결과 검증 → 결과 분석 → (조건부) 추가 분석 또는 보고서 생성
    graph.add_edge(START, "validate_environment")
    graph.add_edge("validate_environment", "read_csv_metadata")
    graph.add_edge("read_csv_metadata", "augment_prompt")  # 메타데이터 읽기 후 프롬프트 보강
    
    if CODE_GENERATION_AGENT_AVAILABLE and code_generation_agent is not None:
        # CodeGeneration Agent subgraph 사용: 프롬프트 보강 후 코드 생성 subgraph로 직접 연결
        graph.add_edge("augment_prompt", "code_generation")  # Orchestrator → CodeGeneration Agent subgraph
        # CodeGeneration Agent subgraph가 완료되면 (END) 자동으로 다음 노드로 진행
        graph.add_edge("code_generation", "execute_code")  # CodeGeneration Agent → 실행
    else:
        # 폴백: 기존 방식
        graph.add_edge("augment_prompt", "generate_analysis_code")  # Orchestrator → Worker: 향상된 프롬프트 전달
        
        # 조건부 엣지: 코드 생성 후 검증 필요 여부 판단 (코딩 에이전트가 이미 검증한 경우 스킵)
        graph.add_conditional_edges(
            "generate_analysis_code",
            should_validate_code_after_generation,
            {
                "execute": "execute_code",  # 코딩 에이전트가 이미 검증 완료: 바로 실행
                "validate": "validate_code_syntax"  # 검증 필요: 검증 노드로 진행
            }
        )
        
        # 조건부 엣지: 문법 검증 후 실행 여부 판단
        graph.add_conditional_edges(
            "validate_code_syntax",
            should_execute_after_syntax_validation,
            {
                "execute": "execute_code",  # 문법 검증 통과: 코드 실행
                "fix_syntax": "generate_analysis_code"  # 문법 검증 실패: 코드 재생성
            }
        )
    
    # execute_code는 code_generation subgraph와 폴백 경로 모두에서 사용
    graph.add_edge("execute_code", "validate_execution_result")  # Phase 1: 실행 후 결과 검증
    
    # 조건부 엣지: 결과 검증 후 재시도 여부 판단
    graph.add_conditional_edges(
        "validate_execution_result",
        should_retry_after_validation,
        {
            "retry": "augment_prompt",  # 재시도: 프롬프트 보강으로 돌아가서 다시 분석
            "analyze": "analyze_execution_result"  # 검증 통과: 결과 분석
        }
    )
    
    # 조건부 엣지: 결과 분석 후 추가 분석 필요 여부 판단
    graph.add_conditional_edges(
        "analyze_execution_result",
        should_continue_analysis,
        {
            "continue_analysis": "augment_prompt",  # 추가 분석: 프롬프트 보강으로 돌아가서 더 깊이 있는 분석
            "generate_report": "generate_final_report"  # 보고서 생성: 충분한 정보 수집됨
        }
    )
    
    graph.add_edge("generate_final_report", END)
    
    # 그래프 컴파일 (Checkpointer 포함)
    if checkpointer:
        compiled_graph = graph.compile(checkpointer=checkpointer)
        print("✅ CSV Data Analysis Agent가 성공적으로 생성되었습니다.")
        print(f"   Orchestrator 모델: {model} (프롬프트 향상, 보고서 작성)")
        print(f"   Worker 모델: {code_generation_model} (코드 생성)")
        print(f"   Human-in-the-Loop: 활성화됨 ✅")
        print(f"   🔄 Phase 1 개선: 반복적 분석 루프 활성화 (최대 {3}회)")
    else:
        compiled_graph = graph.compile()
        print("✅ CSV Data Analysis Agent가 성공적으로 생성되었습니다.")
        print(f"   Orchestrator 모델: {model} (프롬프트 향상, 보고서 작성)")
        print(f"   Worker 모델: {code_generation_model} (코드 생성)")
        print(f"   Human-in-the-Loop: 비활성화됨")
        print(f"   🔄 Phase 1 개선: 반복적 분석 루프 활성화 (최대 {3}회)")
    
    return compiled_graph


# LangGraph Studio용 agent 변수
_agent_cache = None

def _get_default_agent():
    """기본 CSV Data Analysis Agent 그래프 생성 (lazy initialization with caching)"""
    global _agent_cache
    if _agent_cache is None:
        try:
            _agent_cache = create_csv_data_analysis_agent()
        except Exception as e:
            import traceback
            error_msg = f"⚠️ 에이전트 생성 실패: {str(e)}"
            print(error_msg)
            print("   환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요.")
            print("   상세 에러:")
            traceback.print_exc()
            # LangGraph Studio는 None이 아닌 Graph 객체를 기대하므로 예외를 다시 발생시킴
            raise
    return _agent_cache

# LangGraph Studio에서 참조할 agent 변수
# LangGraph Studio는 None이 아닌 Graph 객체를 기대하므로 예외 발생 시에도 재시도하도록 함
try:
    agent = _get_default_agent()
except Exception as e:
    # LangGraph Studio가 로드할 때 예외가 발생하면, 에러 메시지를 출력하고 다시 시도
    import traceback
    print(f"❌ CSV Data Analysis Agent 초기화 실패:")
    traceback.print_exc()
    # None을 반환하면 LangGraph Studio가 에러를 표시함
    # 대신 예외를 다시 발생시켜서 명확한 에러 메시지를 표시
    raise RuntimeError(
        f"CSV Data Analysis Agent를 초기화할 수 없습니다: {str(e)}\n"
        "환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요."
    ) from e

