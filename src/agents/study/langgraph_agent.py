"""
LangGraph Agent 모듈
"""

# 표준 라이브러리
import os
from datetime import datetime
from typing import TypedDict, Annotated

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


# State 정의
class AgentState(TypedDict):
    """Agent의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    user_query: str  # 사용자 쿼리
    model_response: str  # 모델 응답
    llm_calls: int  # LLM 호출 횟수


class LangGraphAgent(BaseAgent):
    """LangGraph를 사용한 Basic Agent 클래스"""
    
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
        self.graph = None
        self.build_graph()
    
    def input_processor(self, state: AgentState) -> AgentState:
        """입력 처리 노드"""
        print(f"🔍 입력 처리 중: {state['user_query']}")
        
        # 사용자 메시지를 메시지 히스토리에 추가
        user_message = HumanMessage(content=state['user_query'])
        
        return {
            "messages": [user_message],
            "llm_calls": state.get("llm_calls", 0)
        }
    
    def llm_call(self, state: AgentState) -> AgentState:
        """LLM 호출 노드"""
        if not self.model:
            return {
                "model_response": "❌ 모델이 초기화되지 않았습니다.",
                "llm_calls": state.get("llm_calls", 0) + 1
            }
        
        try:
            print("🤖 LLM 호출 중...")
            
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공하세요."
            )
            
            # 메시지 리스트 구성 (시스템 메시지 + 기존 메시지들)
            messages = [system_message] + state["messages"]
            
            # 모델 호출
            response = self.model.invoke(messages)
            
            # AI 메시지를 메시지 히스토리에 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "model_response": response.content,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 응답 생성 중 오류 발생: {str(e)}"
            return {
                "model_response": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def response_formatter(self, state: AgentState) -> AgentState:
        """응답 포맷팅 노드"""
        print("📝 응답 포맷팅 중...")
        
        # 응답을 포맷팅하여 반환
        formatted_response = f"🤖 Agent 응답:\n{state['model_response']}"
        
        return {
            "model_response": formatted_response
        }
    
    def build_graph(self):
        """LangGraph 빌드"""
        if not self.model:
            print("❌ 모델이 초기화되지 않아 그래프를 빌드할 수 없습니다.")
            return
        
        try:
            # StateGraph 생성
            builder = StateGraph(AgentState)
            
            # 노드 추가
            builder.add_node("input_processor", self.input_processor)
            builder.add_node("llm_call", self.llm_call)
            builder.add_node("response_formatter", self.response_formatter)
            
            # 엣지 추가 (선형 플로우)
            builder.add_edge(START, "input_processor")
            builder.add_edge("input_processor", "llm_call")
            builder.add_edge("llm_call", "response_formatter")
            builder.add_edge("response_formatter", END)
            
            # 그래프 컴파일
            self.graph = builder.compile()
            
            print("✅ LangGraph가 성공적으로 빌드되었습니다.")
            
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
                "llm_calls": 0
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
                "llm_calls": 0
            }
            
            # 그래프 스트리밍 실행
            for chunk in self.graph.stream(initial_state):
                yield chunk
                
        except Exception as e:
            yield {"error": f"❌ 그래프 실행 중 오류 발생: {str(e)}"}
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return self.model is not None and self.graph is not None
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 LangGraph Agent 대화 시작")
        print("=" * 40)
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
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "LangGraph Agent",
                "model": self.model_name,
                "architecture": "StateGraph 기반",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "LangGraph Agent",
            "model": self.model_name,
            "architecture": "StateGraph 기반",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> input_processor -> llm_call -> response_formatter -> END",
            "state_schema": list(AgentState.__annotations__.keys()),
            "features": ["상태 관리", "노드 기반", "확장 가능", "디버깅 용이"]
        }
