"""
Code Generation Agent - 범용 코드 생성 에이전트

다양한 도메인(CSV 분석, 웹 개발, API 개발 등)에서 코드를 생성하는 범용 에이전트입니다.

워크플로우:
1. 요구사항 분석
2. 코드 생성 (Worker 모델)
3. 코드 검증
4. 코드 실행 (선택적)
5. 코드 수정 (필요시)

설계 원칙:
- 범용성: 다양한 도메인 지원
- 모듈성: 명확한 인터페이스
- 확장성: 새로운 도메인 추가 용이
"""

import os
import re
import json
import threading
from typing import Dict, Any, Optional, Literal
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END, MessagesState

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.paths import (
    get_workspace_subdirectories,
    get_project_root,
    get_data_directory,
    get_workspace_directory,
    resolve_data_file_path
)
from src.utils.errors import (
    ExecutionError,
    format_error_message,
    format_error_for_state
)
from src.tools.planning import write_todos_tool
from src.tools.filesystem import ls_tool, read_file_tool, write_file_tool, edit_file_tool
# 새로운 통합 코드 실행 시스템 사용
from src.tools.code_execution import (
    CodeExecutionFactory,
    ExecutionEnvironment,
    ExecutionConfig,
    execute_code_in_docker
)
from src.tools.code_execution.utils import extract_context_from_result
from .state import CodeGenerationState
from .prompts import (
    get_code_generation_system_prompt,
    create_code_generation_user_prompt,
    CODE_VALIDATION_SYSTEM_PROMPT,
    CODE_FIXING_SYSTEM_PROMPT
)
from .auto_fix import auto_fix_syntax_errors


# ========== Workspace 디렉토리 관리 함수 ==========

def _setup_workspace_directories() -> Dict[str, Path]:
    """Workspace 디렉토리 구조 생성 및 반환"""
    return get_workspace_subdirectories()


# ========== 파일 경로 추출 유틸리티 함수 ==========

def _extract_natural_language_query_from_messages(messages: list) -> str:
    """메시지 리스트에서 자연어 쿼리 추출
    
    Args:
        messages: LangChain 메시지 리스트
        
    Returns:
        추출된 자연어 쿼리 문자열
    """
    if not messages:
        return ""
    
    # 마지막 HumanMessage에서 내용 추출
    for message in reversed(messages):
        message_content = None
        
        # HumanMessage 객체인 경우
        if isinstance(message, HumanMessage):
            message_content = message.content if hasattr(message, 'content') else str(message)
        # 딕셔너리 형식인 경우 (LangGraph Studio에서 전달되는 형식)
        elif isinstance(message, dict):
            # role이 "user"이거나 type이 "human"인 경우
            if message.get("role") == "user" or message.get("type") == "human":
                message_content = message.get("content", "")
            # content만 있는 경우
            elif "content" in message:
                message_content = message.get("content", "")
        
        if message_content:
            return message_content
    
    return ""


def _normalize_file_path(filepath: str) -> str:
    """파일 경로 정규화 헬퍼 함수
    
    Args:
        filepath: 파일 경로 문자열
        
    Returns:
        정규화된 파일 경로 문자열
    """
    if not filepath:
        return ""
    
    try:
        # resolve_data_file_path를 사용하여 경로 해석
        resolved_path = resolve_data_file_path(filepath)
        filepath = str(resolved_path)
    except Exception:
        # 경로 해석 실패 시 기존 방식으로 폴백
        if not filepath.startswith("/"):
            if "/" not in filepath:
                # 파일명만 있는 경우
                data_dir = get_data_directory()
                filepath = str(data_dir / filepath)
            else:
                # 상대 경로인 경우
                project_root = get_project_root()
                filepath = str(project_root / filepath)
    
    # 중복된 경로 수정 및 tests -> data 변환 (하위 호환성)
    if "/data/data/" in filepath:
        filepath = filepath.replace("/data/data/", "/data/")
    if "/tests/tests/" in filepath:
        filepath = filepath.replace("/tests/tests/", "/data/")
    if "/tests/" in filepath and not filepath.startswith("/tests/"):
        # tests/ 경로를 data/로 변환 (하위 호환성)
        filepath = filepath.replace("/tests/", "/data/")
    
    return filepath


