"""
Python REPL Agent (Study)

LangChain의 Python REPL 도구를 사용하여 Python 코드를 실행하는 LangGraph 기반 Agent

⚠️ 현재 상태:
- 단순한 독립 Python 실행기로 구현됨
- 코드 생성 → 실행 → 결과 반환의 기본적인 워크플로우

🔄 향후 개선 필요:
- 단순 독립 실행기가 아닌 코드 생성 후 커널에 전달하는 로직
- 실행 결과를 받아 상태를 업데이트하는 반복적 워크플로우
- 코드 생성 → 커널 전달 → 실행 결과 수신 → 상태 업데이트 → 재생성 (필요시)

현재 워크플로우:
1. 사용자 쿼리 수신
2. LLM이 Python REPL 도구를 사용하여 코드 생성 및 실행
3. 실행 결과 반환

테스트 목적:
- LangGraph에서 Python REPL 기능 동작 확인
- OSS 모델에서도 정상 동작하는지 확인
"""

import os
from typing import TypedDict, Annotated, Optional, Literal
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain.tools import tool
from langchain_experimental.utilities import PythonREPL
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper

load_dotenv()

# Python REPL Agent State 정의
class PythonREPLAgentState(MessagesState, total=False):
    """Python REPL Agent의 상태"""
    query: Optional[str]  # 사용자 쿼리
    model_response: Optional[str]  # 모델 응답
    tool_calls: Optional[list]  # Tool 호출 목록
    tool_results: Optional[list]  # Tool 실행 결과
    llm_calls: int  # LLM 호출 횟수
    tool_calls_count: int  # Tool 호출 횟수


