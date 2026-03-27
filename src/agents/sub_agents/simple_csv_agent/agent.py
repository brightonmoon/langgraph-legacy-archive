"""
Simple CSV Analysis Agent

단순한 CSV 파일 분석 에이전트
- ollama:gpt-oss:120b-cloud 단일 모델 사용
- 워크플로우: CSV 읽기 → 코드 생성 → 실행 → 결과 분석 → 완료
"""

import os
import re
import threading
from typing import Literal, Optional
from pathlib import Path
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages

import json

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.paths import get_data_directory, resolve_data_file_path, get_workspace_subdirectories, get_project_root
from src.tools.csv_tools import read_csv_metadata_tool
from src.tools.planning import write_todos_tool
from src.tools.code_execution import execute_code_in_docker

from .state import SimpleCSVState


def create_simple_csv_agent(
    model: str = "ollama:gpt-oss:120b-cloud",
    max_iterations: int = 3,
    checkpointer=None
):
    """Simple CSV Analysis Agent 생성
    
    Args:
        model: 사용할 모델명 (기본값: ollama:gpt-oss:120b-cloud)
        max_iterations: 최대 반복 횟수 (기본값: 3)
        checkpointer: 상태 지속성을 위한 Checkpointer (LangGraph API 사용 시 무시됨)
        
    Returns:
        LangGraph CompiledStateGraph
        
    Note:
        LangGraph API를 통해 로드될 때는 checkpointer가 자동으로 처리되므로
        이 매개변수는 무시됩니다.
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
    if not model.startswith("ollama:") and not model.startswith("anthropic:") and not model.startswith("openai:"):
        model = f"ollama:{model}"
    
    # 모델 초기화
    llm = init_chat_model_helper(
        model_name=model,
        api_key=ollama_api_key,
        temperature=0.3  # 코드 생성은 낮은 temperature
    )
    
    if not llm:
        raise ValueError(f"모델 초기화 실패: {model}")
    
    print(f"✅ Simple CSV Agent 모델 로드 완료: {model}")
    
    # 워크스페이스 디렉토리 설정
    workspace_dirs = get_workspace_subdirectories()
    workspace_dir = workspace_dirs["generated_code"]
    
    # 노드 함수들 정의
    
    def read_csv_metadata_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 1: CSV 파일 메타데이터 읽기"""
        print("📊 [Read CSV Metadata] CSV 파일 메타데이터 읽기 중...")
        
        # 메시지에서 CSV 파일 경로 추출
        messages = state.get("messages", [])
        csv_file_path = state.get("csv_file_path")
        
        # 메시지에서 파일 경로 추출
        if not csv_file_path and messages:
            for msg in reversed(messages):
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    content = msg.content
                    # CSV 파일 경로 패턴 찾기
                    csv_pattern = r'([^\s]+\.csv)'
                    matches = re.findall(csv_pattern, content)
                    if matches:
                        csv_file_path = matches[0]
                        break
        
        if not csv_file_path:
            error_msg = "CSV 파일 경로가 제공되지 않았습니다. csv_file_path 필드에 파일 경로를 제공하거나 메시지에 파일 경로를 포함해주세요."
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "execution_error": error_msg,
                "final_result": error_msg
            }
        
        # 경로 해결
        try:
            resolved_path = resolve_data_file_path(csv_file_path)
            if not resolved_path or not resolved_path.exists():
                error_msg = f"파일을 찾을 수 없습니다: {csv_file_path}"
                print(f"❌ {error_msg}")
                return {
                    "status": "error",
                    "execution_error": error_msg,
                    "final_result": error_msg
                }
            
            # CSV 메타데이터 읽기
            metadata = read_csv_metadata_tool.invoke({"filepath": str(resolved_path)})
            print(f"✅ CSV 메타데이터 읽기 완료: {resolved_path.name}")
            
            return {
                "csv_file_path": str(resolved_path),
                "csv_metadata": metadata,
                "status": "metadata_read",
                "iteration_count": 0
            }
        except Exception as e:
            error_msg = f"CSV 메타데이터 읽기 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "execution_error": error_msg,
                "final_result": error_msg
            }
    
    def plan_tasks_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 2: 작업 계획 수립 (Planning)"""
        print("📋 [Plan Tasks] 작업 계획 수립 중...")
        
        # Planning이 이미 완료된 경우 스킵
        planning_result_existing = state.get("planning_result")
        if planning_result_existing:
            print("✅ Planning이 이미 완료됨")
            return {
                "status": "planned"
            }
        
        # 쿼리 추출
        query = ""
        messages = state.get("messages", [])
        if messages:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage) and hasattr(msg, 'content') and isinstance(msg.content, str):
                    query = msg.content
                    break
        
        if not query:
            query = "CSV 파일을 분석하고 주요 인사이트를 추출하세요."
        
        csv_metadata = state.get("csv_metadata", "")
        
        # Planning 프롬프트 구성
        planning_context = f"""CSV 파일 분석 작업을 하위 작업으로 분해하세요.

