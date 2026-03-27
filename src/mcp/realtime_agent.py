"""
실시간 설정 적용을 지원하는 MCP Agent
"""

# 표준 라이브러리
import asyncio
import hashlib
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal, Dict, Any, List

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (같은 패키지 내 - 상대 import 허용)
from .client.manager import get_mcp_manager
from .config.manager import get_config_manager

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.tools.factory import ToolFactory
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.token_usage_tracker import TokenUsageTracker


# State 정의
class RealtimeMCPAgentState(TypedDict, total=False):
    """실시간 MCP Agent의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    user_query: str  # 사용자 쿼리
    model_response: str  # 모델 응답
    tool_calls: list  # Tool 호출 목록
    tool_results: list  # Tool 실행 결과
    llm_calls: int  # LLM 호출 횟수
    tool_calls_count: int  # Tool 호출 횟수
    mcp_tools_used: list  # 사용된 MCP 도구 목록
    local_tools_used: list  # 사용된 로컬 도구 목록
    config_reloaded: bool  # 설정이 리로드되었는지 여부
    token_usage: Dict[str, Any]  # 토큰 사용량 정보


class RealtimeMCPAgent(BaseAgent):
    """실시간 설정 적용을 지원하는 MCP LangGraph Agent"""
    
    def __init__(self, auto_reload: bool = True, reload_interval: int = 5):
        """Agent 초기화"""
        setup_langsmith_disabled()
        
        # 모델 초기화 - init_chat_model 직접 사용
        model_str = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
        if not model_str.startswith("ollama:"):
            model_str = f"ollama:{model_str}"
        
        self.model = init_chat_model_helper(
            model_name=model_str,
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        self.mcp_manager = get_mcp_manager()
        self.config_manager = get_config_manager()
        self.tools = []
        self.model_with_tools = None
        self.graph = None
        
        # 실시간 리로드 설정
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval
        self.last_config_hash = None
        self.monitoring_task = None
        
        # 비동기 초기화
        self._initialize_async()
    
    def _initialize_async(self):
        """비동기 초기화 실행"""
        try:
            # 이벤트 루프가 실행 중인지 확인
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프에서는 task로 실행
                asyncio.create_task(self._async_init())
            else:
                # 새로운 루프에서 실행
                asyncio.run(self._async_init())
        except RuntimeError:
            # 루프가 없는 경우 새로 생성
            asyncio.run(self._async_init())
    
    async def _async_init(self):
        """비동기 초기화 로직"""
        # 초기 설정 해시값 저장
        self.last_config_hash = self._get_config_hash()
        
        # MCP 클라이언트 초기화
        await self.mcp_manager.initialize_client()
        
        # 도구 가져오기
        self.tools = self.mcp_manager.get_tools()
        
        # 모델과 그래프 빌드
        self.build_model_with_tools()
        self.build_graph()
        
        # 실시간 모니터링 시작
        if self.auto_reload:
            self.monitoring_task = asyncio.create_task(self._monitor_config_changes())
    
    def _get_config_hash(self) -> str:
        """설정 파일의 해시값 반환"""
        if os.path.exists(self.config_manager.config_path):
            with open(self.config_manager.config_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        return None
    
    async def _monitor_config_changes(self):
        """설정 파일 변경 모니터링"""
        while True:
            try:
                await asyncio.sleep(self.reload_interval)
                await self._check_and_reload()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ 설정 모니터링 중 오류: {str(e)}")
    
    async def _check_and_reload(self):
        """설정 파일 변경 감지 및 자동 리로드"""
        current_hash = self._get_config_hash()
        
        if current_hash != self.last_config_hash:
            print(f"\n🔄 설정 파일 변경 감지! ({datetime.now().strftime('%H:%M:%S')})")
            
            # 설정 파일 다시 로드
            self.config_manager.load_config()
            
            # MCP 클라이언트 재초기화
            await self.mcp_manager.initialize_client()
            
            # 도구 목록 업데이트
            self.tools = self.mcp_manager.get_tools()
            
            # 모델 재빌드
            self.build_model_with_tools()
            self.build_graph()
            
            # 새로운 해시값 저장
            self.last_config_hash = current_hash
            
            # 상태 표시
            status = self.mcp_manager.get_status()
            print(f"✅ 리로드 완료 - MCP 도구 수: {status['mcp_tools_count']}")
            print(f"   총 도구 수: {status['total_tools_count']}")
    
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
            print(f"   - 로컬 도구: {len(self.mcp_manager.get_local_tools())}개")
            print(f"   - MCP 도구: {len(self.mcp_manager.get_mcp_tools())}개")
                
        except Exception as e:
            print(f"❌ Tool 바인딩 중 오류 발생: {str(e)}")
            self.model_with_tools = None
    
    def input_processor(self, state: RealtimeMCPAgentState) -> RealtimeMCPAgentState:
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
            "mcp_tools_used": state.get("mcp_tools_used", []),
            "local_tools_used": state.get("local_tools_used", []),
            "config_reloaded": state.get("config_reloaded", False),
            "token_usage": token_usage
        }
    
    def llm_call(self, state: RealtimeMCPAgentState) -> RealtimeMCPAgentState:
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
            
            # 모델 호출 (callback 포함)
            response = self.model_with_tools.invoke(
                messages,
                config={"callbacks": [callback]}
            )
            
            # AI 메시지를 메시지 히스토리에 추가
            ai_message = AIMessage(content=response.content, tool_calls=response.tool_calls)
            
            # 토큰 사용량 추적 및 업데이트
            current_token_usage = state.get("token_usage", {})
            model_name = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
            updated_token_usage = tracker.update_token_usage(
                current_token_usage,
                response,
                model_name=model_name
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
    
    def _get_mcp_tools_description(self) -> str:
        """MCP 도구 설명 생성"""
        mcp_tools = self.mcp_manager.get_mcp_tools()
        if not mcp_tools:
            return "- MCP 도구 없음"
        
        descriptions = []
        for tool in mcp_tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        
        return "\n".join(descriptions)
    
    async def tool_executor(self, state: RealtimeMCPAgentState) -> RealtimeMCPAgentState:
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
            is_local_tool = any(tool.name == tool_name for tool in self.mcp_manager.get_local_tools())
            
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
                    result = await self._execute_local_tool(tool_name, tool_args)
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
                    
                    # MCP 도구 실행
                    result = await self.mcp_manager.execute_tool(tool_name, tool_args)
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
    
    async def _execute_local_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """로컬 도구 실행"""
        try:
            # 로컬 도구 찾기
            tool_function = None
            for tool in self.mcp_manager.get_local_tools():
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
    
    def should_continue(self, state: RealtimeMCPAgentState) -> Literal["tool_executor", "response_formatter"]:
        """Tool 실행 여부 결정"""
        tool_calls = state.get("tool_calls", [])
        
        if tool_calls:
            print("🔧 Tool 실행이 필요합니다.")
            return "tool_executor"
        else:
            print("📝 최종 응답을 생성합니다.")
            return "response_formatter"
    
    def response_formatter(self, state: RealtimeMCPAgentState) -> RealtimeMCPAgentState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        # Tool 실행 결과가 있는 경우 추가 정보 포함
        tool_results = state.get("tool_results", [])
        mcp_tools_used = state.get("mcp_tools_used", [])
        local_tools_used = state.get("local_tools_used", [])
        
        if tool_results:
            formatted_response = f"🤖 실시간 MCP Agent 응답:\n{state['model_response']}\n\n"
            
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
            formatted_response = f"🤖 실시간 MCP Agent 응답:\n{state['model_response']}"
        
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
            builder = StateGraph(RealtimeMCPAgentState)
            
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
            
            print("✅ 실시간 MCP LangGraph Agent가 성공적으로 빌드되었습니다.")
            
        except Exception as e:
            print(f"❌ 그래프 빌드 중 오류 발생: {str(e)}")
            self.graph = None
    
    async def generate_response(self, query: str) -> str:
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
                "local_tools_used": [],
                "config_reloaded": False,
                "token_usage": {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    },
                    "by_model": {}
                }
            }
            
            # 그래프 실행
            result = await self.graph.ainvoke(initial_state)
            
            # 토큰 사용량 정보 추가 (선택적)
            response = result["model_response"]
            token_usage = result.get("token_usage", {})
            if token_usage and token_usage.get("total", {}).get("total_tokens", 0) > 0:
                tracker = TokenUsageTracker()
                summary = tracker.get_summary(token_usage)
                response += f"\n\n📊 {summary}"
            
            return response
            
        except Exception as e:
            return f"❌ 그래프 실행 중 오류 발생: {str(e)}"
    
    def generate_response_sync(self, query: str) -> str:
        """동기식 응답 생성 (비동기 래퍼)"""
        try:
            # 이벤트 루프가 실행 중인지 확인
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프에서는 task로 실행
                task = asyncio.create_task(self.generate_response(query))
                # 동기식으로 결과 대기 (실제로는 비추천)
                return asyncio.run_coroutine_threadsafe(self.generate_response(query), loop).result()
            else:
                # 새로운 루프에서 실행
                return asyncio.run(self.generate_response(query))
        except RuntimeError:
            # 루프가 없는 경우 새로 생성
            return asyncio.run(self.generate_response(query))
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스 - 실시간 MCP Tool calling 지원"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 실시간 MCP LangGraph Agent 대화 시작")
        print("=" * 60)
        print("💡 '/help' 입력시 도구 설명을 볼 수 있습니다.")
        print("💡 '/mcp' 입력시 MCP 상태를 볼 수 있습니다.")
        print("💡 '/servers' 입력시 서버 상태를 볼 수 있습니다.")
        print("💡 '/reload' 입력시 수동으로 설정을 리로드합니다.")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("🔄 설정 파일 변경시 자동으로 리로드됩니다.")
        print("=" * 60)
        
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
                
                # /reload 명령어 처리
                if user_input.lower() == '/reload':
                    print("🔄 수동 리로드 중...")
                    asyncio.run(self._check_and_reload())
                    continue
                
                if not user_input:
                    print("❌ 질문을 입력해주세요.")
                    continue
                
                print(f"\n🔍 질문: {user_input}")
                print("🤖 답변:")
                print("-" * 30)
                
                # 응답 생성
                response = self.generate_response_sync(user_input)
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
        local_tools = self.mcp_manager.get_local_tools()
        print(f"\n🔧 로컬 도구 ({len(local_tools)}개):")
        for tool in local_tools:
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
        for tool in local_tools:
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
                self.graph is not None and
                self.mcp_manager.is_initialized)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "Realtime MCP LangGraph Agent",
                "model": "gpt-oss:120b-cloud",
                "architecture": "StateGraph 기반 + 실시간 MCP Tool calling",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        mcp_status = self.mcp_manager.get_status()
        
        return {
            "type": "Realtime MCP LangGraph Agent",
            "model": "gpt-oss:120b-cloud",
            "architecture": "StateGraph 기반 + 실시간 MCP Tool calling",
            "ready": self.is_ready(),
            "auto_reload": self.auto_reload,
            "reload_interval": self.reload_interval,
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> input_processor -> llm_call -> [tool_executor] -> response_formatter -> END",
            "state_schema": list(RealtimeMCPAgentState.__annotations__.keys()),
            "local_tools": [tool.name for tool in self.mcp_manager.get_local_tools()],
            "mcp_tools": [tool.name for tool in self.mcp_manager.get_mcp_tools()],
            "total_tools": len(self.tools),
            "mcp_status": mcp_status,
            "features": ["상태 관리", "노드 기반", "실시간 MCP Tool calling", "자동 리로드", "확장 가능", "비동기 지원", "디버깅 용이"]
        }
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self.mcp_manager.cleanup()
        print("🧹 실시간 MCP Agent 정리 완료")
