"""
REPL Data Analysis Agent

REPL 기반 하이브리드 스키마 데이터 분석 에이전트
- REPL 세션 기반 상태 유지
- 반복적 코드 생성 및 개선
- 데이터 분석 특화 기능

워크플로우:
1. 데이터 파일 메타데이터 읽기
2. 데이터 분석 코드 생성 (LLM)
3. REPL 세션에서 코드 실행
4. 실행 결과 검증
5. (조건부: 재시도) → 코드 재생성
6. 인사이트 추출 및 최종 결과 생성
"""

import os
import re
from typing import Literal, Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.paths import get_data_directory, resolve_data_file_path
from src.tools.csv_tools import read_csv_metadata_tool

from .state import DataAnalysisREPLState
from .repl_session import get_or_create_session, REPLSession


def create_repl_data_analysis_agent(
    model: str = "ollama:codegemma:latest",
    max_iterations: int = 5,
    checkpointer=None
):
    """REPL Data Analysis Agent 생성
    
    Args:
        model: 사용할 모델명 (기본값: ollama:codegemma:latest)
        max_iterations: 최대 반복 횟수 (기본값: 5)
        checkpointer: 상태 지속성을 위한 Checkpointer (None이면 메모리 Checkpointer 사용)
        
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
    model = model.strip() if model else "ollama:codegemma:latest"
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
    
    print(f"✅ REPL Data Analysis Agent 모델 로드 완료: {model}")
    
    # Checkpointer 설정
    # LangGraph Studio 환경 감지
    is_langgraph_studio = False
    try:
        import sys
        if "langgraph_api" in sys.modules:
            is_langgraph_studio = True
        if os.getenv("LANGGRAPH_API") or os.getenv("LANGGRAPH_STUDIO"):
            is_langgraph_studio = True
        if any("langgraph" in str(arg).lower() for arg in sys.argv):
            is_langgraph_studio = True
    except Exception:
        pass
    
    if is_langgraph_studio:
        checkpointer = None
        print("⚠️  LangGraph Studio 환경 감지: 커스텀 checkpointer 비활성화 (자동 persistence 사용)")
    elif checkpointer is None:
        checkpointer = MemorySaver()
        print("✅ Checkpointer 활성화 (상태 지속성 지원)")
    
    # 노드 함수들 정의
    
    def read_data_metadata_node(state: DataAnalysisREPLState) -> DataAnalysisREPLState:
        """노드 1: 데이터 파일 메타데이터 읽기"""
        print("📊 [Read Data Metadata] 데이터 파일 메타데이터 읽기 중...")
        
        data_file_paths = state.get("data_file_paths", [])
        query = state.get("query", "")
        
        # 메시지에서 파일 경로 및 쿼리 추출
        # 중요: 메시지가 있으면 항상 최신 메시지에서 쿼리를 추출 (이전 state의 query 무시)
        messages = state.get("messages", [])
        if messages:
            # 최신 메시지부터 역순으로 확인 (최신 쿼리 우선)
            for msg in reversed(messages):
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    content = msg.content
                    
                    # HumanMessage에서 쿼리 추출 (최신 메시지 우선)
                    if isinstance(msg, HumanMessage):
                        query = content  # 최신 메시지의 쿼리로 덮어쓰기
                    
                    # CSV 파일 경로 패턴 찾기
                    csv_pattern = r'([^\s]+\.csv)'
                    matches = re.findall(csv_pattern, content)
                    if matches:
                        data_file_paths = matches
                        # 파일 경로가 있으면 해당 메시지의 쿼리도 사용
                        if isinstance(msg, HumanMessage):
                            query = content
                        break
        # 메시지가 없고 data_file_paths도 없으면 state에서 가져온 값 사용
        
        if not data_file_paths:
            error_msg = "데이터 파일 경로가 제공되지 않았습니다. data_file_paths 필드에 파일 경로를 제공하거나 메시지에 파일 경로를 포함해주세요."
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "execution_error": error_msg,
                "final_result": error_msg
            }
        
        # 메타데이터 읽기
        metadata_parts = []
        for file_path in data_file_paths:
            try:
                # 경로 해결
                resolved_path = resolve_data_file_path(file_path)
                if not resolved_path or not resolved_path.exists():
                    metadata_parts.append(f"⚠️ 파일을 찾을 수 없습니다: {file_path}")
                    continue
                
                # CSV 메타데이터 읽기
                metadata = read_csv_metadata_tool.invoke({"filepath": str(resolved_path)})
                metadata_parts.append(f"=== {resolved_path.name} ===\n{metadata}")
            except Exception as e:
                metadata_parts.append(f"❌ {file_path} 메타데이터 읽기 실패: {str(e)}")
        
        metadata_text = "\n\n".join(metadata_parts)
        print(f"✅ 데이터 메타데이터 읽기 완료 ({len(data_file_paths)} 파일)")
        
        return {
            "data_file_paths": data_file_paths,
            "data_metadata": metadata_text,
            "query": query if query else state.get("query", ""),
            "max_iterations": state.get("max_iterations", max_iterations),
            "iteration_count": state.get("iteration_count", 0),
            "status": "metadata_read"
        }
    
    def generate_code_node(state: DataAnalysisREPLState) -> DataAnalysisREPLState:
        """노드 2: 데이터 분석 코드 생성"""
        print("💻 [Generate Code] 데이터 분석 코드 생성 중...")
        
        # 쿼리는 state에서 가져오되, 메시지가 있으면 최신 메시지 우선
        query = state.get("query", "")
        messages = state.get("messages", [])
        if messages:
            # 최신 HumanMessage에서 쿼리 추출
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage) and hasattr(msg, 'content') and isinstance(msg.content, str):
                    query = msg.content
                    break
        
        data_metadata = state.get("data_metadata", "")
        data_file_paths = state.get("data_file_paths", [])
        execution_result = state.get("execution_result")
        execution_error = state.get("execution_error")
        iteration_count = state.get("iteration_count", 0)
        
        # 이전 실행 결과가 있으면 컨텍스트로 포함
        context = ""
        if data_metadata:
            context += f"\n데이터 메타데이터:\n{data_metadata}\n"
        
        if execution_result:
            context += f"\n이전 실행 결과:\n{execution_result}\n"
        
        if execution_error:
            context += f"\n이전 오류:\n{execution_error}\n"
            context += "\n위 오류를 수정하여 코드를 재생성하세요.\n"
        
        # 파일 경로 변수 설정
        filepath_context = ""
        if data_file_paths:
            for i, file_path in enumerate(data_file_paths):
                resolved_path = resolve_data_file_path(file_path)
                if resolved_path and resolved_path.exists():
                    var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
                    filepath_context += f'{var_name} = "{resolved_path}"\n'
        
        system_prompt = f"""You are a Python data analysis expert. Generate Python code to analyze data files.