def _extract_file_paths_from_query(
    query: str,
    file_extensions: list = None
) -> list[str]:
    """Query에서 파일 경로 추출 (규칙 기반)
    
    Args:
        query: 자연어 쿼리 문자열
        file_extensions: 추출할 파일 확장자 리스트 (기본값: ['.csv', '.xlsx', '.json'])
        
    Returns:
        추출된 파일 경로 리스트
    """
    if file_extensions is None:
        file_extensions = ['.csv', '.xlsx', '.json', '.tsv']
    
    if not query:
        return []
    
    # 파일 경로 패턴 매칭
    file_paths = []
    
    # 각 확장자별 패턴 생성
    for ext in file_extensions:
        # 확장자 없이 매칭을 위해 ext에서 . 제거
        ext_pattern = ext.replace('.', '')
        
        patterns = [
            rf'([\w/\.\-]+{re.escape(ext)})',  # 파일명 패턴
            rf'["\']([^"\']+{re.escape(ext)})["\']',  # 따옴표로 감싼 파일명
            rf'파일[:\s]+([^\s]+{re.escape(ext)})',  # "파일: xxx.ext" 패턴
            rf'{ext_pattern.upper()}[:\s]+([^\s]+{re.escape(ext)})',  # "CSV: xxx.csv" 패턴
            rf'/(?:home|workspace|data|workspace)/[^\s]+{re.escape(ext)}',  # 절대 경로 패턴
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                if match and match not in file_paths:
                    file_paths.append(match)
    
    # 파일 경로 정규화
    normalized_paths = []
    for filepath in file_paths:
        normalized = _normalize_file_path(filepath)
        if normalized:
            # 파일이 실제로 존재하는지 확인
            path_obj = Path(normalized)
            if path_obj.exists():
                normalized_paths.append(normalized)
            else:
                # 존재하지 않아도 추가 (나중에 확인)
                normalized_paths.append(normalized)
    
    # 중복 제거
    unique_paths = []
    for path in normalized_paths:
        if path not in unique_paths:
            unique_paths.append(path)
    
    return unique_paths


def _save_code_to_workspace(
    code: str,
    directory: str = "generated_code",
    prefix: str = "code"
) -> Path:
    """코드를 workspace 디렉토리에 파일로 저장
    
    Args:
        code: 저장할 코드 문자열
        directory: 저장할 디렉토리 (generated_code, approved_code, executed_code)
        prefix: 파일명 접두사
        
    Returns:
        저장된 파일 경로
    """
    directories = _setup_workspace_directories()
    
    if directory not in directories:
        raise ValueError(f"잘못된 디렉토리: {directory}")
    
    target_dir = directories[directory]
    
    # 타임스탬프 기반 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.py"
    file_path = target_dir / filename
    
    # 파일 저장
    file_path.write_text(code, encoding='utf-8')
    
    print(f"💾 코드 파일 저장: {file_path}")
    
    return file_path


# ========== 코드 추출 함수 ==========

def _extract_code_from_response(response: Any) -> str:
    """응답에서 코드 블록 추출
    
    Args:
        response: LLM 응답 객체 또는 문자열
        
    Returns:
        추출된 코드 문자열
    """
    content = response.content if hasattr(response, 'content') else str(response)
    
    # 코드 블록 추출 (```python ... ``` 형식)
    if "```python" in content:
        code_start = content.find("```python") + 9
        code_end = content.find("```", code_start)
        if code_end != -1:
            return content[code_start:code_end].strip()
    elif "```" in content:
        code_start = content.find("```") + 3
        code_end = content.find("```", code_start)
        if code_end != -1:
            return content[code_start:code_end].strip()
    
    # 코드 블록이 없으면 전체 내용 반환
    return content.strip()


# ========== 노드 함수들 ==========

def planning_node(
    state: CodeGenerationState,
    orchestrator_model: Any
) -> CodeGenerationState:
    """노드 0: 작업 계획 수립 (Planning Tool 사용)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("📋 [Code Generation Agent] 작업 계획 수립 중...")
    print("📋 [Code Generation Agent] 작업 계획 수립 중...")
    
    task_description = state.get("task_description", "")
    planning_result_existing = state.get("planning_result")
    
    # Planning이 이미 완료된 경우 스킵
    if planning_result_existing:
        logger.info(f"✅ Planning이 이미 완료됨 (기존 planning_result 존재)")
        print(f"✅ Planning이 이미 완료됨 (기존 planning_result 존재)")
        return {
            "status": "planned",
            "call_count": state.get("call_count", 0)
        }
    
    if not task_description:
        logger.warning(f"⚠️ 작업 설명이 없어 Planning을 건너뜁니다. (task_description: {task_description})")
        print(f"⚠️ 작업 설명이 없어 Planning을 건너뜁니다. (task_description: {task_description})")
        return {
            "status": "planning_skipped",
            "call_count": state.get("call_count", 0)
        }
    
    logger.info(f"📋 Planning 시작: task_description 길이={len(task_description)} 문자")
    print(f"📋 Planning 시작: task_description 길이={len(task_description)} 문자")
    
    try:
        # Orchestrator 모델로 작업을 하위 작업으로 분해
        planning_prompt = f"""다음 작업을 분석하여 하위 작업으로 분해하세요:

작업: {task_description}

**중요 제약사항:**
- 하위 작업 수는 최소 3개, 최대 7개로 제한하세요
- 작업을 너무 세분화하지 말고, 관련된 작업들을 하나의 큰 단위로 묶어서 설계하세요
- 각 하위 작업은 여러 단계를 포함할 수 있는 의미 있는 단위여야 합니다
- 예: "데이터 로드 및 전처리", "데이터 분석 및 시각화", "결과 검증 및 보고서 생성"

하위 작업들을 JSON 배열 형식으로 나열하세요.
예: ["하위 작업 1", "하위 작업 2", "하위 작업 3"]

하위 작업 목록만 출력하세요 (설명 없이)."""
        
        response = orchestrator_model.invoke([
            SystemMessage(content="당신은 작업 계획 수립 전문가입니다. 복잡한 작업을 명확하고 적절한 수의 하위 작업으로 분해하세요. 작업을 너무 세분화하지 말고, 관련된 작업들을 하나의 큰 단위로 묶어서 설계하세요."),
            HumanMessage(content=planning_prompt)
        ])
        
        # 응답에서 하위 작업 추출
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # JSON 배열 추출 시도
        subtasks = []
        try:
            # JSON 배열 형식으로 파싱 시도
            if "[" in response_text and "]" in response_text:
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                json_str = response_text[json_start:json_end]
                subtasks = json.loads(json_str)
        except Exception:
            # JSON 파싱 실패 시 줄 단위로 분리
            lines = [line.strip().strip('"').strip("'") for line in response_text.split('\n') if line.strip()]
            subtasks = [line for line in lines if line and not line.startswith('#')]
        
        # 작업 수 제한: 최소 3개, 최대 7개
        if len(subtasks) > 7:
            logger.warning(f"⚠️ 생성된 작업 수({len(subtasks)}개)가 최대 제한(7개)을 초과했습니다. 작업을 통합합니다.")
            print(f"⚠️ 생성된 작업 수({len(subtasks)}개)가 최대 제한(7개)을 초과했습니다. 작업을 통합합니다.")
            
            # 작업을 7개로 통합 (비슷한 작업들을 묶음)
            # 간단한 방법: 처음 7개만 사용하거나, 작업을 그룹화
            # 더 나은 방법: LLM에게 다시 요청하거나, 관련 작업들을 묶기
            # 여기서는 간단하게 처음 7개만 사용하고, 나머지는 마지막 작업에 통합
            if len(subtasks) > 7:
                # 마지막 작업에 나머지 작업들을 통합
                remaining_tasks = subtasks[6:]
                subtasks = subtasks[:6]  # 처음 6개
                if remaining_tasks:
                    # 마지막 작업에 나머지 통합
                    subtasks.append(f"{subtasks[-1]} 및 {', '.join(remaining_tasks[:3])}" + (" 등" if len(remaining_tasks) > 3 else ""))
                else:
                    subtasks = subtasks[:7]
            
            logger.info(f"✅ 작업 통합 완료: {len(subtasks)}개의 하위 작업으로 축소")
            print(f"✅ 작업 통합 완료: {len(subtasks)}개의 하위 작업으로 축소")
        
        elif len(subtasks) < 3 and len(subtasks) > 0:
            logger.warning(f"⚠️ 생성된 작업 수({len(subtasks)}개)가 최소 제한(3개)보다 적습니다.")
            print(f"⚠️ 생성된 작업 수({len(subtasks)}개)가 최소 제한(3개)보다 적습니다.")
            # 작업이 너무 적으면 그대로 사용 (작업이 단순할 수 있음)
        
        # Planning Tool 호출
        planning_result = write_todos_tool.invoke({
            "task": task_description,
            "subtasks": subtasks if subtasks else None
        })
        
        # Planning 결과 파싱
        try:
            planning_data = json.loads(planning_result)
            todos = planning_data.get("todos", [])
        except Exception:
            todos = []
        
        # 작업 수 검증
        if len(todos) > 7:
            logger.warning(f"⚠️ Planning 결과: {len(todos)}개의 하위 작업 생성됨 (권장: 최대 7개)")
            print(f"⚠️ Planning 결과: {len(todos)}개의 하위 작업 생성됨 (권장: 최대 7개)")
        elif len(todos) < 3 and len(todos) > 0:
            logger.info(f"ℹ️ Planning 결과: {len(todos)}개의 하위 작업 생성됨 (권장: 최소 3개, 작업이 단순할 수 있음)")
            print(f"ℹ️ Planning 결과: {len(todos)}개의 하위 작업 생성됨 (권장: 최소 3개, 작업이 단순할 수 있음)")
        else:
            logger.info(f"✅ Planning 완료: {len(todos)}개의 하위 작업 생성 (권장 범위: 3-7개)")
            print(f"✅ Planning 완료: {len(todos)}개의 하위 작업 생성 (권장 범위: 3-7개)")
        
        if todos:
            logger.info(f"   하위 작업 목록: {[todo.get('description', todo.get('task', str(todo))) for todo in todos]}")
            print(f"   하위 작업 목록:")
            for i, todo in enumerate(todos, 1):
                todo_desc = todo.get("description", todo.get("task", str(todo)))
                logger.info(f"     {i}. {todo_desc}")
                print(f"     {i}. {todo_desc}")
        
        return {
            "planning_result": planning_result,
            "planning_todos": todos,
            "current_subtask": 0,
            "status": "planned",
            "call_count": state.get("call_count", 0) + 1
        }
        
    except Exception as e:
        error_msg = f"Planning 실패: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "errors": [error_msg],
            "status": "planning_failed",
            "call_count": state.get("call_count", 0) + 1
        }


def analyze_requirements_node(state: CodeGenerationState) -> CodeGenerationState:
    """노드 1: 요구사항 분석 및 파일 경로 추출
    
    Query에서 파일 경로를 추출하여 context에 설정합니다.
    """
    print("🔍 [Code Generation Agent] 요구사항 분석 중...")
    
    task_description = state.get("task_description", "")
    requirements = state.get("requirements", "")
    context = state.get("context", {}) or {}
    messages = state.get("messages", [])
    
    # 메시지에서 자연어 쿼리 추출 (파일 경로 추출용)
    natural_language_query = ""
    if messages:
        natural_language_query = _extract_natural_language_query_from_messages(messages)
    
    # task_description이 있으면 쿼리로 사용
    if not natural_language_query and task_description:
        natural_language_query = task_description
    
    # 파일 경로 추출 (context에 없을 경우에만)
    extracted_file_paths = []
    csv_file_path = context.get("csv_file_path", "")
    csv_file_paths = context.get("csv_file_paths", [])
    
    # Query에서 파일 경로 추출 (context에 파일 경로가 없는 경우)
    if not csv_file_path and not csv_file_paths and natural_language_query:
        print("📥 Query에서 파일 경로 추출 중...")
        extracted_file_paths = _extract_file_paths_from_query(natural_language_query)
        
        if extracted_file_paths:
            # 존재하는 파일만 필터링
            existing_paths = []
            for path_str in extracted_file_paths:
                path_obj = Path(path_str).expanduser()
                if path_obj.exists():
                    existing_paths.append(str(path_obj.resolve()))
                else:
                    # 절대 경로가 아니면 상대 경로로 시도
                    normalized = _normalize_file_path(path_str)
                    normalized_obj = Path(normalized).expanduser()
                    if normalized_obj.exists():
                        existing_paths.append(str(normalized_obj.resolve()))
            
            if existing_paths:
                if len(existing_paths) == 1:
                    csv_file_path = existing_paths[0]
                    print(f"✅ 파일 경로 추출 완료 (단일 파일): {csv_file_path}")
                else:
                    csv_file_paths = existing_paths
                    print(f"✅ 파일 경로 추출 완료 (다중 파일): {len(csv_file_paths)}개")
                
                # context 업데이트
                if csv_file_path:
                    context["csv_file_path"] = csv_file_path
                    # CSV 분석 도메인으로 설정
                    if "domain" not in context:
                        context["domain"] = "csv_analysis"
                elif csv_file_paths:
                    context["csv_file_paths"] = csv_file_paths
                    # CSV 분석 도메인으로 설정
                    if "domain" not in context:
                        context["domain"] = "csv_analysis"
            else:
                print(f"⚠️ 파일 경로를 찾았지만 파일이 존재하지 않습니다: {extracted_file_paths}")
        else:
            print("ℹ️ Query에서 파일 경로를 찾을 수 없습니다.")
    
    # 요구사항이 이미 제공된 경우 그대로 사용
    result_state = {
        "status": "requirements_analyzed",
        "call_count": state.get("call_count", 0)
    }
    
    if requirements:
        print("✅ 요구사항이 이미 제공됨")
        if context:
            result_state["context"] = context
        return result_state
    
    # 요구사항이 없으면 task_description을 requirements로 사용
    if task_description:
        print("✅ task_description을 requirements로 사용")
        result_state["requirements"] = task_description
        if context:
            result_state["context"] = context
        return result_state
    
    # context 업데이트
    if context:
        result_state["context"] = context
    
    return result_state


def generate_code_node(
    state: CodeGenerationState,
    worker_model: Any
) -> CodeGenerationState:
    """노드 2: 코드 생성 (Worker 모델 사용)
    
    이전 실행 결과의 context를 활용하여 다음 코드 생성에 반영
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("💻 [Code Generation Agent] 코드 생성 중...")
    print("💻 [Code Generation Agent] 코드 생성 중...")
    
    task_description = state.get("task_description", "")
    requirements = state.get("requirements", "")
    context = state.get("context", {}) or {}
    
    # 이전 실행 결과의 context 활용
    execution_context = state.get("execution_context")
    if execution_context:
        print("📊 이전 실행 결과의 context를 활용합니다:")
        if execution_context.get("stdout_summary"):
            print(f"   📝 stdout 요약: {execution_context['stdout_summary'][:100]}...")
        if execution_context.get("statistics"):
            print(f"   📈 통계 정보: {len(execution_context['statistics'])}개 항목")
        if execution_context.get("extracted_data"):
            print(f"   📊 추출된 데이터: {len(execution_context['extracted_data'])}개 항목")
        
        # context에 execution_context 통합
        if "previous_execution" not in context:
            context["previous_execution"] = {}
        context["previous_execution"]["context"] = execution_context
        context["previous_execution"]["stdout_summary"] = execution_context.get("stdout_summary", "")
        context["previous_execution"]["statistics"] = execution_context.get("statistics", {})
        context["previous_execution"]["extracted_data"] = execution_context.get("extracted_data", {})
        context["previous_execution"]["insights"] = execution_context.get("insights", [])
    
    # 도메인 추출
    domain = context.get("domain", "general") if context else "general"
    
    # Docker 경로 정보 계산 및 context에 추가 (프롬프트에 포함하기 위해)
    # 코드 파일 경로는 나중에 생성되므로, 예상되는 코드 디렉토리 사용
    if domain == "csv_analysis" and context:
        from src.utils.paths import get_workspace_subdirectories
        directories = get_workspace_subdirectories()
        # 코드는 generated_code 디렉토리에 생성될 것으로 예상
        expected_code_dir = str(directories.get("generated_code", Path("workspace/generated_code")))
        
        csv_file_path = context.get("csv_file_path", "")
        csv_file_paths = context.get("csv_file_paths", [])
        
        # 단일 파일의 Docker 경로 계산
        if csv_file_path:
            csv_path_obj = Path(csv_file_path).expanduser()
            if csv_path_obj.exists():
                csv_path_obj = csv_path_obj.resolve()
                csv_parent = str(csv_path_obj.parent)
                
                # 코드와 같은 디렉토리인지 확인
                if csv_parent == expected_code_dir:
                    docker_path = f"/workspace/code/{csv_path_obj.name}"
                else:
                    docker_path = f"/workspace/data/{csv_path_obj.name}"
                
                context["docker_file_path"] = docker_path
                context["filepath_example"] = f'filepath = "{docker_path}"'
        
        # 여러 파일의 Docker 경로 계산
        if csv_file_paths:
            docker_paths = []
            filepath_examples = []
            for i, csv_path_str in enumerate(csv_file_paths):
                csv_path_obj = Path(csv_path_str).expanduser()
                if csv_path_obj.exists():
                    csv_path_obj = csv_path_obj.resolve()
                    csv_parent = str(csv_path_obj.parent)
                    
                    # 코드와 같은 디렉토리인지 확인
                    if csv_parent == expected_code_dir:
                        docker_path = f"/workspace/code/{csv_path_obj.name}"
                    else:
                        docker_path = f"/workspace/data/{csv_path_obj.name}"
                    
                    docker_paths.append(docker_path)
                    if i == 0:
                        filepath_examples.append(f'filepath = "{docker_path}"')
                    else:
                        filepath_examples.append(f'filepath_{i+1} = "{docker_path}"')
            
            if docker_paths:
                context["docker_file_paths"] = docker_paths
                context["filepath_examples"] = filepath_examples
        
        # 출력 디렉토리 정보
        output_dir_str = context.get("output_directory", "")
        if output_dir_str:
            context["docker_output_path"] = "/workspace/results"
            context["output_path_example"] = 'output_path = "/workspace/results/output.png"'
    
    # 시스템 프롬프트 가져오기
    system_prompt = get_code_generation_system_prompt(domain)
    
    # 사용자 프롬프트 생성
    user_prompt = create_code_generation_user_prompt(
        task_description=task_description,
        requirements=requirements,
        context=context
    )
    
    try:
        # Worker 모델로 코드 생성
        print(f"🤖 Worker 모델로 코드 생성 중... (도메인: {domain})")
        response = worker_model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # 코드 추출
        generated_code = _extract_code_from_response(response)
        
        print(f"✅ 코드 생성 완료 ({len(generated_code)} 문자)")
        
        # 코드를 파일로 저장
        try:
            code_file = _save_code_to_workspace(
                code=generated_code,
                directory="generated_code",
                prefix="code"
            )
            code_file_path = str(code_file)
        except Exception as e:
            print(f"⚠️ 코드 파일 저장 실패: {str(e)} (계속 진행)")
            code_file_path = None
        
        return {
            "generated_code": generated_code,
            "generated_code_file": code_file_path,
            "status": "code_generated",
            "call_count": state.get("call_count", 0) + 1
        }
        
    except Exception as e:
        error_msg = f"코드 생성 실패: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "errors": [error_msg],
            "status": "error",
            "call_count": state.get("call_count", 0) + 1
        }


