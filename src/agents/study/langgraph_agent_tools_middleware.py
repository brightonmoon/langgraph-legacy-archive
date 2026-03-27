"""
LangGraph Agent Tools with Middleware - Middleware를 통합한 LangGraph Agent
"""

# 표준 라이브러리
import asyncio
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal, AsyncIterator, Dict, Any

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.agents.middleware import LoggingMiddleware, RateLimitingMiddleware
from src.tools.factory import ToolFactory
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.token_usage_tracker import TokenUsageTracker


# State 정의
class AgentToolsMiddlewareState(TypedDict, total=False):
    """Agent Tools Middleware의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    user_query: str  # 사용자 쿼리
    model_response: str  # 모델 응답
    tool_calls: list  # Tool 호출 목록
    tool_results: list  # Tool 실행 결과
    llm_calls: int  # LLM 호출 횟수
    tool_calls_count: int  # Tool 호출 횟수
    iteration_count: int  # Agent 반복 횟수 (무한 루프 방지)
    token_usage: Dict[str, Any]  # 토큰 사용량 정보


class LangGraphAgentToolsMiddleware(BaseAgent):
    """Middleware를 통합한 LangGraph Agent Tools 클래스"""
    
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
        self.tools = ToolFactory.get_all_tools()
        self.model_with_tools = None
        self.graph = None
        
        # Middleware 초기화
        self.logging_middleware = LoggingMiddleware(verbose=True)
        self.rate_limiting_middleware = RateLimitingMiddleware(
            max_calls_per_minute=60,
            max_calls_per_hour=1000
        )
        self.middleware_list = [
            self.logging_middleware,
            self.rate_limiting_middleware
        ]
        
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
    
    def input_processor(self, state: AgentToolsMiddlewareState) -> AgentToolsMiddlewareState:
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
            "iteration_count": 0,
            "token_usage": token_usage
        }
    
    def llm_call(self, state: AgentToolsMiddlewareState) -> AgentToolsMiddlewareState:
        """LLM 호출 노드 (Tool calling 지원 + Middleware)"""
        if not self.model_with_tools:
            return {
                "model_response": "❌ Tool이 바인딩된 모델이 초기화되지 않았습니다.",
                "llm_calls": state.get("llm_calls", 0) + 1,
                "token_usage": state.get("token_usage", {})
            }
        
        # Middleware: 로깅 시작 및 Rate limiting 확인
        for middleware in self.middleware_list:
            middleware.process(state, start_time=None)
        
        try:
            print("🤖 LLM 호출 중...")
            
            # TokenUsageTracker 생성 및 callback 가져오기
            tracker = TokenUsageTracker()
            callback = tracker.get_callback()
            
            # 시스템 메시지 설정 (동적 도구 설명 사용)
            iteration_count = state.get("iteration_count", 0)
            local_tools_desc = ToolFactory.get_tools_description()
            
            system_message = SystemMessage(
                content=f"""당신은 도움이 되는 AI 어시스턴트입니다. 
사용자의 질문에 정확하고 유용한 답변을 제공하세요.

사용 가능한 도구들:
{local_tools_desc}