CSV 메타데이터:
{csv_metadata}

사용자 요청: {query}

**중요 제약사항:**
- 하위 작업 수는 최소 3개, 최대 7개로 제한하세요
- 작업을 너무 세분화하지 말고, 관련된 작업들을 하나의 큰 단위로 묶어서 설계하세요
- 각 하위 작업은 여러 단계를 포함할 수 있는 의미 있는 단위여야 합니다
- 예: "데이터 로드 및 전처리", "기본 통계 분석", "고급 분석 및 인사이트 추출", "결과 요약 및 시각화"

하위 작업들을 JSON 배열 형식으로 나열하세요.
예: ["하위 작업 1", "하위 작업 2", "하위 작업 3"]

하위 작업 목록만 출력하세요 (설명 없이)."""

        try:
            # LLM으로 작업 분해
            planning_prompt = f"""다음 작업을 분석하여 하위 작업으로 분해하세요:

{planning_context}"""

            response = llm.invoke([
                SystemMessage(content="당신은 작업 계획 수립 전문가입니다. 복잡한 작업을 명확하고 적절한 수의 하위 작업으로 분해하세요. 작업을 너무 세분화하지 말고, 관련된 작업들을 하나의 큰 단위로 묶어서 설계하세요."),
                HumanMessage(content=planning_prompt)
            ])
            
            # 응답에서 하위 작업 추출
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # JSON 배열 추출 시도
            subtasks = []
            try:
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
                print(f"⚠️ 생성된 작업 수({len(subtasks)}개)가 최대 제한(7개)을 초과했습니다. 작업을 통합합니다.")
                if len(subtasks) > 7:
                    remaining_tasks = subtasks[6:]
                    subtasks = subtasks[:6]
                    if remaining_tasks:
                        subtasks.append(f"{subtasks[-1]} 및 {', '.join(remaining_tasks[:3])}" + (" 등" if len(remaining_tasks) > 3 else ""))
                    else:
                        subtasks = subtasks[:7]
            
            # Planning Tool 호출
            planning_result = write_todos_tool.invoke({
                "task": query,
                "subtasks": subtasks if subtasks else None
            })
            
            # Planning 결과 파싱
            try:
                planning_data = json.loads(planning_result)
                todos = planning_data.get("todos", [])
            except Exception:
                todos = []
            
            print(f"✅ Planning 완료: {len(todos)}개의 하위 작업 생성")
            if todos:
                print("   하위 작업 목록:")
                for i, todo in enumerate(todos, 1):
                    todo_desc = todo.get("task", todo.get("description", str(todo)))
                    print(f"     {i}. {todo_desc}")
            
            return {
                "planning_result": planning_result,
                "planning_todos": todos,
                "current_subtask": 0,
                "subtask_results": [],
                "subtask_codes": [],
                "status": "planned"
            }
            
        except Exception as e:
            error_msg = f"Planning 실패: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            # Planning 실패 시 단일 작업으로 진행
            return {
                "planning_result": None,
                "planning_todos": [],
                "current_subtask": 0,
                "subtask_results": [],
                "subtask_codes": [],
                "status": "planning_failed"
            }
    
    def generate_code_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 3: 데이터 분석 코드 생성 (현재 하위 작업에 맞게)"""
        print("💻 [Generate Code] 데이터 분석 코드 생성 중...")
        
        # Planning 정보 확인
        planning_todos = state.get("planning_todos", [])
        current_subtask = state.get("current_subtask", 0)
        subtask_results = state.get("subtask_results", [])
        
        # 현재 하위 작업 추출
        current_task = ""
        if planning_todos and current_subtask < len(planning_todos):
            current_todo = planning_todos[current_subtask]
            current_task = current_todo.get("task", current_todo.get("description", str(current_todo)))
            print(f"📌 현재 하위 작업 ({current_subtask + 1}/{len(planning_todos)}): {current_task}")
        else:
            # Planning이 없거나 완료된 경우 전체 쿼리 사용
            messages = state.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, HumanMessage) and hasattr(msg, 'content') and isinstance(msg.content, str):
                        current_task = msg.content
                        break
        
        if not current_task:
            current_task = "CSV 파일을 분석하고 주요 인사이트를 추출하세요."
        
        csv_metadata = state.get("csv_metadata", "")
        csv_file_path = state.get("csv_file_path", "")
        execution_result = state.get("execution_result")
        execution_error = state.get("execution_error")
        iteration_count = state.get("iteration_count", 0)
        
        # 컨텍스트 구성
        context_parts = []
        if csv_metadata:
            context_parts.append(f"CSV 메타데이터:\n{csv_metadata}\n")
        
        if csv_file_path:
            context_parts.append(f"CSV 파일 경로: {csv_file_path}\n")
        
        # 이전 하위 작업 결과 추가 (중요: 다음 작업에서 활용해야 함)
        previous_context = ""
        if subtask_results:
            context_parts.append("\n=== 이전 하위 작업 결과 (반드시 활용하세요) ===\n")
            for i, result in enumerate(subtask_results, 1):
                task_name = result.get("task", f"작업 {i}")
                task_result = result.get("result", "")
                if task_result:
                    # 전체 결과를 포함 (500자로 제한하지 않음)
                    context_parts.append(f"\n--- 작업 {i}: {task_name} ---\n{task_result}\n")
            
            previous_context = "\n".join(context_parts[-len(subtask_results):])
            context_parts.append("\n⚠️ 중요: 위의 이전 작업 결과를 참고하여 다음 작업을 수행하세요.\n")
            context_parts.append("이전 작업에서 생성된 변수, 필터링된 데이터, 계산된 값 등을 활용하세요.\n")
        
        if execution_result and not subtask_results:
            context_parts.append(f"\n이전 실행 결과:\n{execution_result}\n")
        
        if execution_error:
            context_parts.append(f"\n이전 오류:\n{execution_error}\n")
            context_parts.append("위 오류를 수정하여 코드를 재생성하세요.\n")
        
        context = "\n".join(context_parts)
        
        # Planning이 있는 경우와 없는 경우를 구분하여 프롬프트 작성
        if planning_todos and current_subtask > 0:
            # 하위 작업 중간 단계: 이전 결과를 활용해야 함
            # 이전 작업의 코드를 포함하여 변수를 사용 가능하게 함
            subtask_codes = state.get("subtask_codes", [])
            
            previous_code_context = ""
            if subtask_codes:
                previous_code_context = "\n**이전 하위 작업 코드 (이미 실행됨, 변수 사용 가능):**\n"
                for i, prev_code in enumerate(subtask_codes, 1):
                    previous_code_context += f"\n--- 작업 {i} 코드 ---\n{prev_code}\n"
                previous_code_context += "\n**중요**: 위 코드들이 이미 실행되어 변수들(df, filtered_df 등)이 사용 가능합니다.\n"
            
            system_prompt = f"""You are a Python data analysis expert. Generate Python code to analyze CSV files.

**⚠️ 매우 중요: 이것은 연속적인 하위 작업 중 하나입니다.**
**이전 작업의 코드가 이미 실행되어 변수들이 메모리에 있습니다.**
**같은 작업을 반복하지 말고, 이전 작업의 변수를 재사용하세요!**

{previous_code_context}

Requirements:
1. Use ONLY pandas and numpy for data analysis (matplotlib and seaborn may not be available)
2. Always print results so they can be captured
3. **절대 같은 작업을 반복하지 마세요** - 이전 작업에서 이미 로드한 데이터(df), 필터링한 데이터(filtered_df 등)를 재사용하세요
4. **이전 작업의 변수를 직접 사용하세요** - 예: df, filtered_df, sig_genes 등
5. **데이터를 다시 로드하지 마세요** - 이전 작업에서 이미 로드했습니다
6. **필터링을 다시 하지 마세요** - 이전 작업의 결과를 사용하세요
7. Generate ONLY the code for the current subtask that builds upon previous work
8. For visualization, use simple text-based output or skip visualization if matplotlib is not available
9. Print summary statistics and insights using pandas describe(), value_counts(), etc.
10. DO NOT try to install packages - only use what's available (pandas, numpy)

**코드 생성 규칙:**
- 이전 작업에서 생성된 변수(df, filtered_df, sig_genes 등)를 직접 사용
- 데이터 로드 코드를 포함하지 마세요 (이미 로드됨)
- 필터링 코드를 포함하지 마세요 (이미 필터링됨)
- 현재 하위 작업에 필요한 코드만 생성하세요

Available packages:
- pandas (for data manipulation and analysis)
- numpy (for numerical operations)

{context}

Generate Python code to solve the current subtask ONLY. Output only the Python code without markdown code blocks or explanations."""
        else:
            # 첫 번째 작업 또는 Planning이 없는 경우
            system_prompt = f"""You are a Python data analysis expert. Generate Python code to analyze CSV files.

Requirements:
1. Use ONLY pandas and numpy for data analysis (matplotlib and seaborn may not be available)
2. Always print results so they can be captured
3. Use the CSV file path provided in the context
4. Generate complete, executable code
5. For visualization, use simple text-based output or skip visualization if matplotlib is not available
6. Print summary statistics and insights using pandas describe(), value_counts(), etc.
7. The CSV file will be available at the path specified in the context
8. DO NOT try to install packages - only use what's available (pandas, numpy)

Available packages:
- pandas (for data manipulation and analysis)
- numpy (for numerical operations)

{context}

Generate Python code to solve the user's request. Output only the Python code without markdown code blocks or explanations."""

        user_prompt = current_task
        
        # LLM 호출
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        
        # 코드 추출
        code = response.content if hasattr(response, 'content') else str(response)
        
        # 마크다운 코드 블록 제거
        code_block_match = re.search(r'```(?:python)?\n?(.*?)```', code, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1).strip()
        else:
            code = code.strip()
        
        print(f"✅ 코드 생성 완료 ({len(code)} 문자, 반복: {iteration_count + 1})")
        
        # Planning이 있는 경우 코드 저장
        subtask_codes = state.get("subtask_codes", [])
        if planning_todos:
            if not subtask_codes:
                subtask_codes = []
            # 현재 작업의 코드 저장 (나중에 다음 작업에서 사용)
            result = {
                "messages": [response],
                "generated_code": code,
                "iteration_count": iteration_count + 1,
                "status": "code_generated"
            }
            # 코드는 나중에 실행 후 저장 (analyze_result에서)
            return result
        else:
            return {
                "messages": [response],
                "generated_code": code,
                "iteration_count": iteration_count + 1,
                "status": "code_generated"
            }
    
    def execute_code_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 3: 코드 실행 (Docker 샌드박스에서 안전하게 실행)"""
        print("🚀 [Execute Code] Docker 샌드박스에서 코드 실행 중...")

        generated_code = state.get("generated_code", "")
        csv_file_path = state.get("csv_file_path", "")

        if not generated_code:
            error_msg = "실행할 코드가 없습니다."
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "execution_error": error_msg
            }

        try:
            # 이전 하위 작업 결과가 있으면 코드에 통합
            planning_todos = state.get("planning_todos", [])
            current_subtask = state.get("current_subtask", 0)
            subtask_results = state.get("subtask_results", [])
            subtask_codes = state.get("subtask_codes", [])

            # 이전 작업 결과를 코드에 통합
            if subtask_codes and current_subtask > 0:
                # 이전 모든 작업의 코드를 순차적으로 실행하여 변수를 사용 가능하게 함
                previous_code_parts = []
                previous_code_parts.append(f"# CSV 파일 경로\ncsv_file_path = \"{csv_file_path}\"\n")
                previous_code_parts.append("\n# === 이전 하위 작업 코드 (변수 재사용을 위해 실행) ===\n")
                previous_code_parts.append("# 주의: 아래 코드들이 순차적으로 실행되어 변수들이 메모리에 유지됩니다.\n")

                # 이전 모든 작업의 코드를 포함 (실제로 실행됨)
                for i, prev_code in enumerate(subtask_codes):
                    previous_code_parts.append(f"\n# --- 작업 {i+1} 코드 (실행됨) ---\n")
                    # 함수 정의가 있으면 제거하고 직접 실행 가능하게 수정
                    prev_code_clean = prev_code

                    # main() 함수 정의 및 호출 패턴 제거
                    if "def main():" in prev_code_clean:
                        # main() 함수 내용만 추출 (들여쓰기 제거)
                        main_match = re.search(r'def main\(\):\s*\n(.*?)(?=\n(?:if __name__|def |class |$))', prev_code_clean, re.DOTALL)
                        if main_match:
                            # 함수 내용 추출 및 들여쓰기 제거
                            func_body = main_match.group(1)
                            # 첫 줄의 들여쓰기 확인
                            lines = func_body.split('\n')
                            if lines:
                                indent = len(lines[0]) - len(lines[0].lstrip())
                                # 들여쓰기 제거
                                func_body = '\n'.join([line[indent:] if len(line) > indent else line for line in lines])
                            prev_code_clean = func_body.strip()

                    # if __name__ == "__main__": 패턴 제거
                    prev_code_clean = re.sub(r'if __name__\s*==\s*["\']__main__["\']:.*', '', prev_code_clean, flags=re.DOTALL)
                    # main() 호출 제거
                    prev_code_clean = re.sub(r'^\s*main\(\)\s*$', '', prev_code_clean, flags=re.MULTILINE)

                    previous_code_parts.append(prev_code_clean)
                    previous_code_parts.append("\n")

                previous_code = "\n".join(previous_code_parts)

                code_with_path = f"""{previous_code}