def validate_code_syntax_node(state: CodeGenerationState) -> CodeGenerationState:
    """노드 3: 코드 문법 검증"""
    print("✅ [Code Generation Agent] 코드 문법 검증 중...")
    
    # fixed_code가 있으면 우선 사용 (수정된 코드), 없으면 generated_code 사용
    code_to_validate = state.get("fixed_code") or state.get("generated_code", "")
    
    # 파일에서 코드를 읽어서 검증 (파일이 있으면)
    generated_code_file = state.get("generated_code_file")
    if generated_code_file and not code_to_validate:
        try:
            code_file_path = Path(generated_code_file)
            if code_file_path.exists():
                code_to_validate = code_file_path.read_text(encoding='utf-8')
                print(f"📄 파일에서 코드 읽기: {generated_code_file}")
        except Exception as e:
            print(f"⚠️ 파일 읽기 실패: {str(e)}")
    
    if not code_to_validate:
        return {
            "code_syntax_valid": False,
            "syntax_errors": ["검증할 코드가 없습니다."],
            "status": "validation_failed"
        }
    
    # 간단한 문법 검증 (Python)
    syntax_errors = []
    
    try:
        # Python 문법 검증 (AST 파싱 사용 - 더 정확함)
        import ast
        try:
            tree = ast.parse(code_to_validate)
            code_syntax_valid = True
            print("✅ 문법 검증 통과 (AST 파싱)")
            
            # 변수명 검증 추가 (CSV 분석 도메인인 경우)
            context = state.get("context", {})
            domain = context.get("domain", "")
            
            if domain == "csv_analysis":
                # 변수 정의 및 사용 수집
                defined_vars = set()
                used_vars = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defined_vars.add(target.id)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        # 내장 함수/상수 제외
                        if node.id not in dir(__builtins__):
                            used_vars.add(node.id)
                
                # filepath 관련 변수 확인
                filepath_vars = {var for var in used_vars if var.startswith('filepath')}
                undefined_filepath_vars = filepath_vars - defined_vars
                
                if undefined_filepath_vars:
                    var_list = ', '.join(sorted(undefined_filepath_vars))
                    error_msg = f"변수 정의 오류: {var_list} 변수가 사용되지만 정의되지 않았습니다. 코드에서 이 변수들을 정의하거나 올바른 변수명을 사용하세요."
                    syntax_errors.append(error_msg)
                    code_syntax_valid = False
                    print(f"❌ 변수명 검증 실패: {error_msg}")
        except SyntaxError as e:
            # 핵심: 프로그램으로 자동 수정 시도
            print(f"🔧 Syntax 에러 발견: {e.msg} - 자동 수정 시도 중...")
            context = state.get("context", {})
            fixed_code, auto_fix_success = auto_fix_syntax_errors(code_to_validate, e, context)
            
            if auto_fix_success:
                # 자동 수정 성공 - 재검증
                try:
                    ast.parse(fixed_code)
                    code_syntax_valid = True
                    code_to_validate = fixed_code  # 수정된 코드 사용
                    print("✅ 프로그램으로 자동 수정 완료!")
                except SyntaxError as e2:
                    # 자동 수정 후에도 에러가 있으면 LLM 필요
                    code_syntax_valid = False
                    error_msg = f"자동 수정 후에도 문법 오류 (라인 {e2.lineno}): {e2.msg}"
                    if e2.text:
                        error_msg += f"\n  코드: {e2.text.strip()}"
                    syntax_errors.append(error_msg)
                    print(f"❌ {error_msg} - LLM 수정 필요")
            else:
                # 자동 수정 실패 → LLM 필요
                code_syntax_valid = False
                error_msg = f"문법 오류 (자동 수정 불가, 라인 {e.lineno}): {e.msg}"
                if e.text:
                    error_msg += f"\n  코드: {e.text.strip()}"
                    if e.offset:
                        error_msg += f"\n  위치: {' ' * (e.offset - 1)}^"
                syntax_errors.append(error_msg)
                print(f"❌ {error_msg} - LLM 수정 필요")
        
        # 검증 통과 시 fixed_code를 generated_code로 업데이트
        if state.get("fixed_code") and code_syntax_valid:
            print("✅ 수정된 코드가 검증 통과 - generated_code 업데이트")
    except SyntaxError as e:
        code_syntax_valid = False
        error_msg = f"문법 오류 (라인 {e.lineno}): {e.msg}"
        if e.text:
            error_msg += f"\n  코드: {e.text.strip()}"
            if e.offset:
                error_msg += f"\n  위치: {' ' * (e.offset - 1)}^"
        syntax_errors.append(error_msg)
        print(f"❌ {error_msg}")
    except Exception as e:
        # 기타 오류는 문법 오류로 간주하지 않음
        code_syntax_valid = True
        print(f"⚠️ 문법 검증 중 예외 발생 (무시): {str(e)}")
    
    result = {
        "code_syntax_valid": code_syntax_valid,
        "syntax_errors": syntax_errors if syntax_errors else [],  # 빈 리스트로 명확히 표시 (검증 수행됨)
        "code_valid": code_syntax_valid,  # 하위 호환성
        "validation_errors": syntax_errors if syntax_errors else [],  # 빈 리스트로 명확히 표시 (검증 수행됨)
        "status": "validated" if code_syntax_valid else "validation_failed"
    }
    
    # 자동 수정된 코드 또는 fixed_code를 generated_code로 업데이트
    if code_syntax_valid:
        if code_to_validate != (state.get("fixed_code") or state.get("generated_code", "")):
            # 자동 수정된 코드
            result["generated_code"] = code_to_validate
            result["auto_fixed"] = True
        elif state.get("fixed_code"):
            # LLM으로 수정된 코드
            result["generated_code"] = state.get("fixed_code")
            result["fixed_code"] = None  # 사용 완료 후 정리
    
    return result


