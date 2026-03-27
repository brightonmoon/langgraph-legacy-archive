"""
LangGraph Agent Tools - Tool calling을 지원하는 개선된 LangGraph Agent
"""

# 표준 라이브러리
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal, Optional, Dict, Any

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.agents.memory.checkpointer import get_default_checkpointer
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.token_usage_tracker import TokenUsageTracker
from src.tools.factory import ToolFactory


# State 정의
class AgentToolsState(TypedDict, total=False):
    """Agent Tools의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    user_query: str  # 사용자 쿼리
    model_response: str  # 모델 응답
    tool_calls: list  # Tool 호출 목록
    tool_results: list  # Tool 실행 결과
    llm_calls: int  # LLM 호출 횟수
    tool_calls_count: int  # Tool 호출 횟수
    token_usage: Dict[str, Any]  # 토큰 사용량 정보


class LangGraphAgentTools(BaseAgent):
    """Tool calling을 지원하는 개선된 LangGraph Agent 클래스"""
    
    def __init__(
        self,
        model_name: str = None,
        checkpointer = None,
        use_default_checkpointer: bool = True,
    ):
        """Agent 초기화
        
        Args:
            model_name: 사용할 모델명 (예: "gpt-oss:120b-cloud", "kimi-k2:1t-cloud")
            checkpointer: 상태 지속성을 위한 Checkpointer (None이면 기본 메모리 Checkpointer 사용)
            use_default_checkpointer: True일 때 기본 메모리 Checkpointer 사용 (LangGraph Dev에서는 False 권장)
        """
        # Checkpointer가 없으면 기본 메모리 Checkpointer 사용
        if checkpointer is None and use_default_checkpointer:
            checkpointer = get_default_checkpointer()
        
        super().__init__(checkpointer=checkpointer)
        
        setup_langsmith_disabled()
        
        # 모델 초기화 - init_chat_model 직접 사용
        model_str = model_name or os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
        if model_str and not model_str.startswith("ollama:"):
            model_str = f"ollama:{model_str}"
        
        self.model = init_chat_model_helper(
            model_name=model_str,
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        self.model_name = model_name or "gpt-oss:120b-cloud"
        self.tools = ToolFactory.get_all_tools()
        self.model_with_tools = None
        self.graph = None
        self.build_model_with_tools()
        self.build_graph()
    
    def build_model_with_tools(self):
        """Tool이 바인딩된 모델 생성"""
        if not self.model:
            print("❌ 모델이 초기화되지 않아 Tool을 바인딩할 수 없습니다.")
            return
        
        try:
            # Tool을 모델에 바인딩
            self.model_with_tools = self.model.bind_tools(self.tools)
            print(f"✅ {len(self.tools)}개의 Tool이 모델에 바인딩되었습니다.")
                
        except Exception as e:
            print(f"❌ Tool 바인딩 중 오류 발생: {str(e)}")
            self.model_with_tools = None
    
    def input_processor(self, state: AgentToolsState) -> AgentToolsState:
        """입력 처리 노드"""
        print(f"🔍 입력 처리 중: {state['user_query']}")
        
        # 사용자 메시지를 메시지 히스토리에 추가
        user_message = HumanMessage(content=state['user_query'])
        
        # token_usage 초기화 (없는 경우)
        token_usage = state.get("token_usage")
        if not token_usage:
            token_usage = {
                "total": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                "by_model": {}
            }
        
        return {
            "messages": [user_message],
            "llm_calls": state.get("llm_calls", 0),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "token_usage": token_usage
        }
    
    def llm_call(self, state: AgentToolsState) -> AgentToolsState:
        """LLM 호출 노드 (Tool calling 지원)"""
        if not self.model_with_tools:
            return {
                "model_response": "❌ Tool이 바인딩된 모델이 초기화되지 않았습니다.",
                "llm_calls": state.get("llm_calls", 0) + 1,
                "token_usage": state.get("token_usage", {})
            }
        
        try:
            print("🤖 LLM 호출 중...")
            
            # TokenUsageTracker 생성 및 callback 가져오기
            tracker = TokenUsageTracker()
            callback = tracker.get_callback()
            
            # 시스템 메시지 설정 (동적 도구 설명 사용)
            local_tools_desc = ToolFactory.get_tools_description()
            
            system_message = SystemMessage(
                content=f"""당신은 도움이 되는 AI 어시스턴트입니다. 
사용자의 질문에 정확하고 유용한 답변을 제공하세요.

사용 가능한 도구들:
{local_tools_desc}

