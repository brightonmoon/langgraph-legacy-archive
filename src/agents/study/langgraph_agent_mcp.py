"""
LangGraph Agent MCP - MCP 도구를 통합한 LangGraph Agent
"""

# 표준 라이브러리
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.mcp.client.manager import get_mcp_manager
from src.tools.factory import ToolFactory
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


# State 정의
class AgentMCPState(TypedDict):
    """Agent MCP의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    user_query: str  # 사용자 쿼리
    model_response: str  # 모델 응답
    tool_calls: list  # Tool 호출 목록
    tool_results: list  # Tool 실행 결과
    llm_calls: int  # LLM 호출 횟수
    tool_calls_count: int  # Tool 호출 횟수
    mcp_tools_used: list  # 사용된 MCP 도구 목록
    local_tools_used: list  # 사용된 로컬 도구 목록


class LangGraphAgentMCP(BaseAgent):
    """MCP 도구를 통합한 LangGraph Agent 클래스"""
    
    def __init__(self, model_name: str = None):
        """Agent 초기화
        
        Args:
            model_name: 사용할 모델명 (예: "gpt-oss:120b-cloud", "kimi-k2:1t-cloud")
        """
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
        self.local_tools = ToolFactory.get_all_tools()
        self.mcp_manager = get_mcp_manager()
        self.tools = []
        self.model_with_tools = None
        self.graph = None
        
        # MCP 클라이언트 초기화 및 도구 통합
        self._initialize_mcp()
        self.build_model_with_tools()
        self.build_graph()
    
    def _initialize_mcp(self):
        """MCP 클라이언트 초기화 및 도구 통합"""
        try:
            import asyncio
            
            # 이벤트 루프가 실행 중인지 확인
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프에서는 task로 실행
                    asyncio.create_task(self._async_mcp_init())
                else:
                    # 새로운 루프에서 실행
                    asyncio.run(self._async_mcp_init())
            except RuntimeError:
                # 루프가 없는 경우 새로 생성
                asyncio.run(self._async_mcp_init())
                
        except Exception as e:
            print(f"⚠️ MCP 초기화 중 오류 발생: {str(e)}")
            print("로컬 도구만 사용합니다.")
            self.tools = self.local_tools.copy()
    
    async def _async_mcp_init(self):
        """비동기 MCP 초기화"""
        try:
            # MCP 클라이언트 초기화
            await self.mcp_manager.initialize_client()
            
            # 모든 도구 통합 (로컬 도구 + MCP 도구)
            mcp_tools = self.mcp_manager.get_mcp_tools()
            self.tools = self.local_tools + mcp_tools
            
            print(f"✅ MCP 통합 완료")
            print(f"   - 로컬 도구: {len(self.local_tools)}개")
            print(f"   - MCP 도구: {len(mcp_tools)}개")
            print(f"   - 총 도구: {len(self.tools)}개")
            
        except Exception as e:
            print(f"❌ MCP 초기화 실패: {str(e)}")
            self.tools = self.local_tools.copy()
    
    def build_model_with_tools(self):
        """Tool이 바인딩된 모델 생성"""
        if not self.model:
            print("❌ 모델이 초기화되지 않아 Tool을 바인딩할 수 없습니다.")
            return
        
        if not self.tools:
            print("⚠️ 사용 가능한 도구가 없습니다.")
            return
        
        try:
            # Tool을 모델에 바인딩
            self.model_with_tools = self.model.bind_tools(self.tools)
            print(f"✅ {len(self.tools)}개의 Tool이 모델에 바인딩되었습니다.")
                
        except Exception as e:
            print(f"❌ Tool 바인딩 중 오류 발생: {str(e)}")
            self.model_with_tools = None
    
    def input_processor(self, state: AgentMCPState) -> AgentMCPState:
        """입력 처리 노드"""
        print(f"🔍 입력 처리 중: {state['user_query']}")
        
        # 사용자 메시지를 메시지 히스토리에 추가
        user_message = HumanMessage(content=state['user_query'])
        
        return {
            "messages": [user_message],
            "llm_calls": state.get("llm_calls", 0),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "mcp_tools_used": state.get("mcp_tools_used", []),
            "local_tools_used": state.get("local_tools_used", [])
        }
    
    def llm_call(self, state: AgentMCPState) -> AgentMCPState:
        """LLM 호출 노드 (Tool calling 지원)"""
        if not self.model_with_tools:
            return {
                "model_response": "❌ Tool이 바인딩된 모델이 초기화되지 않았습니다.",
                "llm_calls": state.get("llm_calls", 0) + 1
            }
        
        try:
            print("🤖 LLM 호출 중...")
            
            # 시스템 메시지 설정 (동적 도구 설명 사용)
            local_tools_desc = ToolFactory.get_tools_description()
            mcp_tools_desc = self._get_mcp_tools_description()
            
            system_message = SystemMessage(
                content=f"""당신은 도움이 되는 AI 어시스턴트입니다. 