def fix_code_node(
    state: CodeGenerationState,
    worker_model: Any
) -> CodeGenerationState:
    """노드 4: 코드 수정 (에러 기반)"""
    print("🔧 [Code Generation Agent] 코드 수정 중...")
    
    generated_code = state.get("generated_code", "")
    validation_errors = state.get("validation_errors", [])
    syntax_errors = state.get("syntax_errors", [])
    execution_errors = state.get("execution_errors", [])
    fix_iterations = state.get("fix_iterations", 0)
    max_iterations = state.get("max_iterations", 3)
    previous_fix_errors = state.get("previous_fix_errors", [])
    
    # 최대 반복 횟수 확인
    if fix_iterations >= max_iterations:
        error_msg = f"최대 수정 횟수({max_iterations})에 도달했습니다."
        print(f"❌ {error_msg}")
        return {
            "errors": [error_msg],
            "status": "error"
        }
    
    # 모든 오류 수집
    all_errors = []
    if validation_errors:
        all_errors.extend(validation_errors)
    if syntax_errors:
        all_errors.extend(syntax_errors)
    if execution_errors:
        all_errors.extend(execution_errors)
    
    if not all_errors:
        print("⚠️ 수정할 오류가 없습니다.")
        return {
            "fixed_code": generated_code,
            "status": "fixed"
        }
    
    errors_str = "\n".join([f"- {err}" for err in all_errors])
    
    # 이전 수정 이력이 있으면 포함 (핵심: 여러 번 수정하는 과정에서 이전 오류를 다시 놓치지 않도록)
    history_context = ""
    if fix_iterations > 0:
        history_context = f"\n\n**중요: 이전에 {fix_iterations}번 수정을 시도했습니다. 이전에 수정했던 오류들이 다시 발생하지 않도록 주의하세요.**"
        if previous_fix_errors:
            history_context += f"\n이전에 발견된 오류들 (다시 발생하지 않도록 확인):\n" + "\n".join([f"- {err}" for err in previous_fix_errors[:5]])
    
    # 코드 수정 프롬프트
    fix_prompt = f"""다음 코드에 오류가 있습니다. 코드를 수정해주세요:

코드:
```python
{generated_code}
```

오류:
{errors_str}
{history_context}

수정된 코드만 출력하세요 (설명 없이 코드만)."""
    
    try:
        response = worker_model.invoke([
            SystemMessage(content=CODE_FIXING_SYSTEM_PROMPT),
            HumanMessage(content=fix_prompt)
        ])
        
        fixed_code = _extract_code_from_response(response)
        
        print(f"✅ 코드 수정 완료 (반복 {fix_iterations + 1}/{max_iterations})")
        
        # 수정된 코드를 파일로 저장
        try:
            code_file = _save_code_to_workspace(
                code=fixed_code,
                directory="generated_code",
                prefix="code_fixed"
            )
            code_file_path = str(code_file)
        except Exception as e:
            print(f"⚠️ 코드 파일 저장 실패: {str(e)}")
            code_file_path = state.get("generated_code_file")
        
        return {
            "fixed_code": fixed_code,
            "generated_code": fixed_code,  # 수정된 코드를 generated_code로 업데이트
            "generated_code_file": code_file_path,
            "fix_iterations": fix_iterations + 1,
            "previous_fix_errors": all_errors,  # 이전 오류 저장 (다음 수정 시 참조)
            "code_syntax_valid": None,  # 재검증을 위해 리셋 (None으로 설정하여 재검증 수행)
            "syntax_errors": None,  # 재검증을 위해 리셋
            "validation_errors": None,  # 재검증을 위해 리셋
            "status": "fixed",
            "call_count": state.get("call_count", 0) + 1
        }
        
    except Exception as e:
        error_msg = f"코드 수정 실패: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "errors": [error_msg],
            "status": "error",
            "call_count": state.get("call_count", 0) + 1
        }