필요한 경우 적절한 도구를 사용하여 사용자의 질문에 답변하세요."""
            )
            
            # 메시지 리스트 구성 (시스템 메시지 + 기존 메시지들)
            messages = [system_message] + state["messages"]
            
            # 모델 호출 (callback 포함)
            response = self.model_with_tools.invoke(
                messages,
                config={"callbacks": [callback]}
            )
            
            # AI 메시지를 메시지 히스토리에 추가
            ai_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
            
            # 토큰 사용량 추적 및 업데이트
            current_token_usage = state.get("token_usage", {})
            updated_token_usage = tracker.update_token_usage(
                current_token_usage,
                response,
                model_name=self.model_name
            )
            
            return {
                "messages": [ai_message],
                "model_response": response.content,
                "tool_calls": response.tool_calls or [],
                "llm_calls": state.get("llm_calls", 0) + 1,
                "token_usage": updated_token_usage
            }
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            return {
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1,
                "token_usage": state.get("token_usage", {})
            }
    
    def tool_executor(self, state: AgentToolsState) -> AgentToolsState:
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
                
                # Tool 실행 - 직접 함수 호출
                tool_function = None
                for tool in self.tools:
                    if tool.name == tool_name:
                        tool_function = tool
                        break
                
                if not tool_function:
                    raise ValueError(f"Tool '{tool_name}'을 찾을 수 없습니다.")
                
                # Tool 함수 직접 호출
                result = tool_function.invoke(tool_args)
                
                # ToolMessage 생성
                tool_message = ToolMessage(
                    content=result,
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
    
    def should_continue(self, state: AgentToolsState) -> Literal["tool_executor", "response_formatter"]:
        """Tool 실행 여부 결정"""
        tool_calls = state.get("tool_calls", [])
        
        if tool_calls:
            print("🔧 Tool 실행이 필요합니다.")
            return "tool_executor"
        else:
            print("📝 최종 응답을 생성합니다.")
            return "response_formatter"
    
    def response_formatter(self, state: AgentToolsState) -> AgentToolsState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        # Tool 실행 결과가 있는 경우 추가 정보 포함
        tool_results = state.get("tool_results", [])
        if tool_results:
            formatted_response = f"🤖 Agent 응답:\n{state['model_response']}\n\n"
            formatted_response += "🔧 사용된 도구들:\n"
            for result in tool_results:
                formatted_response += f"• {result.name}: {result.content}\n"
        else:
            formatted_response = f"🤖 Agent 응답:\n{state['model_response']}"
        
        return {
            "model_response": formatted_response
        }
    
    def build_graph(self):
        """LangGraph 빌드"""
        if not self.model_with_tools:
            print("❌ Tool이 바인딩된 모델이 초기화되지 않아 그래프를 빌드할 수 없습니다.")
            return
        
        try:
            # StateGraph 생성
            builder = StateGraph(AgentToolsState)
            
            # 노드 추가
            builder.add_node("input_processor", self.input_processor)
            builder.add_node("llm_call", self.llm_call)
            builder.add_node("tool_executor", self.tool_executor)
            builder.add_node("response_formatter", self.response_formatter)
            
            # 엣지 추가
            builder.add_edge(START, "input_processor")
            builder.add_edge("input_processor", "llm_call")
            
            # 조건부 엣지 추가 (Tool 실행 여부에 따라)
            builder.add_conditional_edges(
                "llm_call",
                self.should_continue,
                ["tool_executor", "response_formatter"]
            )
            
            builder.add_edge("tool_executor", "llm_call")  # Tool 실행 후 다시 LLM 호출
            builder.add_edge("response_formatter", END)
            
            # 그래프 컴파일 (Checkpointer 포함)
            if self.checkpointer:
                self.graph = builder.compile(checkpointer=self.checkpointer)
                print("✅ LangGraph Agent Tools가 Checkpointer와 함께 성공적으로 빌드되었습니다.")
            else:
                self.graph = builder.compile()
                print("✅ LangGraph Agent Tools가 성공적으로 빌드되었습니다.")
            
        except Exception as e:
            print(f"❌ 그래프 빌드 중 오류 발생: {str(e)}")
            self.graph = None
    
    def generate_response(self, query: str, thread_id: Optional[str] = None) -> str:
        """쿼리에 대한 응답 생성
        
        Args:
            query: 사용자 쿼리
            thread_id: 스레드 ID (Checkpointer 사용 시 멀티 턴 대화를 위해 필요)
        
        Returns:
            Agent 응답 문자열
        """
        if not self.graph:
            return "❌ 그래프가 초기화되지 않았습니다."
        
        try:
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_query": query,
                "model_response": "",
                "tool_calls": [],
                "tool_results": [],
                "llm_calls": 0,
                "tool_calls_count": 0,
                "token_usage": {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    },
                    "by_model": {}
                }
            }
            
            # Checkpointer가 있으면 thread_id를 config에 포함
            if self.checkpointer and thread_id:
                config = {"configurable": {"thread_id": thread_id}}
                result = self.graph.invoke(initial_state, config)
            else:
                # Checkpointer가 없거나 thread_id가 없으면 일반 실행
                result = self.graph.invoke(initial_state)
            
            # 토큰 사용량 정보 추가 (선택적)
            response = result["model_response"]
            token_usage = result.get("token_usage", {})
            if token_usage and token_usage.get("total", {}).get("total_tokens", 0) > 0:
                from src.utils.token_usage_tracker import TokenUsageTracker
                tracker = TokenUsageTracker()
                summary = tracker.get_summary(token_usage)
                response += f"\n\n📊 {summary}"
            
            return response
            
        except Exception as e:
            return f"❌ 그래프 실행 중 오류 발생: {str(e)}"
    
    def stream(self, query: str, thread_id: Optional[str] = None):
        """스트리밍 응답 생성
        
        Args:
            query: 사용자 쿼리
            thread_id: 스레드 ID (Checkpointer 사용 시 멀티 턴 대화를 위해 필요)
        """
        if not self.graph:
            yield {"error": "❌ 그래프가 초기화되지 않았습니다."}
            return
        
        try:
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_query": query,
                "model_response": "",
                "tool_calls": [],
                "tool_results": [],
                "llm_calls": 0,
                "tool_calls_count": 0,
                "token_usage": {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    },
                    "by_model": {}
                }
            }
            
            # Checkpointer가 있으면 thread_id를 config에 포함
            if self.checkpointer and thread_id:
                config = {"configurable": {"thread_id": thread_id}}
                for chunk in self.graph.stream(initial_state, config):
                    yield chunk
            else:
                # Checkpointer가 없거나 thread_id가 없으면 일반 실행
                for chunk in self.graph.stream(initial_state):
                    yield chunk
                
        except Exception as e:
            yield {"error": f"❌ 그래프 실행 중 오류 발생: {str(e)}"}
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스 - Tool calling 지원"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 LangGraph Agent Tools 대화 시작")
        print("=" * 40)
        print("💡 '/help' 입력시 도구 설명을 볼 수 있습니다.")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("=" * 40)
        
        while True:
            try:
                # 사용자 입력 받기
                if query:
                    user_input = query
                    query = None  # 한 번만 사용
                else:
                    user_input = input("\n👤 질문을 입력하세요: ").strip()
                
                # 종료 조건 확인
                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
                
                # /help 명령어 처리
                if user_input.lower() == '/help':
                    self.show_help()
                    continue
                
                if not user_input:
                    print("❌ 질문을 입력해주세요.")
                    continue
                
                print(f"\n🔍 질문: {user_input}")
                print("🤖 답변:")
                print("-" * 20)
                
                # 응답 생성
                response = self.generate_response(user_input)
                print(response)
                print("-" * 20)
                
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+C로 대화를 종료합니다. 안녕히 가세요!")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {str(e)}")
                print("계속하려면 Enter를 누르세요...")
                try:
                    input()
                except KeyboardInterrupt:
                    print("\n\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
    
    def show_help(self) -> None:
        """도구 설명 표시"""
        print(f"\n📚 사용 가능한 도구:")
        print("=" * 40)
        for tool in self.tools:
            print(f"\n🔧 {tool.name}")
            print(f"   설명: {tool.description}")
            
            # 도구의 파라미터 정보 표시
            if hasattr(tool, 'args_schema') and tool.args_schema:
                print(f"   파라미터:")
                for field_name, field_info in tool.args_schema.model_fields.items():
                    print(f"     - {field_name}: {field_info.description or '설명 없음'}")
        
        print(f"\n💡 사용 예시:")
        # 동적으로 사용 예시 생성
        example_messages = []
        for tool in self.tools:
            if tool.name == "calculator":
                example_messages.append("   - '2 + 3 * 4 계산해줘' (calculator 도구 사용)")
            elif tool.name == "brave_search":
                example_messages.append("   - '파이썬 최신 버전 검색해줘' (brave_search 도구 사용)")
        
        if example_messages:
            for msg in example_messages:
                print(msg)
        else:
            print("   (도구 사용 예시 없음)")
        print("=" * 40)
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return (self.model is not None and 
                self.model_with_tools is not None and 
                self.graph is not None)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "LangGraph Agent Tools",
                "model": self.model_name,
                "architecture": "StateGraph 기반 + Tool calling",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "LangGraph Agent Tools",
            "model": self.model_name,
            "architecture": "StateGraph 기반 + Tool calling",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> input_processor -> llm_call -> [tool_executor] -> response_formatter -> END",
            "state_schema": list(AgentToolsState.__annotations__.keys()),
            "tools": [tool.name for tool in self.tools],
            "tool_count": len(self.tools),
            "features": ["상태 관리", "노드 기반", "Tool calling", "확장 가능", "디버깅 용이"]
        }


# ============================================
# LangGraph dev 환경용 export 함수
# ============================================

def create_langgraph_agent_tools_graph(
    model_name: str = None,
    checkpointer = None
):
    """LangGraph dev 환경에서 사용할 LangGraphAgentTools 그래프 생성
    
    Args:
        model_name: 사용할 모델명 (None이면 환경변수에서 자동 결정)
        checkpointer: Checkpointer 인스턴스 (None이면 기본 메모리 Checkpointer 사용)
        
    Returns:
        LangGraph CompiledStateGraph
    """
    agent = LangGraphAgentTools(
        model_name=model_name,
        checkpointer=checkpointer,
        use_default_checkpointer=False,
    )
    return agent.graph


def _get_default_langgraph_agent_tools():
    """기본 LangGraphAgentTools 그래프 생성 (lazy initialization)
    
    환경변수에서 자동으로 설정을 읽어옵니다.
    """
    return create_langgraph_agent_tools_graph()


# LangGraph dev에서 참조할 agent 변수
agent = _get_default_langgraph_agent_tools()