Requirements:
1. Use pandas, numpy, matplotlib, seaborn for data analysis
2. Always print results so they can be captured
3. Use the filepath variables provided in the context
4. Generate complete, executable code
5. Include data visualization when appropriate
6. Print summary statistics and insights

{context}

File paths:
{filepath_context}

Generate Python code to solve the user's request. Output only the Python code without markdown code blocks or explanations."""

        user_prompt = query if query else "데이터를 분석하고 인사이트를 추출하세요."
        
        # 메시지 구성
        messages = state.get("messages", [])
        system_msg = SystemMessage(content=system_prompt)
        user_msg = HumanMessage(content=user_prompt)
        
        # 이전 메시지와 함께 LLM 호출
        response = llm.invoke([system_msg, user_msg] + messages[-5:])  # 최근 5개 메시지만 사용
        
        # 코드 추출
        code = response.content if hasattr(response, 'content') else str(response)
        
        # 마크다운 코드 블록 제거
        code_block_match = re.search(r'```(?:python)?\n?(.*?)```', code, re.DOTALL)
        if code_block_match:
            code = code_block_match.group(1).strip()
        else:
            code = code.strip()
        
        print(f"✅ 코드 생성 완료 ({len(code)} 문자, 반복: {iteration_count + 1})")
        
        return {
            "messages": [response],
            "generated_code": code,
            "iteration_count": iteration_count + 1,
            "status": "code_generated"
        }
    
    def execute_in_repl_node(state: DataAnalysisREPLState) -> DataAnalysisREPLState:
        """노드 3: REPL 세션에서 코드 실행"""
        print("🚀 [Execute in REPL] REPL 세션에서 코드 실행 중...")
        
        generated_code = state.get("generated_code", "")
        session_id = state.get("repl_session_id")
        
        if not generated_code:
            return {
                "status": "error",
                "execution_error": "실행할 코드가 없습니다."
            }
        
        # 세션 가져오기 또는 생성
        session = get_or_create_session(session_id)
        
        # 코드 실행
        result = session.execute(generated_code, timeout=30)
        
        if result["success"]:
            execution_result = result["stdout"]
            if result["stderr"]:
                execution_result += f"\n⚠️ 경고:\n{result['stderr']}"
            
            accumulated_output = session.get_accumulated_output()
            
            print("✅ 코드 실행 완료")
            
            return {
                "repl_session_id": session.session_id,
                "execution_result": execution_result,
                "execution_error": None,
                "accumulated_output": accumulated_output,
                "status": "execution_success"
            }
        else:
            error_msg = result.get("error", result.get("stderr", "알 수 없는 오류"))
            print(f"❌ 코드 실행 실패: {error_msg}")
            
            return {
                "repl_session_id": session.session_id,
                "execution_result": None,
                "execution_error": error_msg,
                "status": "execution_error"
            }
    
    def validate_result_node(state: DataAnalysisREPLState) -> DataAnalysisREPLState:
        """노드 4: 실행 결과 검증 및 재시도 필요 여부 판단"""
        print("🔍 [Validate Result] 실행 결과 검증 중...")
        
        execution_result = state.get("execution_result")
        execution_error = state.get("execution_error")
        iteration_count = state.get("iteration_count", 0)
        max_iterations_value = state.get("max_iterations", max_iterations)
        
        # 오류가 있으면 재시도
        if execution_error:
            if iteration_count < max_iterations_value:
                print(f"⚠️ 실행 오류 발생 - 재시도 필요 (반복: {iteration_count}/{max_iterations_value})")
                return {
                    "should_retry": True,
                    "retry_reason": f"실행 오류: {execution_error}",
                    "result_valid": False,
                    "status": "validation_failed_error"
                }
            else:
                print(f"❌ 최대 반복 횟수 도달 - 재시도 중단")
                return {
                    "should_retry": False,
                    "retry_reason": "최대 반복 횟수 도달",
                    "result_valid": False,
                    "status": "validation_failed_max_iterations"
                }
        
        # 결과가 없거나 비어있으면 재시도
        if not execution_result or len(execution_result.strip()) == 0:
            if iteration_count < max_iterations_value:
                print(f"⚠️ 실행 결과가 비어있음 - 재시도 필요 (반복: {iteration_count}/{max_iterations_value})")
                return {
                    "should_retry": True,
                    "retry_reason": "실행 결과가 비어있음",
                    "result_valid": False,
                    "status": "validation_failed_empty"
                }
            else:
                print(f"❌ 최대 반복 횟수 도달 - 재시도 중단")
                return {
                    "should_retry": False,
                    "retry_reason": "최대 반복 횟수 도달",
                    "result_valid": False,
                    "status": "validation_failed_max_iterations"
                }
        
        # 결과가 충분한지 간단 검증 (LLM 기반 검증은 선택적)
        # 여기서는 간단히 결과가 있으면 통과
        print("✅ 실행 결과 검증 통과")
        
        return {
            "should_retry": False,
            "result_valid": True,
            "status": "validation_passed"
        }
    
    def generate_insights_node(state: DataAnalysisREPLState) -> DataAnalysisREPLState:
        """노드 5: 인사이트 추출 및 최종 결과 생성"""
        print("💡 [Generate Insights] 인사이트 추출 및 최종 결과 생성 중...")
        
        execution_result = state.get("execution_result", "")
        accumulated_output = state.get("accumulated_output", "")
        query = state.get("query", "")
        
        # 최종 결과 구성
        final_result_parts = []
        final_result_parts.append("=== 데이터 분석 결과 ===\n")
        
        if query:
            final_result_parts.append(f"요청사항: {query}\n")
        
        final_result_parts.append("\n=== 실행 결과 ===\n")
        final_result_parts.append(execution_result)
        
        if accumulated_output:
            final_result_parts.append("\n=== 실행 히스토리 ===\n")
            final_result_parts.append(accumulated_output)
        
        final_result = "\n".join(final_result_parts)
        
        # 간단한 인사이트 추출 (LLM 기반 추출은 선택적)
        insights = []
        if execution_result:
            # 결과에서 숫자나 통계 정보 추출
            if "mean" in execution_result.lower() or "평균" in execution_result:
                insights.append("데이터의 평균값이 계산되었습니다.")
            if "correlation" in execution_result.lower() or "상관관계" in execution_result:
                insights.append("상관관계 분석이 수행되었습니다.")
            if "plot" in execution_result.lower() or "그래프" in execution_result:
                insights.append("시각화가 생성되었습니다.")
        
        print("✅ 인사이트 추출 및 최종 결과 생성 완료")
        
        return {
            "final_result": final_result,
            "insights": insights if insights else None,
            "status": "completed"
        }
    
    # 조건부 엣지 함수
    def should_continue_loop(state: DataAnalysisREPLState) -> Literal["generate_code", "generate_insights", END]:
        """반복 루프 제어"""
        should_retry = state.get("should_retry", False)
        iteration_count = state.get("iteration_count", 0)
        max_iterations_value = state.get("max_iterations", max_iterations)
        
        # 재시도 필요하고 최대 반복 횟수 미만이면 코드 재생성
        if should_retry and iteration_count < max_iterations_value:
            return "generate_code"
        
        # 최대 반복 횟수 도달 또는 검증 통과
        if iteration_count >= max_iterations_value or not should_retry:
            return "generate_insights"
        
        return END
    
    # 그래프 구성
    graph = StateGraph(DataAnalysisREPLState)
    
    # 노드 추가
    graph.add_node("read_data_metadata", read_data_metadata_node)
    graph.add_node("generate_code", generate_code_node)
    graph.add_node("execute_in_repl", execute_in_repl_node)
    graph.add_node("validate_result", validate_result_node)
    graph.add_node("generate_insights", generate_insights_node)
    
    # 엣지 추가
    graph.add_edge(START, "read_data_metadata")
    
    # 조건부 엣지: 메타데이터 읽기 성공 여부에 따라 진행 또는 종료
    def should_continue_after_metadata(state: DataAnalysisREPLState) -> Literal["generate_code", END]:
        """메타데이터 읽기 후 진행 여부 판단"""
        if state.get("status") == "error":
            return END
        return "generate_code"
    
    graph.add_conditional_edges(
        "read_data_metadata",
        should_continue_after_metadata,
        {
            "generate_code": "generate_code",
            END: END
        }
    )
    graph.add_edge("generate_code", "execute_in_repl")
    graph.add_edge("execute_in_repl", "validate_result")
    
    # 조건부 엣지: 검증 결과에 따라 재생성 또는 최종 결과 생성
    graph.add_conditional_edges(
        "validate_result",
        should_continue_loop,
        {
            "generate_code": "generate_code",  # 재시도: 코드 재생성
            "generate_insights": "generate_insights",  # 완료: 최종 결과 생성
            END: END  # 종료
        }
    )
    
    graph.add_edge("generate_insights", END)
    
    # 그래프 컴파일
    agent = graph.compile(checkpointer=checkpointer)
    
    return agent


# 기본 에이전트 인스턴스 생성
agent = create_repl_data_analysis_agent()