# ========== 조건부 라우팅 함수 ==========

def tool_executor_node(
    state: CodeGenerationState,
    tools: list
) -> CodeGenerationState:
    """노드 2.5: Tool 실행 (Filesystem Tools 등)"""
    print("🔧 [Code Generation Agent] Tool 실행 중...")

    # 현재는 코드 생성 후 파일 저장에 Filesystem Tool 사용
    generated_code = state.get("generated_code", "")
    target_filepath = state.get("target_filepath")

    if not generated_code:
        print("⚠️ 생성된 코드가 없어 Tool 실행을 건너뜁니다.")
        return {
            "status": "tool_execution_skipped",
            "tool_call_count": state.get("tool_call_count", 0)
        }

    files_created = state.get("files_created", [])
    files_edited = state.get("files_edited", [])

    # target_filepath가 있으면 해당 경로에 파일 생성
    if target_filepath:
        # Path validation: Prevent writes outside allowed directories
        def validate_target_path(filepath: str) -> tuple[bool, str]:
            """Validate that target_filepath is within allowed directories.

            Args:
                filepath: Target file path from LLM output

            Returns:
                Tuple of (is_valid, error_message)
            """
            try:
                # Resolve the path to absolute
                target_path = Path(filepath).resolve()

                # Get allowed directories
                workspace_root = get_workspace_directory()
                data_root = get_data_directory()

                # Check if path is relative to allowed directories
                is_in_workspace = target_path.is_relative_to(workspace_root)
                is_in_data = target_path.is_relative_to(data_root)

                if not (is_in_workspace or is_in_data):
                    error_msg = (
                        f"Security error: target_filepath '{filepath}' is outside allowed directories. "
                        f"Files must be written to workspace/ or data/ directories only. "
                        f"Resolved path: {target_path}, "
                        f"Workspace: {workspace_root}, Data: {data_root}"
                    )
                    return False, error_msg

                return True, ""

            except Exception as e:
                error_msg = f"Path validation error: {str(e)}"
                return False, error_msg

        # Validate the path before writing
        is_valid, validation_error = validate_target_path(target_filepath)
        if not is_valid:
            print(f"❌ {validation_error}")
            return {
                "errors": [validation_error],
                "status": "tool_execution_failed",
                "tool_call_count": state.get("tool_call_count", 0) + 1
            }

        try:
            # write_file_tool 찾기
            write_tool = None
            for tool in tools:
                if tool.name == "write_file":
                    write_tool = tool
                    break

            if write_tool:
                result = write_tool.invoke({
                    "filepath": target_filepath,
                    "content": generated_code
                })
                print(f"✅ 파일 생성 완료: {target_filepath}")
                files_created.append(target_filepath)
            else:
                # Tool이 없으면 직접 파일 저장
                path = Path(target_filepath)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(generated_code, encoding='utf-8')
                print(f"✅ 파일 생성 완료 (직접 저장): {target_filepath}")
                files_created.append(target_filepath)
        except Exception as e:
            error_msg = f"파일 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "status": "tool_execution_failed",
                "tool_call_count": state.get("tool_call_count", 0) + 1
            }
    else:
        # target_filepath가 없으면 기존 방식 사용 (workspace)
        print("ℹ️ target_filepath가 없어 기존 방식으로 저장합니다.")

    return {
        "files_created": files_created,
        "files_edited": files_edited,
        "status": "tool_executed",
        "tool_call_count": state.get("tool_call_count", 0) + 1
    }


