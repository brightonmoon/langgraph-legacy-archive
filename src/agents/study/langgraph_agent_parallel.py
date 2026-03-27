"""
LangGraph Agent Parallel - Parallelization Pattern
병렬 처리 워크플로우 패턴 구현
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
class ParallelState(TypedDict):
    """Parallelization의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    topic: str  # 주제
    joke: str  # 농담
    story: str  # 이야기
    poem: str  # 시
    combined_output: str  # 통합된 출력
    llm_calls: int  # LLM 호출 횟수


class LangGraphAgentParallel(BaseAgent):
    """Parallelization 패턴을 구현한 LangGraph Agent 클래스
    
    LangChain 문서의 Parallelization 예시를 기반으로 구현:
    - call_llm_1: 농담 생성
    - call_llm_2: 이야기 생성
    - call_llm_3: 시 생성
    - aggregator: 결과 통합
    """
    
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
    
    def call_llm_1(self, state: ParallelState) -> ParallelState:
        """첫 번째 LLM 호출: 농담 생성"""
        print(f"🎭 농담 생성 중: {state['topic']}")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 유머러스한 코미디언입니다. 재미있는 농담을 만들어주세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"{state['topic']}에 대한 짧고 재미있는 농담을 써주세요."
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "joke": response.content
            }
            
        except Exception as e:
            error_msg = f"❌ 농담 생성 중 오류 발생: {str(e)}"
            return {
                "joke": error_msg
            }
    
    def call_llm_2(self, state: ParallelState) -> ParallelState:
        """두 번째 LLM 호출: 이야기 생성"""
        print(f"📖 이야기 생성 중: {state['topic']}")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 창의적인 이야기 작가입니다. 흥미로운 이야기를 만들어주세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"{state['topic']}에 대한 짧은 이야기를 써주세요. (3-5문장)"
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "story": response.content
            }
            
        except Exception as e:
            error_msg = f"❌ 이야기 생성 중 오류 발생: {str(e)}"
            return {
                "story": error_msg
            }
    
    def call_llm_3(self, state: ParallelState) -> ParallelState:
        """세 번째 LLM 호출: 시 생성"""
        print(f"📝 시 생성 중: {state['topic']}")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 감성적인 시인입니다. 아름다운 시를 써주세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"{state['topic']}에 대한 짧은 시를 써주세요. (2-3연)"
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "poem": response.content
            }
            
        except Exception as e:
            error_msg = f"❌ 시 생성 중 오류 발생: {str(e)}"
            return {
                "poem": error_msg
            }
    
    def aggregator(self, state: ParallelState) -> ParallelState:
        """결과 통합 노드"""
        print("📦 결과 통합 중...")
        
        topic = state.get("topic", "")
        joke = state.get("joke", "")
        story = state.get("story", "")
        poem = state.get("poem", "")
        
        # LLM 호출 횟수 계산 (3개 노드 실행)
        llm_calls = 3
        
        # 결과 통합
        combined = f"{topic}에 대한 창의적인 콘텐츠\n"
        combined += "=" * 50 + "\n\n"
        
        if joke:
            combined += f"🎭 농담:\n{joke}\n\n"
        
        if story:
            combined += f"📖 이야기:\n{story}\n\n"
        
        if poem:
            combined += f"📝 시:\n{poem}\n\n"
        
        combined += f"📊 총 LLM 호출 횟수: {llm_calls}회\n"
        
        return {
            "combined_output": combined,
            "llm_calls": llm_calls
        }
    
    def build_graph(self):
        """LangGraph 빌드 - 병렬 처리 구조"""
        if not self.model:
            print("❌ 모델이 초기화되지 않아 그래프를 빌드할 수 없습니다.")
            return
        
        try:
            # StateGraph 생성
            parallel_builder = StateGraph(ParallelState)
            
            # 노드 추가
            parallel_builder.add_node("call_llm_1", self.call_llm_1)
            parallel_builder.add_node("call_llm_2", self.call_llm_2)
            parallel_builder.add_node("call_llm_3", self.call_llm_3)
            parallel_builder.add_node("aggregator", self.aggregator)
            
            # 병렬 실행 구조: START에서 세 노드로 동시 분기
            parallel_builder.add_edge(START, "call_llm_1")
            parallel_builder.add_edge(START, "call_llm_2")
            parallel_builder.add_edge(START, "call_llm_3")
            
            # Aggregator로 통합
            parallel_builder.add_edge("call_llm_1", "aggregator")
            parallel_builder.add_edge("call_llm_2", "aggregator")
            parallel_builder.add_edge("call_llm_3", "aggregator")
            
            # Aggregator 후 종료
            parallel_builder.add_edge("aggregator", END)
            
            # 그래프 컴파일
            self.graph = parallel_builder.compile()
            
            print("✅ LangGraph Parallel Agent가 성공적으로 빌드되었습니다.")
            
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
                "topic": query,
                "joke": "",
                "story": "",
                "poem": "",
                "combined_output": "",
                "llm_calls": 0
            }
            
            # 그래프 실행
            result = self.graph.invoke(initial_state)
            
            return result.get("combined_output", "결과 없음")
            
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
                "topic": query,
                "joke": "",
                "story": "",
                "poem": "",
                "combined_output": "",
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
        
        print(f"\n🚀 LangGraph Parallel Agent 시작")
        print("=" * 50)
        print("💡 주제를 입력하세요 (예: 고양이, 봄, 코딩)")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("=" * 50)
        
        while True:
            try:
                # 사용자 입력 받기
                if query:
                    user_input = query
                    query = None  # 한 번만 사용
                else:
                    user_input = input("\n👤 주제를 입력하세요: ").strip()
                
                # 종료 조건 확인
                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
                
                if not user_input:
                    print("❌ 주제를 입력해주세요.")
                    continue
                
                print(f"\n🚀 콘텐츠 생성 중: {user_input}")
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
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "LangGraph Parallel Agent",
                "model": self.model_name,
                "architecture": "StateGraph 기반 + Parallelization",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "LangGraph Parallel Agent",
            "model": self.model_name,
            "architecture": "StateGraph 기반 + Parallelization",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> [call_llm_1, call_llm_2, call_llm_3] -> aggregator -> END",
            "state_schema": list(ParallelState.__annotations__.keys()),
            "features": [
                "상태 관리",
                "노드 기반",
                "병렬 처리",
                "결과 통합",
                "성능 향상",
                "확장 가능",
                "디버깅 용이"
            ]
        }