사용자의 질문에 정확하고 유용한 답변을 제공하세요.

사용 가능한 도구들:
로컬 도구:
{local_tools_desc}

MCP 도구:
{mcp_tools_desc}

필요한 경우 적절한 도구를 사용하여 사용자의 질문에 답변하세요."""
            )
            
            # 메시지 리스트 구성 (시스템 메시지 + 기존 메시지들)
            messages = [system_message] + state["messages"]
            
            # 모델 호출
            response = self.model_with_tools.invoke(messages)
            
            # AI 메시지를 메시지 히스토리에 추가
            ai_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
            
            return {
                "messages": [ai_message],
                "model_response": response.content,
                "tool_calls": response.tool_calls or [],
                "llm_calls": state.get("llm_calls", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            return {
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def _get_mcp_tools_description(self) -> str:
        """MCP 도구 설명 생성"""
        mcp_tools = self.mcp_manager.get_mcp_tools()
        if not mcp_tools:
            return "- MCP 도구 없음"
        
        descriptions = []
        for tool in mcp_tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    def tool_executor(self, state: AgentMCPState) -> AgentMCPState:
        """Tool 실행 노드 (MCP 지원)"""
        tool_calls = state.get("tool_calls", [])
        if not tool_calls:
            return state
        
        print(f"🔧 {len(tool_calls)}개의 Tool 실행 중...")
        
        tool_results = []
        mcp_tools_used = state.get("mcp_tools_used", [])
        local_tools_used = state.get("local_tools_used", [])
        
        # 도구 타입별로 분류
        local_tool_calls = []
        mcp_tool_calls = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            is_local_tool = any(tool.name == tool_name for tool in self.local_tools)
            
            if is_local_tool:
                local_tool_calls.append(tool_call)
            else:
                mcp_tool_calls.append(tool_call)
        
        # 로컬 도구 실행
        if local_tool_calls:
            print(f"   📦 로컬 도구 {len(local_tool_calls)}개 실행 중...")
            for tool_call in local_tool_calls:
                try:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_call_id = tool_call["id"]
                    
                    print(f"      🔧 [로컬] {tool_name} 실행: {tool_args}")
                    
                    # 로컬 도구 실행
                    result = self._execute_local_tool(tool_name, tool_args)
                    local_tools_used.append(tool_name)
                    
                    # ToolMessage 생성
                    tool_message = ToolMessage(
                        content=result,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    
                    tool_results.append(tool_message)
                    print(f"      ✅ [로컬] {tool_name} 실행 완료")
                    
                except Exception as e:
                    error_msg = f"❌ Tool 실행 중 오류 발생: {str(e)}"
                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"]
                    )
                    tool_results.append(tool_message)
                    print(f"      ❌ [로컬] {tool_call['name']} 실행 실패: {str(e)}")
        
        # MCP 도구 실행
        if mcp_tool_calls:
            print(f"   🌐 MCP 도구 {len(mcp_tool_calls)}개 실행 중...")
            for tool_call in mcp_tool_calls:
                try:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_call_id = tool_call["id"]
                    
                    print(f"      🔧 [MCP] {tool_name} 실행: {tool_args}")
                    
                    # MCP 도구 실행 (동기식으로 처리)
                    result = self._execute_mcp_tool_sync(tool_name, tool_args)
                    mcp_tools_used.append(tool_name)
                    
                    # ToolMessage 생성
                    tool_message = ToolMessage(
                        content=result,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    
                    tool_results.append(tool_message)
                    print(f"      ✅ [MCP] {tool_name} 실행 완료")
                    
                except Exception as e:
                    error_msg = f"❌ Tool 실행 중 오류 발생: {str(e)}"
                    tool_message = ToolMessage(
                        content=error_msg,
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"]
                    )
                    tool_results.append(tool_message)
                    print(f"      ❌ [MCP] {tool_call['name']} 실행 실패: {str(e)}")
        
        return {
            "messages": tool_results,
            "tool_results": tool_results,
            "tool_calls_count": state.get("tool_calls_count", 0) + len(tool_calls),
            "mcp_tools_used": mcp_tools_used,
            "local_tools_used": local_tools_used
        }
    
    def _execute_local_tool(self, tool_name: str, tool_args: dict) -> str:
        """로컬 도구 실행"""
        try:
            # 로컬 도구 찾기
            tool_function = None
            for tool in self.local_tools:
                if tool.name == tool_name:
                    tool_function = tool
                    break
            
            if not tool_function:
                raise ValueError(f"로컬 도구 '{tool_name}'을 찾을 수 없습니다.")
            
            # Tool 함수 직접 호출
            result = tool_function.invoke(tool_args)
            return result
            
        except Exception as e:
            raise Exception(f"로컬 도구 '{tool_name}' 실행 실패: {str(e)}")
    
    def _execute_mcp_tool_sync(self, tool_name: str, tool_args: dict) -> str:
        """MCP 도구 실행 (동기식 래퍼)"""
        try:
            import asyncio
            
            # 이벤트 루프가 실행 중인지 확인
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프에서는 task로 실행
                    task = asyncio.create_task(self.mcp_manager.execute_tool(tool_name, tool_args))
                    # 동기식으로 결과 대기
                    return asyncio.run_coroutine_threadsafe(self.mcp_manager.execute_tool(tool_name, tool_args), loop).result()
                else:
                    # 새로운 루프에서 실행
                    return asyncio.run(self.mcp_manager.execute_tool(tool_name, tool_args))
            except RuntimeError:
                # 루프가 없는 경우 새로 생성
                return asyncio.run(self.mcp_manager.execute_tool(tool_name, tool_args))
                
        except Exception as e:
            raise Exception(f"MCP 도구 '{tool_name}' 실행 실패: {str(e)}")
    
    def should_continue(self, state: AgentMCPState) -> Literal["tool_executor", "response_formatter"]:
        """Tool 실행 여부 결정"""
        tool_calls = state.get("tool_calls", [])
        llm_calls = state.get("llm_calls", 0)
        
        # 무한 루프 방지: 최대 10회 LLM 호출 제한
        if llm_calls >= 10:
            print(f"⚠️ 최대 LLM 호출 횟수(10회) 도달. 응답 생성합니다.")
            return "response_formatter"
        
        if tool_calls:
            print("🔧 Tool 실행이 필요합니다.")
            return "tool_executor"
        else:
            print("📝 최종 응답을 생성합니다.")
            return "response_formatter"
    
    def response_formatter(self, state: AgentMCPState) -> AgentMCPState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        # Tool 실행 결과가 있는 경우 추가 정보 포함
        tool_results = state.get("tool_results", [])
        mcp_tools_used = state.get("mcp_tools_used", [])
        local_tools_used = state.get("local_tools_used", [])
        
        if tool_results:
            formatted_response = f"🤖 LangGraph MCP Agent 응답:\n{state['model_response']}\n\n"
            
            if local_tools_used:
                formatted_response += "🔧 사용된 로컬 도구들:\n"
                for tool_name in local_tools_used:
                    formatted_response += f"• {tool_name}\n"
            
            if mcp_tools_used:
                formatted_response += "🌐 사용된 MCP 도구들:\n"
                for tool_name in mcp_tools_used:
                    formatted_response += f"• {tool_name}\n"
            
            formatted_response += "\n📊 실행 결과:\n"
            for result in tool_results:
                formatted_response += f"• {result.name}: {result.content}\n"
        else:
            formatted_response = f"🤖 LangGraph MCP Agent 응답:\n{state['model_response']}"
        
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
            builder = StateGraph(AgentMCPState)
            
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
            
            # 그래프 컴파일
            self.graph = builder.compile()
            
            print("✅ LangGraph MCP Agent가 성공적으로 빌드되었습니다.")
            
        except Exception as e:
            print(f"❌ 그래프 빌드 중 오류 발생: {str(e)}")
            self.graph = None
    
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
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
                "mcp_tools_used": [],
                "local_tools_used": []
            }
            
            # 그래프 실행
            result = self.graph.invoke(initial_state)
            
            return result["model_response"]
            
        except Exception as e:
            return f"❌ 그래프 실행 중 오류 발생: {str(e)}"
    
    def stream(self, query: str):
        """스트리밍 응답 생성"""
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
                "mcp_tools_used": [],
                "local_tools_used": []
            }
            
            # 그래프 스트리밍 실행
            for chunk in self.graph.stream(initial_state):
                yield chunk
                
        except Exception as e:
            yield {"error": f"❌ 그래프 실행 중 오류 발생: {str(e)}"}
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스 - MCP Tool calling 지원"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 LangGraph MCP Agent 대화 시작")
        print("=" * 50)
        print("💡 '/help' 입력시 도구 설명을 볼 수 있습니다.")
        print("💡 '/mcp' 입력시 MCP 상태를 볼 수 있습니다.")
        print("💡 '/servers' 입력시 서버 상태를 볼 수 있습니다.")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("=" * 50)
        
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
                
                # /mcp 명령어 처리
                if user_input.lower() == '/mcp':
                    self.show_mcp_status()
                    continue
                
                # /servers 명령어 처리
                if user_input.lower() == '/servers':
                    self.show_server_status()
                    continue
                
                if not user_input:
                    print("❌ 질문을 입력해주세요.")
                    continue
                
                print(f"\n🔍 질문: {user_input}")
                print("🤖 답변:")
                print("-" * 30)
                
                # 응답 생성
                response = self.generate_response(user_input)
                print(response)
                print("-" * 30)
                
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
        print("=" * 50)
        
        # 로컬 도구
        print(f"\n🔧 로컬 도구 ({len(self.local_tools)}개):")
        for tool in self.local_tools:
            print(f"\n   • {tool.name}")
            print(f"     설명: {tool.description}")
            
            # 도구의 파라미터 정보 표시
            if hasattr(tool, 'args_schema') and tool.args_schema:
                print(f"     파라미터:")
                for field_name, field_info in tool.args_schema.model_fields.items():
                    print(f"       - {field_name}: {field_info.description or '설명 없음'}")
        
        # MCP 도구
        mcp_tools = self.mcp_manager.get_mcp_tools()
        if mcp_tools:
            print(f"\n🌐 MCP 도구 ({len(mcp_tools)}개):")
            for tool in mcp_tools:
                print(f"\n   • {tool.name}")
                print(f"     설명: {tool.description}")
        
        print(f"\n💡 사용 예시:")
        # 동적으로 사용 예시 생성
        example_messages = []
        for tool in self.local_tools:
            if tool.name == "calculator":
                example_messages.append("   - '2 + 3 * 4 계산해줘' (calculator 도구 사용)")
            elif tool.name == "brave_search":
                example_messages.append("   - '파이썬 최신 버전 검색해줘' (brave_search 도구 사용)")
        
        if example_messages:
            for msg in example_messages:
                print(msg)
        else:
            print("   (도구 사용 예시 없음)")
        print("=" * 50)
    
    def show_mcp_status(self) -> None:
        """MCP 상태 표시"""
        status = self.mcp_manager.get_status()
        print(f"\n📊 MCP 클라이언트 상태:")
        print("=" * 40)
        for key, value in status.items():
            print(f"   {key}: {value}")
        print("=" * 40)
    
    def show_server_status(self) -> None:
        """서버 상태 표시"""
        self.mcp_manager.show_server_status()
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return (self.model is not None and 
                self.model_with_tools is not None and 
                self.graph is not None)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "LangGraph MCP Agent",
                "model": self.model_name,
                "architecture": "StateGraph 기반 + MCP Tool calling",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        mcp_status = self.mcp_manager.get_status()
        
        return {
            "type": "LangGraph MCP Agent",
            "model": self.model_name,
            "architecture": "StateGraph 기반 + MCP Tool calling",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> input_processor -> llm_call -> [tool_executor] -> response_formatter -> END",
            "state_schema": list(AgentMCPState.__annotations__.keys()),
            "local_tools": [tool.name for tool in self.local_tools],
            "mcp_tools": [tool.name for tool in self.mcp_manager.get_mcp_tools()],
            "total_tools": len(self.tools),
            "mcp_status": mcp_status,
            "features": ["상태 관리", "노드 기반", "MCP Tool calling", "확장 가능", "디버깅 용이"]
        }