def execute_code_node(state: CodeGenerationState) -> CodeGenerationState:
    """노드 5: 코드 실행 (src/tools의 도구 사용)
    
    기본적으로 도커 샌드박스에서 실행하여 실행 환경을 분리합니다.
    로컬 실행은 명시적으로 요청된 경우에만 사용합니다.
    
    사용 도구:
    - 기본: execute_code_in_docker (도커 샌드박스)
    - 예외: context.execution_environment == "local"인 경우 로컬 실행
    """
    print("🚀 [Code Generation Agent] 코드 실행 중...")
    
    generated_code = state.get("generated_code", "")
    generated_code_file = state.get("generated_code_file")
    context = state.get("context", {})
    
    # 실행할 코드 확인
    if not generated_code and not generated_code_file:
        error_msg = "실행할 코드가 없습니다."
        print(f"❌ {error_msg}")
        return {
            "execution_errors": [error_msg],
            "execution_result": None,
            "status": "execution_failed"
        }
    
    # 실행 환경 결정 (항상 Docker 사용 - 격리된 환경 필요)
    domain = context.get("domain", "") if context else ""
    
    # 컨텍스트 정보 출력 (디버깅용)
    if domain:
        print(f"📋 도메인: {domain}")
    print("🐳 도커 샌드박스에서 실행 (격리된 환경)")
    
    try:
        # 도커 샌드박스 실행 (격리된 환경)
        # 핵심: 코드와 파일이 외부에 있고, 도커 환경에서 실행
        if not generated_code_file:
            # 코드 문자열인 경우 임시 파일로 저장
            from src.utils.paths import get_workspace_subdirectories
            directories = get_workspace_subdirectories()
            temp_file = directories["generated_code"] / f"temp_code_{os.getpid()}.py"
            temp_file.write_text(generated_code, encoding='utf-8')
            code_file_path = temp_file
        else:
            code_file_path = Path(generated_code_file)
        
        # 입력 파일 경로 추출 (CSV 파일 등)
        csv_file = None
        csv_files = None
        if context:
            csv_file_path = context.get("csv_file_path", "")
            csv_file_paths = context.get("csv_file_paths", [])
            
            if csv_file_paths:
                resolved_files = []
                for p in csv_file_paths:
                    if not p:
                        continue
                    path_obj = Path(p).expanduser()
                    if path_obj.exists():
                        resolved_files.append(path_obj.resolve())
                if resolved_files:
                    csv_files = resolved_files
            elif csv_file_path:
                csv_file_path_obj = Path(csv_file_path).expanduser()
                if csv_file_path_obj.exists():
                    csv_file = csv_file_path_obj.resolve()
        
        # 출력 디렉토리 설정 (결과 파일 저장용)
        output_dir = None
        if context:
            output_dir_str = context.get("output_directory", "")
            if output_dir_str:
                output_dir = Path(output_dir_str).expanduser().resolve()
            else:
                # 출력 디렉토리가 지정되지 않으면 workspace/results 사용
                from src.utils.paths import get_workspace_subdirectories
                directories = get_workspace_subdirectories()
                output_dir = directories.get("results").resolve()
        
        # 도커 이미지 설정 (기본값: csv-sandbox:test)
        docker_image = context.get("docker_image", "csv-sandbox:test") if context else "csv-sandbox:test"
        
        # CSV 파일이 있는 경우 코드에 파일 경로 변수 추가 및 도커 경로 변환
        code_to_execute = generated_code
        if csv_files or csv_file:
            # CSV 파일 목록 준비
            csv_file_paths_list = csv_files if csv_files else ([csv_file] if csv_file else [])
            
            # 마운트 정보 계산 (실제 마운트와 일치하도록)
            from src.tools.code_execution.utils.docker_path_converter import (
                calculate_mount_info,
                convert_host_paths_to_docker
            )
            
            mount_info = calculate_mount_info(
                code_file=code_file_path,
                input_files=csv_file_paths_list,
                output_directory=output_dir
            )
            
            # 유틸리티 함수를 사용하여 경로 변환
            code_to_execute = convert_host_paths_to_docker(
                code=code_to_execute,
                code_file=code_file_path,
                input_files=csv_file_paths_list,
                mount_info=mount_info
            )
            
            # 수정된 코드를 파일에 저장
            code_file_path.write_text(code_to_execute, encoding='utf-8')
            print(f"✅ 코드에 파일 경로 변수 추가 및 도커 경로 변환 완료 (마운트 정보 기반)")
        
        print(f"🐳 도커 샌드박스에서 코드 실행 중... (이미지: {docker_image})")
        print(f"   코드 파일: {code_file_path}")
        if csv_files:
            print(f"   CSV 파일: {len(csv_files)}개")
            for csv_file in csv_files:
                print(f"      - {csv_file.name}")
        elif csv_file:
            print(f"   CSV 파일: {csv_file.name}")
        if output_dir:
            print(f"   출력 디렉토리: {output_dir}")
        
        # 새로운 통합 시스템 사용
        input_files = []
        if csv_files:
            input_files.extend([str(f) for f in csv_files])
        elif csv_file:
            input_files.append(str(csv_file))
        
        execution_result_obj = execute_code_in_docker(
            code_file=str(code_file_path),
            docker_image=docker_image,
            input_files=input_files if input_files else None,
            output_directory=str(output_dir) if output_dir else None,
            timeout=60
        )
        
        # 기존 형식으로 변환 (하위 호환성)
        docker_result = execution_result_obj.to_dict()
        
        # 마운트 정보는 metadata에서 가져오기
        mount_info = docker_result.get("metadata", {}).get("mount_info", {})
        docker_result["mount_info"] = mount_info
        
        # 마운트 정보 출력 (디버깅용)
        if mount_info:
            print("📋 도커 마운트 정보:")
            for file_name, docker_path in mount_info.items():
                print(f"   {file_name} -> {docker_path}")
        
        # 임시 파일 정리
        if not generated_code_file and code_file_path.exists() and code_file_path.name.startswith("temp_code_"):
            try:
                code_file_path.unlink()
            except Exception:
                pass
        
        # 결과 포맷팅
        # 핵심: stdout에는 print 출력과 출력 파일 내용이 모두 포함됨
        if docker_result.get("success", False):
            result_parts = []
            
            # stdout (print 출력 + 출력 파일 내용 포함)
            if docker_result.get("stdout"):
                result_parts.append(f"📊 실행 결과 (stdout):\n{docker_result['stdout']}")
            
            # 출력 파일 목록 (추가 정보)
            output_files = docker_result.get("output_files", [])
            if output_files:
                result_parts.append(f"📄 출력 파일 ({len(output_files)}개): {', '.join([Path(f).name for f in output_files])}")
            
            # stderr (경고)
            if docker_result.get("stderr"):
                result_parts.append(f"⚠️ 경고 (stderr):\n{docker_result['stderr']}")
            
            if not result_parts:
                result_parts.append("✅ 코드 실행 완료 (출력 없음)")
            
            execution_result = "\n\n".join(result_parts)
            execution_errors = []
        else:
            # 실행 실패
            error_parts = []
            if docker_result.get("stdout"):
                error_parts.append(f"📊 실행 결과 (stdout):\n{docker_result['stdout']}")
            if docker_result.get("stderr"):
                error_parts.append(f"❌ 에러 (stderr):\n{docker_result['stderr']}")
            if docker_result.get("error"):
                error_parts.append(f"❌ 오류: {docker_result['error']}")
            if docker_result.get("exit_code") is not None and docker_result.get("exit_code") != 0:
                error_parts.append(f"❌ 종료 코드: {docker_result['exit_code']}")
            
            # 마운트 정보 포함 (경로 오류 해결에 도움)
            mount_info = docker_result.get("mount_info", {})
            if mount_info:
                error_parts.append("\n📋 도커 마운트 정보:")
                for file_name, docker_path in mount_info.items():
                    error_parts.append(f"   {file_name} -> {docker_path}")
            
            execution_result = "\n\n".join(error_parts) if error_parts else "❌ 코드 실행 실패"
            
            # 경로 오류 감지 및 구체적인 해결 방법 제시
            execution_errors = []  # execution_errors 초기화
            stderr = docker_result.get("stderr", "")
            mount_info = docker_result.get("mount_info", {})
            
            if "FileNotFoundError" in stderr or "No such file or directory" in stderr:
                # 마운트 정보를 포함한 구체적인 에러 메시지 생성
                error_msg = "파일 경로 오류: 도커 컨테이너 내부 경로를 확인하세요.\n\n"
                error_msg += "📋 사용 가능한 파일 경로 (마운트 정보):\n"
                
                if mount_info:
                    for file_name, docker_path in mount_info.items():
                        if file_name != "output_directory":
                            error_msg += f"   - {file_name} -> {docker_path}\n"
                    
                    if "output_directory" in mount_info:
                        error_msg += f"\n   출력 디렉토리: {mount_info['output_directory']}\n"
                else:
                    error_msg += "   (마운트 정보 없음)\n"
                
                error_msg += "\n💡 해결 방법:\n"
                error_msg += "   - 위의 도커 경로를 사용하여 파일을 읽으세요\n"
                error_msg += "   - filepath 변수를 사용하는 경우 올바른 도커 경로로 설정되었는지 확인하세요\n"
                
                execution_errors.append(error_msg)
            else:
                execution_errors = [execution_result]
        
        # stdout/stderr에서 context 추출
        extracted_context = None
        if execution_result_obj:
            user_query = state.get("task_description", "")
            extracted_context = extract_context_from_result(
                execution_result_obj,
                user_query=user_query if user_query else None
            )
            
            # Context 정보 출력
            if extracted_context:
                print("📊 Context 추출 완료:")
                if extracted_context.get("insights"):
                    print(f"   💡 인사이트: {len(extracted_context['insights'])}개")
                if extracted_context.get("statistics"):
                    stats = extracted_context["statistics"]
                    print(f"   📈 통계 정보: {len(stats)}개 항목")
                    for key, value in list(stats.items())[:3]:
                        print(f"      - {key}: {value}")
                if extracted_context.get("extracted_data"):
                    data = extracted_context["extracted_data"]
                    print(f"   📊 추출된 데이터: {len(data)}개 항목")
                if extracted_context.get("stdout_summary"):
                    summary = extracted_context["stdout_summary"]
                    if summary:
                        preview = summary[:150] if len(summary) > 150 else summary
                        print(f"   📝 stdout 요약: {preview}...")
        
        # 결과 반환
        if execution_errors:
            print(f"❌ 코드 실행 실패: {len(execution_errors)}개 오류 발견")
            for i, err in enumerate(execution_errors[:3], 1):
                print(f"   {i}. {err[:100]}...")  # 최대 100자만 출력
            return {
                "execution_result": execution_result,
                "execution_errors": execution_errors,
                "execution_context": extracted_context,  # Context 추가 (에러가 있어도 추출된 context는 유지)
                "status": "execution_failed"
            }
        else:
            print(f"✅ 코드 실행 성공")
            # 실행 결과 미리보기
            if execution_result:
                preview = execution_result[:200] if len(execution_result) > 200 else execution_result
                print(f"📊 실행 결과 미리보기: {preview}...")
            return {
                "execution_result": execution_result,
                "execution_errors": [],
                "execution_context": extracted_context,  # Context 추가
                "status": "code_executed"
            }
            
    except Exception as e:
        generated_code = state.get("generated_code", "")
        error = ExecutionError(
            message=f"코드 실행 중 오류 발생: {str(e)}",
            code=generated_code,
            agent_name="code_generation_agent",
            node_name="execute_code_node",
            original_error=e
        )
        print(format_error_message(error, include_traceback=True))
        
        error_state = format_error_for_state(error)
        error_state["execution_errors"] = [error.message]
        error_state["execution_result"] = None
        error_state["status"] = "execution_failed"
        return error_state


