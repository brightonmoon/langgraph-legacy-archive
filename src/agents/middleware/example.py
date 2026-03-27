"""
Middleware 사용 예시

이 파일은 Middleware를 Agent에 통합하는 방법을 보여줍니다.
"""

from typing import TypedDict, Annotated
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from .logging import LoggingMiddleware
from .model_selection import ModelSelectionMiddleware
from .rate_limiting import RateLimitingMiddleware
from .decorators import apply_middleware


# State 정의
class AgentWithMiddlewareState(TypedDict):
    """Middleware를 사용하는 Agent의 상태"""
    messages: Annotated[list, add_messages]
    user_query: str
    model_response: str
    llm_calls: int


class AgentWithMiddleware:
    """Middleware를 사용하는 Agent 예시"""
    
    def __init__(self, model, tools=None):
        """Agent 초기화"""
        self.model = model
        self.tools = tools or []
        
        # Middleware 설정
        self.logging_middleware = LoggingMiddleware(verbose=True)
        self.rate_limiting_middleware = RateLimitingMiddleware(
            max_calls_per_minute=60,
            max_calls_per_hour=1000
        )
        
        # Middleware 리스트
        self.middleware_list = [
            self.logging_middleware,
            self.rate_limiting_middleware
        ]
        
        self.graph = None
        self.build_graph()
    
    def input_processor(self, state: AgentWithMiddlewareState) -> AgentWithMiddlewareState:
        """입력 처리 노드"""
        # Middleware 적용
        for middleware in self.middleware_list:
            middleware.process(state, start_time=None)
        
        user_message = HumanMessage(content=state['user_query'])
        
        return {
            "messages": [user_message],
            "llm_calls": state.get("llm_calls", 0)
        }
    
    def llm_call(self, state: AgentWithMiddlewareState) -> AgentWithMiddlewareState:
        """LLM 호출 노드"""
        try:
            system_message = SystemMessage(
                content="당신은 도움이 되는 AI 어시스턴트입니다."
            )
            
            messages = [system_message] + state["messages"]
            response = self.model.invoke(messages)
            
            ai_message = AIMessage(content=response.content)
            
            result = {
                "messages": [ai_message],
                "model_response": response.content,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
            
            # Middleware 처리 (완료 후)
            for middleware in self.middleware_list:
                middleware.process(result, start_time=True)
            
            return result
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            return {
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def build_graph(self):
        """LangGraph 빌드"""
        builder = StateGraph(AgentWithMiddlewareState)
        
        builder.add_node("input_processor", self.input_processor)
        builder.add_node("llm_call", self.llm_call)
        
        builder.add_edge(START, "input_processor")
        builder.add_edge("input_processor", "llm_call")
        builder.add_edge("llm_call", END)
        
        self.graph = builder.compile()
    
    def invoke(self, query: str):
        """쿼리 실행"""
        initial_state = {
            "messages": [],
            "user_query": query,
            "model_response": "",
            "llm_calls": 0
        }
        
        result = self.graph.invoke(initial_state)
        return result["model_response"]
    
    def get_middleware_stats(self):
        """Middleware 통계 반환"""
        return {
            "logging": self.logging_middleware.get_stats(),
            "rate_limiting": self.rate_limiting_middleware.get_stats()
        }


# 사용 예시
if __name__ == "__main__":
    # Middleware를 사용하는 Agent 생성
    import os
    from src.utils.config import init_chat_model_helper
    
    model_str = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
    if not model_str.startswith("ollama:"):
        model_str = f"ollama:{model_str}"
    
    model = init_chat_model_helper(
        model_name=model_str,
        api_key=os.getenv("OLLAMA_API_KEY"),
        temperature=0.7
    )
    agent = AgentWithMiddleware(model)
    
    # 쿼리 실행
    response = agent.invoke("안녕하세요!")
    print(response)
    
    # Middleware 통계 확인
    stats = agent.get_middleware_stats()
    print("\n=== Middleware 통계 ===")
    print(f"로깅: {stats['logging']}")
    print(f"Rate Limiting: {stats['rate_limiting']}")