def create_python_repl_agent(
    model: str = "ollama:codegemma:latest",
    checkpointer=None
):
    """Python REPL Agent 생성
    
    Args:
        model: 사용할 모델명 (기본값: ollama:codegemma:latest)
        checkpointer: 상태 지속성을 위한 Checkpointer (None이면 메모리 Checkpointer 사용)
    
    Returns:
        LangGraph CompiledStateGraph
    """
    setup_langsmith_disabled()
    
    # 모델 초기화
    model_str = model.strip() if model else os.getenv("OLLAMA_MODEL_NAME", "ollama:codegemma:latest")
    if not model_str.startswith("ollama:") and not model_str.startswith("anthropic:") and not model_str.startswith("openai:"):
        model_str = f"ollama:{model_str}"
    
    llm = init_chat_model_helper(
        model_name=model_str,
        api_key=os.getenv("OLLAMA_API_KEY"),
        temperature=0.7
    )
    
    if not llm:
        raise ValueError(f"모델 초기화 실패: {model_str}")
    
    print(f"✅ Python REPL Agent 모델 로드 완료: {model_str}")
    
    # Python REPL 도구 생성
    python_repl = PythonREPL()
    
    @tool("python_repl")
    def python_repl_tool(query: str) -> str:
        """A Python shell. Use this to execute python commands. 
        Input should be a valid python command. 
        If you want to see the output of a value, you should print it out with `print(...)`.
        This tool can execute arbitrary code on the host machine. Use with caution.
        
        Args:
            query: Python 코드 문자열
            
        Returns:
            코드 실행 결과
        """
        return python_repl.run(query)
    
    tools = [python_repl_tool]
    
    # 모델에 도구 바인딩
    model_with_tools = llm.bind_tools(tools)
    print(f"✅ Python REPL 도구가 모델에 바인딩되었습니다.")
    
    # 노드 함수들 정의
    def input_processor(state: PythonREPLAgentState) -> PythonREPLAgentState:
        """입력 처리 노드"""
        query = state.get("query", "")
        if not query and state.get("messages"):
            # messages에서 마지막 HumanMessage 추출
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    query = msg.content
                    break
        
        print(f"🔍 입력 처리 중: {query}")
        
        user_message = HumanMessage(content=query)
        
        return {
            "messages": [user_message],
            "query": query,
            "llm_calls": state.get("llm_calls", 0),
            "tool_calls_count": state.get("tool_calls_count", 0)
        }
    
    def llm_call(state: PythonREPLAgentState) -> PythonREPLAgentState:
        """LLM 호출 노드 (Tool calling 지원)"""
        try:
            print("🤖 LLM 호출 중...")
            
            system_message = SystemMessage(
                content="""You are a helpful AI assistant that can execute Python code using the Python REPL tool.
When the user asks you to perform calculations, write code, or solve problems, use the python_repl tool to execute Python code.
Always print the result so the user can see it.
Be careful with code execution - only execute safe code."""
            )
            
            messages = [system_message] + state["messages"]
            
            response = model_with_tools.invoke(messages)
            
            ai_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
            
            return {
                "messages": [ai_message],
                "model_response": response.content,
                "tool_calls": response.tool_calls or [],
                "llm_calls": state.get("llm_calls", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            print(error_msg)
            return {
                "messages": [AIMessage(content=error_msg)],
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def tool_executor(state: PythonREPLAgentState) -> PythonREPLAgentState:
        """Tool 실행 노드"""
        tool_calls = state.get("tool_calls", [])
        if not tool_calls:
            return state
        
        print(f"🔧 {len(tool_calls)}개의 Tool 실행 중...")
        
        tool_results = []
        for tool_call in tool_calls:
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                print(f"   🔧 {tool_name} 실행: {tool_args}")
                
                # Tool 실행 - 도구 목록에서 찾아서 직접 호출
                tool_function = None
                for tool in tools:
                    if tool.name == tool_name:
                        tool_function = tool
                        break
                
                if not tool_function:
                    raise ValueError(f"Tool '{tool_name}'을 찾을 수 없습니다.")
                
                # Tool 함수 직접 호출
                result = tool_function.invoke(tool_args)
                
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                
                tool_results.append(tool_message)
                print(f"   ✅ {tool_name} 실행 완료")
                
            except Exception as e:
                error_msg = f"❌ Tool 실행 중 오류 발생: {str(e)}"
                tool_message = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"]
                )
                tool_results.append(tool_message)
                print(f"   ❌ {tool_call['name']} 실행 실패: {str(e)}")
        
        return {
            "messages": tool_results,
            "tool_results": tool_results,
            "tool_calls_count": state.get("tool_calls_count", 0) + len(tool_calls)
        }
    
    def should_continue(state: PythonREPLAgentState) -> Literal["tool_executor", "response_formatter"]:
        """Tool 실행 여부 결정"""
        tool_calls = state.get("tool_calls", [])
        
        if tool_calls:
            print("🔧 Tool 실행이 필요합니다.")
            return "tool_executor"
        else:
            print("📝 최종 응답을 생성합니다.")
            return "response_formatter"
    
    def response_formatter(state: PythonREPLAgentState) -> PythonREPLAgentState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        tool_results = state.get("tool_results", [])
        if tool_results:
            formatted_response = f"{state.get('model_response', '')}\n\n"
            formatted_response += "실행 결과:\n"
            for result in tool_results:
                formatted_response += f"{result.content}\n"
        else:
            formatted_response = state.get("model_response", "")
        
        return {
            "model_response": formatted_response
        }
    
    # 그래프 빌드
    graph = StateGraph(PythonREPLAgentState)
    
    # 노드 추가
    graph.add_node("input_processor", input_processor)
    graph.add_node("llm_call", llm_call)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("response_formatter", response_formatter)
    
    # 엣지 추가
    graph.add_edge(START, "input_processor")
    graph.add_edge("input_processor", "llm_call")
    
    # 조건부 엣지 추가
    graph.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_executor": "tool_executor",
            "response_formatter": "response_formatter"
        }
    )
    
    graph.add_edge("tool_executor", "llm_call")  # Tool 실행 후 다시 LLM 호출
    graph.add_edge("response_formatter", END)
    
    # 그래프 컴파일
    if checkpointer:
        compiled_graph = graph.compile(checkpointer=checkpointer)
    else:
        compiled_graph = graph.compile()
    
    print("✅ Python REPL Agent가 성공적으로 생성되었습니다.")
    
    return compiled_graph


# LangGraph Studio용 agent 변수
_agent_cache = None

def _get_default_agent():
    """기본 Python REPL Agent 그래프 생성 (lazy initialization with caching)"""
    global _agent_cache
    if _agent_cache is None:
        try:
            _agent_cache = create_python_repl_agent()
        except Exception as e:
            import traceback
            error_msg = f"⚠️ 에이전트 생성 실패: {str(e)}"
            print(error_msg)
            print("   환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요.")
            print("   상세 에러:")
            traceback.print_exc()
            raise
    return _agent_cache

# LangGraph Studio에서 참조할 agent 변수
try:
    agent = _get_default_agent()
except Exception as e:
    import traceback
    print(f"❌ Python REPL Agent 초기화 실패:")
    traceback.print_exc()
    raise RuntimeError(
        f"Python REPL Agent를 초기화할 수 없습니다: {str(e)}\n"
        "환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요."
    ) from e