def should_fix_code(state: CodeGenerationState) -> Literal["fix", "done"]:
    """코드 검증 후 수정 여부 판단
    
    핵심: 프로그램으로 자동 수정 성공 시 LLM 수정 불필요
    """
    code_syntax_valid = state.get("code_syntax_valid", None)
    auto_fixed = state.get("auto_fixed", False)
    syntax_errors = state.get("syntax_errors", [])
    validation_errors = state.get("validation_errors", [])
    
    # code_syntax_valid가 None이면 검증이 수행되지 않았으므로 통과로 간주하지 않음
    if code_syntax_valid is None:
        print("⚠️ 코드 검증이 수행되지 않았습니다. 검증을 수행합니다.")
        return "done"
    
    # 프로그램으로 자동 수정 성공 시 LLM 수정 불필요
    if auto_fixed and code_syntax_valid:
        print("✅ 프로그램으로 자동 수정 완료 - LLM 수정 불필요")
        return "done"
    
    # code_syntax_valid가 True이고 오류가 없으면 통과
    if code_syntax_valid and not syntax_errors and not validation_errors:
        print("✅ 코드 검증 통과 - 코드 실행으로 진행")
        return "done"
    
    # code_syntax_valid가 False이거나 오류가 있으면 LLM 수정 필요
    error_count = len(syntax_errors) if syntax_errors else 0
    error_count += len(validation_errors) if validation_errors else 0
    print(f"❌ 코드 검증 실패 - LLM 수정 필요 (오류 {error_count}개)")
    if syntax_errors:
        print(f"   문법 오류: {syntax_errors[:3]}")  # 최대 3개만 출력
    if validation_errors:
        print(f"   검증 오류: {validation_errors[:3]}")  # 최대 3개만 출력
    return "fix"


def should_fix_after_execution(state: CodeGenerationState) -> Literal["fix", "done"]:
    """코드 실행 후 수정 여부 판단
    
    - 실행 오류가 있으면 수정 필요 ("fix")
    - 실행 성공하면 완료 ("done")
    - Context는 추출되어 다음 코드 생성에 활용됨 (generate_code_node에서 처리)
    """
    execution_errors = state.get("execution_errors", [])
    execution_context = state.get("execution_context")
    
    if execution_errors:
        error_count = len(execution_errors)
        print(f"❌ 코드 실행 실패 - LLM 수정 필요 (실행 오류 {error_count}개)")
        for i, err in enumerate(execution_errors[:3], 1):
            print(f"   {i}. {err[:100]}...")  # 최대 100자만 출력
        return "fix"
    else:
        # 실행 성공
        # context가 추출되었으면 다음 코드 생성에 활용됨
        if execution_context:
            insights = execution_context.get("insights", [])
            statistics = execution_context.get("statistics", {})
            extracted_data = execution_context.get("extracted_data", {})
            
            # 의미있는 context가 추출되었는지 확인
            has_meaningful_context = (
                len(insights) > 0 or
                len(statistics) > 0 or
                len(extracted_data) > 0
            )
            
            if has_meaningful_context:
                print("✅ 코드 실행 성공 - Context 추출 완료")
                print("   💡 다음 코드 생성 시 이전 실행 결과를 활용할 수 있습니다.")
            else:
                print("✅ 코드 실행 성공 - 작업 완료")
        else:
            print("✅ 코드 실행 성공 - 작업 완료")
        
        return "done"