# === 현재 작업 ({current_subtask + 1}/{len(planning_todos)}) ===
# ⚠️ 중요: 위의 이전 작업 코드들이 이미 실행되어 변수들(df, filtered_df 등)이 메모리에 있습니다.
# 이전 작업에서 생성된 변수를 직접 사용하세요. 같은 작업을 반복하지 마세요.

{generated_code}
"""
            else:
                # 첫 번째 작업인 경우
                code_with_path = f"""# CSV 파일 경로
csv_file_path = "{csv_file_path}"

{generated_code}
"""

            # 코드를 임시 파일로 저장
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            code_file = workspace_dir / f"simple_csv_code_{timestamp}.py"
            code_file.write_text(code_with_path, encoding="utf-8")

            # 작업 디렉토리 설정 (데이터 디렉토리)
            work_dir = get_data_directory()

            # Docker 샌드박스에서 코드 실행 (보안 격리)
            # CSV 파일을 input_files로 전달하여 컨테이너에 마운트
            input_files = [csv_file_path] if csv_file_path else None

            result = execute_code_in_docker(
                code_file=str(code_file),
                input_files=input_files,
                output_directory=str(work_dir),
                timeout=60
            )

            # 결과 처리
            result_dict = result.to_dict()

            if result_dict["success"]:
                execution_result = result_dict["stdout"]
                if result_dict["stderr"]:
                    execution_result += f"\n⚠️ 경고:\n{result_dict['stderr']}"

                print("✅ 코드 실행 완료")

                return {
                    "execution_result": execution_result,
                    "execution_error": None,
                    "status": "execution_success"
                }
            else:
                # 에러 발생
                error_msg = result_dict.get("error") or result_dict.get("stderr") or result_dict.get("stdout") or "알 수 없는 오류"
                if result_dict.get("stdout"):
                    error_msg = f"{error_msg}\n\n출력:\n{result_dict['stdout']}"
                if result_dict.get("exit_code"):
                    error_msg = f"종료 코드: {result_dict['exit_code']}\n{error_msg}"

                print(f"❌ 코드 실행 실패: {error_msg[:200]}...")

                return {
                    "execution_result": None,
                    "execution_error": error_msg,
                    "status": "execution_error"
                }

        except Exception as e:
            error_msg = f"코드 실행 중 예외 발생: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "execution_result": None,
                "execution_error": error_msg,
                "status": "execution_error"
            }
    
    def analyze_result_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 5: 결과 분석 및 다음 작업 결정"""
        print("🔍 [Analyze Result] 결과 분석 중...")
        
        execution_result = state.get("execution_result")
        execution_error = state.get("execution_error")
        iteration_count = state.get("iteration_count", 0)
        max_iterations_value = state.get("max_iterations", max_iterations)
        
        # Planning 정보 확인
        planning_todos = state.get("planning_todos", [])
        current_subtask = state.get("current_subtask", 0)
        subtask_results = state.get("subtask_results", [])
        
        # 오류가 있으면 재시도 여부 결정
        if execution_error:
            if iteration_count < max_iterations_value:
                print(f"⚠️ 실행 오류 발생 - 재시도 필요 (반복: {iteration_count}/{max_iterations_value})")
                return {
                    "status": "retry_needed"
                }
            else:
                print(f"❌ 최대 반복 횟수 도달 - 오류로 종료")
                return {
                    "status": "error",
                    "final_result": f"최대 반복 횟수 도달. 마지막 오류: {execution_error}"
                }
        
        # 결과가 없거나 비어있으면 재시도
        if not execution_result or len(execution_result.strip()) == 0:
            if iteration_count < max_iterations_value:
                print(f"⚠️ 실행 결과가 비어있음 - 재시도 필요 (반복: {iteration_count}/{max_iterations_value})")
                return {
                    "status": "retry_needed"
                }
            else:
                print(f"❌ 최대 반복 횟수 도달 - 결과 없음으로 종료")
                return {
                    "status": "error",
                    "final_result": "최대 반복 횟수 도달. 실행 결과가 없습니다."
                }
        
        # Planning이 있고 하위 작업이 남아있는 경우
        if planning_todos and current_subtask < len(planning_todos):
            # 현재 하위 작업 결과 저장
            current_todo = planning_todos[current_subtask]
            current_task = current_todo.get("task", current_todo.get("description", str(current_todo)))
            
            # 결과 저장
            if not subtask_results:
                subtask_results = []
            
            # 현재 작업의 코드도 저장 (다음 작업에서 재사용)
            subtask_codes = state.get("subtask_codes", [])
            if not subtask_codes:
                subtask_codes = []
            
            # 현재 생성된 코드 저장
            current_code = state.get("generated_code", "")
            if current_code:
                subtask_codes.append(current_code)
            
            subtask_results.append({
                "task": current_task,
                "result": execution_result,
                "subtask_index": current_subtask
            })
            
            print(f"✅ 하위 작업 {current_subtask + 1}/{len(planning_todos)} 완료: {current_task}")
            
            # 다음 하위 작업으로 진행
            next_subtask = current_subtask + 1
            if next_subtask < len(planning_todos):
                print(f"🔄 다음 하위 작업으로 진행: {next_subtask + 1}/{len(planning_todos)}")
                return {
                    "subtask_results": subtask_results,
                    "subtask_codes": subtask_codes,
                    "current_subtask": next_subtask,
                    "execution_result": None,  # 다음 작업을 위해 초기화
                    "execution_error": None,
                    "iteration_count": 0,  # 다음 작업을 위해 초기화
                    "status": "subtask_completed"
                }
            else:
                # 모든 하위 작업 완료
                print("✅ 모든 하위 작업 완료 - 결과 요약으로 진행")
                # 마지막 코드도 저장
                subtask_codes = state.get("subtask_codes", [])
                current_code = state.get("generated_code", "")
                if current_code and (not subtask_codes or len(subtask_codes) == current_subtask):
                    if not subtask_codes:
                        subtask_codes = []
                    subtask_codes.append(current_code)
                
                return {
                    "subtask_results": subtask_results,
                    "subtask_codes": subtask_codes,
                    "current_subtask": next_subtask,
                    "status": "all_subtasks_completed"
                }
        
        # Planning이 없거나 모든 하위 작업이 완료된 경우
        print("✅ 결과 분석 완료 - 작업 완료")
        
        # Planning이 없는 경우 기존 로직 사용
        if not planning_todos:
            query = ""
            messages = state.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, HumanMessage) and hasattr(msg, 'content') and isinstance(msg.content, str):
                        query = msg.content
                        break
            
            final_result_parts = []
            final_result_parts.append("=== CSV 데이터 분석 결과 ===\n")
            
            if query:
                final_result_parts.append(f"요청사항: {query}\n")
            
            final_result_parts.append("\n=== 실행 결과 ===\n")
            final_result_parts.append(execution_result)
            
            final_result = "\n".join(final_result_parts)
            
            return {
                "status": "completed",
                "final_result": final_result
            }
        
        # Planning이 있는 경우 summarize로 진행
        return {
            "status": "all_subtasks_completed"
        }
    
    def summarize_results_node(state: SimpleCSVState) -> SimpleCSVState:
        """노드 6: 모든 하위 작업 결과 요약"""
        print("📝 [Summarize Results] 결과 요약 중...")
        
        planning_todos = state.get("planning_todos", [])
        subtask_results = state.get("subtask_results", [])
        
        if not subtask_results:
            return {
                "status": "error",
                "final_result": "요약할 결과가 없습니다."
            }
        
        # 쿼리 추출
        query = ""
        messages = state.get("messages", [])
        if messages:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage) and hasattr(msg, 'content') and isinstance(msg.content, str):
                    query = msg.content
                    break
        
        # 요약 프롬프트 구성
        summary_context = f"""다음은 CSV 파일 분석 작업의 모든 하위 작업 결과입니다.

사용자 요청: {query}

하위 작업 목록:
"""
        for i, todo in enumerate(planning_todos, 1):
            todo_desc = todo.get("task", todo.get("description", str(todo)))
            summary_context += f"{i}. {todo_desc}\n"

        summary_context += "\n각 하위 작업의 결과:\n"
        for i, result in enumerate(subtask_results, 1):
            task_name = result.get("task", f"작업 {i}")
            task_result = result.get("result", "")
            summary_context += f"\n=== 작업 {i}: {task_name} ===\n{task_result}\n"

        summary_prompt = f"""위의 모든 하위 작업 결과를 종합하여 최종 분석 보고서를 작성하세요.

요구사항:
1. 모든 하위 작업의 주요 결과를 요약하세요
2. 발견된 주요 인사이트를 정리하세요
3. 데이터의 패턴이나 트렌드를 설명하세요
4. 결론 및 제안사항을 포함하세요
5. 한글로 작성하세요

최종 보고서를 작성하세요."""

        try:
            response = llm.invoke([
                SystemMessage(content="당신은 데이터 분석 전문가입니다. 여러 하위 작업의 결과를 종합하여 명확하고 통찰력 있는 최종 보고서를 작성하세요."),
                HumanMessage(content=summary_prompt)
            ])
            
            summary = response.content if hasattr(response, 'content') else str(response)
            
            # 최종 결과 구성
            final_result_parts = []
            final_result_parts.append("=== CSV 데이터 분석 최종 보고서 ===\n")
            
            if query:
                final_result_parts.append(f"요청사항: {query}\n")
            
            final_result_parts.append("\n=== 최종 요약 ===\n")
            final_result_parts.append(summary)
            
            final_result_parts.append("\n\n=== 상세 결과 ===\n")
            for i, result in enumerate(subtask_results, 1):
                task_name = result.get("task", f"작업 {i}")
                task_result = result.get("result", "")
                final_result_parts.append(f"\n--- 작업 {i}: {task_name} ---\n{task_result}\n")
            
            final_result = "\n".join(final_result_parts)
            
            print("✅ 결과 요약 완료")
            
            return {
                "status": "completed",
                "final_result": final_result
            }
            
        except Exception as e:
            error_msg = f"결과 요약 실패: {str(e)}"
            print(f"❌ {error_msg}")
            # 요약 실패 시 상세 결과만 반환
            final_result_parts = []
            final_result_parts.append("=== CSV 데이터 분석 결과 ===\n")
            if query:
                final_result_parts.append(f"요청사항: {query}\n")
            final_result_parts.append("\n=== 상세 결과 ===\n")
            for i, result in enumerate(subtask_results, 1):
                task_name = result.get("task", f"작업 {i}")
                task_result = result.get("result", "")
                final_result_parts.append(f"\n--- 작업 {i}: {task_name} ---\n{task_result}\n")
            
            return {
                "status": "completed",
                "final_result": "\n".join(final_result_parts)
            }
    
    # 조건부 엣지 함수
    def should_continue_after_metadata(state: SimpleCSVState) -> Literal["plan_tasks", END]:
        """메타데이터 읽기 후 진행 여부 판단"""
        if state.get("status") == "error":
            return END
        return "plan_tasks"
    
    def should_continue_after_planning(state: SimpleCSVState) -> Literal["generate_code", END]:
        """Planning 후 진행 여부 판단"""
        status = state.get("status", "")
        if status == "error":
            return END
        # Planning 실패해도 계속 진행 (단일 작업으로 처리)
        return "generate_code"
    
    def should_retry_or_continue(state: SimpleCSVState) -> Literal["generate_code", "summarize_results", END]:
        """결과 분석 후 재시도, 다음 하위 작업, 또는 요약 결정"""
        status = state.get("status", "")
        
        if status == "retry_needed":
            return "generate_code"
        elif status == "all_subtasks_completed":
            return "summarize_results"
        elif status == "subtask_completed":
            return "generate_code"  # 다음 하위 작업으로
        elif status == "completed" or status == "error":
            return END
        else:
            # Planning이 없는 경우 바로 완료
            planning_todos = state.get("planning_todos", [])
            if not planning_todos:
                return END
            return "summarize_results"
    
    # 그래프 구성
    graph = StateGraph(SimpleCSVState)
    
    # 노드 추가
    graph.add_node("read_csv_metadata", read_csv_metadata_node)
    graph.add_node("plan_tasks", plan_tasks_node)
    graph.add_node("generate_code", generate_code_node)
    graph.add_node("execute_code", execute_code_node)
    graph.add_node("analyze_result", analyze_result_node)
    graph.add_node("summarize_results", summarize_results_node)
    
    # 엣지 추가
    graph.add_edge(START, "read_csv_metadata")
    
    graph.add_conditional_edges(
        "read_csv_metadata",
        should_continue_after_metadata,
        {
            "plan_tasks": "plan_tasks",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "plan_tasks",
        should_continue_after_planning,
        {
            "generate_code": "generate_code",
            END: END
        }
    )
    
    graph.add_edge("generate_code", "execute_code")
    graph.add_edge("execute_code", "analyze_result")
    
    graph.add_conditional_edges(
        "analyze_result",
        should_retry_or_continue,
        {
            "generate_code": "generate_code",  # 재시도 또는 다음 하위 작업
            "summarize_results": "summarize_results",  # 모든 하위 작업 완료
            END: END  # 완료 또는 오류
        }
    )
    
    graph.add_edge("summarize_results", END)
    
    # 그래프 컴파일
    # LangGraph API는 자동으로 persistence를 처리하므로 checkpointer를 전달하지 않음
    agent = graph.compile()
    
    return agent


# Lazy initialization to prevent module-level side effects
_agent_cache = None
_agent_cache_lock = threading.Lock()

def get_agent():
    """기본 Simple CSV Agent 인스턴스 반환 (thread-safe lazy initialization)"""
    global _agent_cache
    if _agent_cache is None:
        with _agent_cache_lock:
            if _agent_cache is None:  # Double-checked locking
                _agent_cache = create_simple_csv_agent()
    return _agent_cache

# Lazy initialization - use get_agent() to get the agent instance
# Do NOT create agent at module level to prevent import side effects
agent = None