⚠️ 중요 지침:
1. 도구 호출은 최대 5회까지만 허용됩니다 (현재 반복 횟수: {iteration_count}/5)
2. 동일한 검색 쿼리를 반복하지 마세요
3. 도구 실행 결과를 충분히 활용하여 최종 답변을 생성하세요
4. 검색 결과가 부족하거나 관련이 없다면, 가지고 있는 정보로 최선의 답변을 제공하세요
5. 계속해서 도구를 호출하지 말고, 적절한 시점에 최종 답변을 제공하세요

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
            
            result = {
                "messages": [ai_message],
                "model_response": response.content,
                "tool_calls": response.tool_calls or [],
                "llm_calls": state.get("llm_calls", 0) + 1,
                "iteration_count": state.get("iteration_count", 0) + 1,
                "token_usage": updated_token_usage
            }
            
            # Middleware: 도구 호출 로깅
            if result.get("tool_calls"):
                for middleware in self.middleware_list:
                    middleware.process(result)
            
            return result
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            
            # Middleware: 에러 로깅
            for middleware in self.middleware_list:
                middleware.process({"model_response": error_msg})
            
            return {
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1,
                "token_usage": state.get("token_usage", {})
            }
    
    def tool_executor(self, state: AgentToolsMiddlewareState) -> AgentToolsMiddlewareState:
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
    
    def should_continue(self, state: AgentToolsMiddlewareState) -> Literal["tool_executor", "response_formatter"]:
        """Tool 실행 여부 결정"""
        tool_calls = state.get("tool_calls", [])
        iteration_count = state.get("iteration_count", 0)
        
        # 무한 루프 방지: 최대 5회 반복 제한 (10회에서 5회로 축소)
        if iteration_count >= 5:
            print(f"⚠️ 최대 반복 횟수(5회) 도달. 응답 생성합니다.")
            return "response_formatter"
        
        if tool_calls:
            print("🔧 Tool 실행이 필요합니다.")
            return "tool_executor"
        else:
            print("📝 최종 응답을 생성합니다.")
            return "response_formatter"
    
    def response_formatter(self, state: AgentToolsMiddlewareState) -> AgentToolsMiddlewareState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        # Middleware: 로깅 완료
        for middleware in self.middleware_list:
            middleware.process(state, start_time=True)
        
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
            builder = StateGraph(AgentToolsMiddlewareState)
            
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
            
            print("✅ LangGraph Agent Tools Middleware가 성공적으로 빌드되었습니다.")
            
        except Exception as e:
            print(f"❌ 그래프 빌드 중 오류 발생: {str(e)}")
            self.graph = None
    
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        if not self.graph:
            return "❌ 그래프가 초기화되지 않았습니다."
        
        try:
            # 새로운 요청 시작 시 로깅 미들웨어의 시작 시간 리셋
            self.logging_middleware.reset_start_time()
            
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
            
            # 그래프 실행
            result = self.graph.invoke(initial_state)
            
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
    
    def stream(self, query: str):
        """스트리밍 응답 생성"""
        if not self.graph:
            yield {"error": "❌ 그래프가 초기화되지 않았습니다."}
            return
        
        try:
            # 새로운 요청 시작 시 로깅 미들웨어의 시작 시간 리셋
            self.logging_middleware.reset_start_time()
            
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_query": query,
                "model_response": "",
                "tool_calls": [],
                "tool_results": [],
                "llm_calls": 0,
                "tool_calls_count": 0,
                "iteration_count": 0
            }
            
            # 그래프 스트리밍 실행
            for chunk in self.graph.stream(initial_state):
                yield chunk
                
        except Exception as e:
            yield {"error": f"❌ 그래프 실행 중 오류 발생: {str(e)}"}
    
    async def stream_chat(self, query: str):
        """LLM 토큰 단위 스트리밍으로 대화 실행"""
        if not self.graph:
            print("❌ 그래프가 초기화되지 않았습니다.")
            return
        
        try:
            # 새로운 요청 시작 시 로깅 미들웨어의 시작 시간 리셋
            self.logging_middleware.reset_start_time()
            
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_query": query,
                "model_response": "",
                "tool_calls": [],
                "tool_results": [],
                "llm_calls": 0,
                "tool_calls_count": 0,
                "iteration_count": 0,
                "token_usage": {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    },
                    "by_model": {}
                }
            }
            
            # LLM 응답 누적 변수
            accumulated_response = ""
            
            # astream_events를 사용하여 LLM 토큰 스트리밍
            async for event in self.graph.astream_events(initial_state, version="v2"):
                kind = event.get("event")
                
                # LLM 토큰이 생성될 때마다 출력
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", {})
                    if isinstance(chunk, AIMessage):
                        content = chunk.content
                        if content:
                            print(content, end="", flush=True)
                            accumulated_response += content
                
                # 노드 시작 이벤트 출력
                elif kind == "on_chain_start":
                    name = event.get("name", "")
                    if name == "llm_call":
                        print("🤖 LLM 호출 중...\n", end="", flush=True)
                    elif name == "tool_executor":
                        print("\n🔧 Tool 실행 중...\n", end="", flush=True)
                
                # 최종 응답 추출
                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    if name == "response_formatter":
                        output = event.get("data", {}).get("output", {})
                        if isinstance(output, dict) and "model_response" in output:
                            # 이미 출력된 내용이므로 추가 출력 불필요
                            pass
            
            # 응답이 없으면 fallback
            if not accumulated_response:
                print("\n📝 Fallback: generate_response() 사용")
                response = self.generate_response(query)
                print(response)
            else:
                print()  # 줄바꿈
                
        except Exception as e:
            print(f"\n❌ 스트리밍 중 오류 발생: {str(e)}")
    
    def chat(self, query: str = None, stream: bool = False) -> None:
        """
        대화형 인터페이스 - Tool calling + Middleware 지원
        
        Args:
            query: 초기 쿼리 (대화형 모드에서는 무시됨)
            stream: True이면 토큰 단위 스트리밍, False이면 전체 응답 반환 (기본값: False)
                   - stream=True: 사용자 인터페이스에 적합, 실시간 토큰 출력
                   - stream=False: 자동화/테스트에 적합, 전체 응답 반환
        """
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 LangGraph Agent Tools (Middleware) 대화 시작")
        print("=" * 50)
        print("💡 '/help' 입력시 도구 설명을 볼 수 있습니다.")
        print("💡 '/stats' 입력시 Middleware 통계를 볼 수 있습니다.")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        if stream:
            print("💡 스트리밍 모드: 토큰 단위로 실시간 출력됩니다.")
        else:
            print("💡 일반 모드: 전체 응답이 생성된 후 출력됩니다.")
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
                
                # /stats 명령어 처리
                if user_input.lower() == '/stats':
                    self.show_stats()
                    continue
                
                if not user_input:
                    print("❌ 질문을 입력해주세요.")
                    continue
                
                print(f"\n🔍 질문: {user_input}")
                print("🤖 답변:")
                print("-" * 20)
                
                # 스트리밍 모드에 따라 다른 방식 사용
                try:
                    if stream:
                        # 토큰 단위 스트리밍 (사용자 인터페이스용)
                        asyncio.run(self.stream_chat(user_input))
                    else:
                        # 전체 응답 반환 (테스트/자동화용)
                        response = self.generate_response(user_input)
                        print(response)
                    
                    print("-" * 20)
                except Exception as e:
                    print(f"❌ 응답 생성 중 오류 발생: {str(e)}")
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
        print("=" * 50)
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
        print("=" * 50)
    
    def show_stats(self) -> None:
        """Middleware 통계 표시"""
        stats = self.get_middleware_stats()
        
        print(f"\n📊 Middleware 통계:")
        print("=" * 50)
        
        # Logging 통계
        logging_stats = stats['logging']
        print(f"\n🔹 Logging Middleware:")
        print(f"   총 호출: {logging_stats['total_calls']}")
        print(f"   도구 호출: {logging_stats['tool_calls']}")
        print(f"   에러 수: {logging_stats['errors']}")
        print(f"   평균 시간: {logging_stats['average_time']:.2f}초")
        
        # Rate Limiting 통계
        rate_stats = stats['rate_limiting']
        print(f"\n🔹 Rate Limiting Middleware:")
        print(f"   최근 1분간 호출: {rate_stats['calls_in_last_minute']}")
        print(f"   최근 1시간 호출: {rate_stats['calls_in_last_hour']}")
        print(f"   분당 제한: {rate_stats['max_per_minute']}")
        print(f"   시간당 제한: {rate_stats['max_per_hour']}")
        
        print("=" * 50)
    
    def get_middleware_stats(self):
        """Middleware 통계 반환"""
        return {
            "logging": self.logging_middleware.get_stats(),
            "rate_limiting": self.rate_limiting_middleware.get_stats()
        }
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return (self.model is not None and 
                self.model_with_tools is not None and 
                self.graph is not None)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "LangGraph Agent Tools Middleware",
                "model": self.model_name,
                "architecture": "StateGraph 기반 + Tool calling + Middleware",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "LangGraph Agent Tools Middleware",
            "model": self.model_name,
            "architecture": "StateGraph 기반 + Tool calling + Middleware",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> input_processor -> llm_call -> [tool_executor] -> response_formatter -> END",
            "state_schema": list(AgentToolsMiddlewareState.__annotations__.keys()),
            "tools": [tool.name for tool in self.tools],
            "tool_count": len(self.tools),
            "middleware": ["LoggingMiddleware", "RateLimitingMiddleware"],
            "features": ["상태 관리", "노드 기반", "Tool calling", "Middleware", "로깅", "Rate limiting", "확장 가능", "디버깅 용이"]
        }


# ============================================
# LangGraph dev 환경용 export 함수
# ============================================

def create_langgraph_agent_tools_middleware_graph(
    model_name: str = None
):
    """LangGraph dev 환경에서 사용할 LangGraphAgentToolsMiddleware 그래프 생성
    
    Args:
        model_name: 사용할 모델명 (None이면 환경변수에서 자동 결정)
        
    Returns:
        LangGraph CompiledStateGraph
    """
    agent = LangGraphAgentToolsMiddleware(model_name=model_name)
    return agent.graph


def _get_default_langgraph_agent_tools_middleware():
    """기본 LangGraphAgentToolsMiddleware 그래프 생성 (lazy initialization)
    
    환경변수에서 자동으로 설정을 읽어옵니다.
    """
    return create_langgraph_agent_tools_middleware_graph()


# LangGraph dev에서 참조할 agent 변수
agent = _get_default_langgraph_agent_tools_middleware()