# ========== 에이전트 생성 함수 ==========

def create_code_generation_agent(
    orchestrator_model: str = "ollama:gpt-oss:120b-cloud",
    worker_model: str = "ollama:codegemma:latest",
    enable_planning: bool = True,
    enable_filesystem_tools: bool = True,
    enable_execution: bool = True
):
    """코딩 에이전트 생성
    
    Args:
        orchestrator_model: Orchestrator 모델 (Planning용) - 기본값: gpt-oss:120b-cloud
        worker_model: Worker 모델 (코드 생성) - 기본값: codegemma:latest
        enable_planning: Planning Tool 활성화 여부
        enable_filesystem_tools: Filesystem Tools 활성화 여부
        enable_execution: Code Execution 노드 활성화 여부 (False 시 subgraph로 사용 시 외부 실행 노드 사용)
        
    Returns:
        LangGraph CompiledStateGraph
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
    orchestrator_model_str = orchestrator_model.strip() if orchestrator_model else "ollama:gpt-oss:120b-cloud"
    worker_model_str = worker_model.strip() if worker_model else "ollama:codegemma:latest"
    
    known_prefixes = ("ollama:", "anthropic:", "openai:")
    if not any(orchestrator_model_str.startswith(p) for p in known_prefixes):
        orchestrator_model_str = f"ollama:{orchestrator_model_str}"
    if not any(worker_model_str.startswith(p) for p in known_prefixes):
        worker_model_str = f"ollama:{worker_model_str}"
    
    # Orchestrator 모델 초기화 (Planning용)
    orchestrator = None
    if enable_planning:
        orchestrator = init_chat_model_helper(
            model_name=orchestrator_model_str,
            api_key=ollama_api_key,
            temperature=0.7
        )
        if not orchestrator:
            print(f"⚠️ Orchestrator 모델 초기화 실패: {orchestrator_model_str}")
            enable_planning = False
        else:
            print(f"✅ Orchestrator 모델 로드 완료: {orchestrator_model_str} (Planning)")
    
    # Worker 모델 초기화 (코드 생성)
    worker = init_chat_model_helper(
        model_name=worker_model_str,
        api_key=ollama_api_key,
        temperature=0.3  # 코드 생성은 낮은 temperature
    )
    
    if not worker:
        raise ValueError(f"Worker 모델 초기화 실패: {worker_model_str}")
    
    print(f"✅ Worker 모델 로드 완료: {worker_model_str} (코드 생성)")
    
    # 도구 목록 준비
    tools = []
    if enable_filesystem_tools:
        tools = [ls_tool, read_file_tool, write_file_tool, edit_file_tool]
        print(f"✅ Filesystem Tools 로드 완료: {len(tools)}개")
    
    # 노드 함수들을 클로저로 래핑
    def generate_code_node_with_model(state: CodeGenerationState) -> CodeGenerationState:
        return generate_code_node(state, worker)
    
    def fix_code_node_with_model(state: CodeGenerationState) -> CodeGenerationState:
        return fix_code_node(state, worker)
    
    def planning_node_with_model(state: CodeGenerationState) -> CodeGenerationState:
        if orchestrator:
            return planning_node(state, orchestrator)
        else:
            return {"status": "planning_skipped"}
    
    def tool_executor_node_with_tools(state: CodeGenerationState) -> CodeGenerationState:
        return tool_executor_node(state, tools)
    
    # LangGraph 그래프 구성
    graph = StateGraph(CodeGenerationState)
    
    # 노드 추가
    if enable_planning:
        graph.add_node("planning", planning_node_with_model)
    graph.add_node("analyze_requirements", analyze_requirements_node)
    graph.add_node("generate_code", generate_code_node_with_model)
    if enable_filesystem_tools:
        graph.add_node("tool_executor", tool_executor_node_with_tools)
    graph.add_node("validate_code_syntax", validate_code_syntax_node)
    if enable_execution:
        graph.add_node("execute_code", execute_code_node)  # 코드 실행 노드 추가
    graph.add_node("fix_code", fix_code_node_with_model)
    
    # 엣지 구성
    if enable_planning:
        graph.add_edge(START, "planning")
        graph.add_edge("planning", "analyze_requirements")
    else:
        graph.add_edge(START, "analyze_requirements")
    
    graph.add_edge("analyze_requirements", "generate_code")
    
    if enable_filesystem_tools:
        graph.add_edge("generate_code", "tool_executor")
        graph.add_edge("tool_executor", "validate_code_syntax")
    else:
        graph.add_edge("generate_code", "validate_code_syntax")
    
    # 조건부 엣지: 검증 후 수정 또는 실행/완료 여부 판단
    if enable_execution:
        # 실행 노드가 활성화된 경우: 검증 후 실행 또는 수정
        graph.add_conditional_edges(
            "validate_code_syntax",
            should_fix_code,
            {
                "fix": "fix_code",
                "done": "execute_code"  # 검증 통과 시 코드 실행으로 진행
            }
        )
        
        # 수정 후 재검증
        graph.add_edge("fix_code", "validate_code_syntax")
        
        # 조건부 엣지: 실행 후 수정 또는 완료 여부 판단
        graph.add_conditional_edges(
            "execute_code",
            should_fix_after_execution,
            {
                "fix": "fix_code",  # 실행 오류 시 수정으로
                "done": END  # 실행 성공 시 완료
            }
        )
    else:
        # 실행 노드가 비활성화된 경우: 검증 후 완료 또는 수정 (subgraph로 사용 시)
        graph.add_conditional_edges(
            "validate_code_syntax",
            should_fix_code,
            {
                "fix": "fix_code",
                "done": END  # 검증 통과 시 완료 (외부에서 실행)
            }
        )
        
        # 수정 후 재검증
        graph.add_edge("fix_code", "validate_code_syntax")
    
    # 그래프 컴파일
    compiled_graph = graph.compile()
    
    print("✅ Code Generation Agent가 성공적으로 생성되었습니다.")
    print(f"   Worker 모델: {worker_model_str} (코드 생성)")
    if enable_planning:
        print(f"   Orchestrator 모델: {orchestrator_model_str} (Planning)")
    print(f"   Planning Tool: {'활성화' if enable_planning else '비활성화'}")
    print(f"   Filesystem Tools: {'활성화' if enable_filesystem_tools else '비활성화'}")
    print(f"   Code Execution: {'활성화' if enable_execution else '비활성화'} (기본: 도커 샌드박스, 로컬 실행은 명시적 요청 시)")
    print(f"   지원 도메인: csv_analysis, web_development, api_development, data_processing, general")
    
    return compiled_graph


# LangGraph Studio용 agent 변수
_agent_cache = None
_agent_cache_lock = threading.Lock()

def _get_default_agent():
    """기본 Code Generation Agent 그래프 생성 (thread-safe lazy initialization with caching)"""
    global _agent_cache
    if _agent_cache is None:
        with _agent_cache_lock:
            if _agent_cache is None:  # Double-checked locking
                try:
                    _agent_cache = create_code_generation_agent()
                except Exception as e:
                    print(f"⚠️ 에이전트 생성 실패: {str(e)}")
                    print("   환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요.")
                    raise
    return _agent_cache

# Lazy initialization - use _get_default_agent() to get the agent instance
# Do NOT create agent at module level to prevent import side effects
agent = None

