"""
CSV 에이전트와 코딩 에이전트 통합 예시

이 파일은 통합 방법을 보여주는 예시입니다.
실제 구현은 agent.py의 generate_analysis_code_node에 적용해야 합니다.
"""

# 표준 라이브러리
from pathlib import Path
from typing import Dict, Any, List

# 로컬 (같은 패키지 내 - 상대 import 허용)
from .agent import CSVAnalysisState, _save_code_to_workspace

# 로컬 (다른 패키지 - 절대 import)
from src.agents.sub_agents.code_generation_agent import create_code_generation_agent
from src.agents.sub_agents.code_generation_agent.state import CodeGenerationState


def integrate_code_generation_agent_in_csv_agent():
    """
    CSV 에이전트에 코딩 에이전트를 통합하는 방법
    
    Step 1: create_csv_data_analysis_agent 함수에서 코딩 에이전트 생성
    Step 2: generate_analysis_code_node에서 코딩 에이전트 호출
    """
    
    # ========== Step 1: 코딩 에이전트 생성 ==========
    # create_csv_data_analysis_agent 함수 내부에 추가
    
    def create_csv_data_analysis_agent_with_code_agent(
        model: str = "ollama:gpt-oss:120b-cloud",
        code_generation_model: str = "ollama:codegemma:latest",
        enable_hitl: bool = True,
        use_code_generation_agent: bool = True  # 새 파라미터 추가
    ):
        """CSV 에이전트 생성 (코딩 에이전트 통합 버전)"""
        
        # ... 기존 모델 초기화 코드 ...
        
        # 코딩 에이전트 생성
        code_agent = None
        if use_code_generation_agent:
            try:
                code_agent = create_code_generation_agent(
                    enable_planning=False,  # CSV 에이전트에서 이미 프롬프트 보강 완료
                    enable_filesystem_tools=True  # 파일 저장 필요
                )
                print("✅ 코딩 에이전트 생성 완료")
            except Exception as e:
                print(f"⚠️ 코딩 에이전트 생성 실패: {str(e)}")
                print("   기존 방식으로 폴백합니다.")
                code_agent = None
        
        # ... 나머지 코드 ...
        
        # generate_analysis_code_node에 code_agent 전달
        def generate_analysis_code_node(state: CSVAnalysisState) -> CSVAnalysisState:
            return generate_code_with_agent_or_worker(
                state, code_agent, worker_model, enable_hitl
            )
        
        # ... 그래프 구성 ...
        
        return compiled_graph
    
    # ========== Step 2: 코드 생성 노드 수정 ==========
    
    def generate_code_with_agent_or_worker(
        state: CSVAnalysisState,
        code_agent,  # 코딩 에이전트 인스턴스
        worker_model,  # 기존 Worker 모델 (폴백용)
        enable_hitl: bool
    ) -> CSVAnalysisState:
        """코딩 에이전트 또는 Worker 모델을 사용하여 코드 생성"""
        
        CSV_file_path = state.get("CSV_file_path", "")
        CSV_file_paths = state.get("CSV_file_paths", [])
        CSV_metadata = state.get("CSV_metadata", "")
        query = state.get("query", "")
        augmented_prompt = state.get("augmented_prompt", "")
        
        # Human-in-the-Loop 처리 (기존 로직 유지)
        if enable_hitl and state.get("generated_code") and not state.get("code_approved", False):
            # ... 기존 HITL 로직 ...
            pass
        
        # 코딩 에이전트 사용 여부 결정
        use_code_agent = code_agent is not None
        
        if use_code_agent:
            return _generate_code_with_code_agent(
                state, code_agent, CSV_file_path, CSV_file_paths,
                CSV_metadata, query, augmented_prompt, enable_hitl
            )
        else:
            return _generate_code_with_worker(
                state, worker_model, CSV_file_path, CSV_file_paths,
                CSV_metadata, query, augmented_prompt, enable_hitl
            )
    
    
    def _generate_code_with_code_agent(
        state: CSVAnalysisState,
        code_agent,
        CSV_file_path: str,
        CSV_file_paths: List[str],
        CSV_metadata: str,
        query: str,
        augmented_prompt: str,
        enable_hitl: bool
    ) -> CSVAnalysisState:
        """코딩 에이전트를 사용하여 코드 생성"""
        
        print("🔧 [통합] 코딩 에이전트를 사용하여 코드 생성 중...")
        
        try:
            # CSV 상태를 코딩 에이전트 상태로 변환
            code_agent_state: CodeGenerationState = {
                "messages": [],
                "task_description": query or augmented_prompt or f"CSV 파일 분석: {CSV_file_path}",
                "requirements": augmented_prompt if augmented_prompt else f"CSV 파일을 분석하는 코드 생성",
                "context": {
                    "domain": "csv_analysis",
                    "csv_file_path": CSV_file_path,
                    "csv_file_paths": CSV_file_paths,
                    "csv_metadata": CSV_metadata,
                    "augmented_prompt": augmented_prompt,
                    "query": query
                },
                "target_filepath": None,  # 코딩 에이전트가 자동으로 생성
                "status": "analyzing"
            }
            
            # 코딩 에이전트 실행
            code_agent_result = code_agent.invoke(code_agent_state)
            
            # 코딩 에이전트 결과 추출
            generated_code = code_agent_result.get("generated_code", "")
            generated_code_file = code_agent_result.get("generated_code_file", "")
            
            if not generated_code:
                raise ValueError("코딩 에이전트가 코드를 생성하지 못했습니다.")
            
            print(f"✅ 코딩 에이전트로 코드 생성 완료 ({len(generated_code)} 문자)")
            
            # CSV 특화 처리: 파일 경로 변수 추가
            generated_code = _add_csv_filepath_variables(
                generated_code, CSV_file_path, CSV_file_paths
            )
            
            # 코드 파일 저장 (CSV 에이전트 디렉토리 구조에 맞게)
            code_file = _save_code_to_workspace(
                code=generated_code,
                directory="generated_code",
                prefix="analysis"
            )
            
            return {
                "generated_code": generated_code,
                "generated_code_file": str(code_file),
                "status": "code_generated",
                "code_approved": not enable_hitl,  # HITL 비활성화 시 자동 승인
                "call_count": state.get("call_count", 0) + 1
            }
            
        except Exception as e:
            print(f"⚠️ 코딩 에이전트 실행 중 오류 발생: {str(e)}")
            print("   기존 방식으로 폴백합니다.")
            # 폴백: Worker 모델 사용
            return _generate_code_with_worker(
                state, None, CSV_file_path, CSV_file_paths,
                CSV_metadata, query, augmented_prompt, enable_hitl
            )
    
    
    def _generate_code_with_worker(
        state: CSVAnalysisState,
        worker_model,
        CSV_file_path: str,
        CSV_file_paths: List[str],
        CSV_metadata: str,
        query: str,
        augmented_prompt: str,
        enable_hitl: bool
    ) -> CSVAnalysisState:
        """Worker 모델을 직접 사용하여 코드 생성 (기존 방식)"""
        
        print("🤖 Worker 모델로 코드 생성 중...")
        
        # 기존 코드 생성 로직
        # ... 기존 코드 ...
        
        return {
            "generated_code": "...",
            "generated_code_file": "...",
            "status": "code_generated",
            "code_approved": not enable_hitl,
            "call_count": state.get("call_count", 0) + 1
        }
    
    
    def _add_csv_filepath_variables(
        code: str,
        CSV_file_path: str,
        CSV_file_paths: List[str]
    ) -> str:
        """CSV 파일 경로 변수를 코드에 추가"""
        import re
        
        # 여러 파일 모드
        if CSV_file_paths and len(CSV_file_paths) > 1:
            has_filepath_vars = any(
                f'filepath_{i+1}' in code or (i == 0 and 'filepath' in code)
                for i in range(len(CSV_file_paths))
            )
            
            if not has_filepath_vars:
                filepath_vars = []
                for i, file_path in enumerate(CSV_file_paths):
                    var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
                    filepath_vars.append(f'{var_name} = "{file_path}"')
                code = '\n'.join(filepath_vars) + '\n' + code
        else:
            # 단일 파일 모드
            file_path = CSV_file_paths[0] if CSV_file_paths else CSV_file_path
            if 'filepath' not in code and 'pd.read_csv' in code:
                pattern = r"pd\.read_csv\(['\"]([^'\"]+)['\"]"
                if re.search(pattern, code):
                    code = f'filepath = "{file_path}"\n' + code
                    code = re.sub(pattern, 'pd.read_csv(filepath)', code)
        
        return code


