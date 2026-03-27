"""
LangGraph Agent Chaining - Prompt Chaining with Validation
다단계 개선 워크플로우 패턴 구현
"""

# 표준 라이브러리
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


# State 정의
class ChainingState(TypedDict):
    """Prompt Chaining의 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]  # 메시지 히스토리
    topic: str  # 주제
    joke: str  # 초기 joke
    improved_joke: str  # 개선된 joke
    final_joke: str  # 최종 joke
    llm_calls: int  # LLM 호출 횟수
    iteration_count: int  # 반복 횟수


class LangGraphAgentChaining(BaseAgent):
    """Prompt Chaining 패턴을 구현한 LangGraph Agent 클래스
    
    LangChain 문서의 Prompt Chaining 예시를 기반으로 구현:
    - generate_joke: 초기 joke 생성
    - check_punchline: Gate function으로 punchline 검증
    - improve_joke: 개선된 joke 생성
    - polish_joke: 최종 joke 완성
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
    
    def generate_joke(self, state: ChainingState) -> ChainingState:
        """첫 번째 LLM 호출: 초기 joke 생성"""
        print(f"🎭 초기 joke 생성 중: {state['topic']}")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 유머러스한 코미디언입니다. 재미있는 농담을 만들어주세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"{state['topic']}에 대한 짧은 농담을 써주세요."
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "joke": response.content,
                "llm_calls": state.get("llm_calls", 0) + 1,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 농담 생성 중 오류 발생: {str(e)}"
            return {
                "joke": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def check_punchline(self, state: ChainingState) -> Literal["Pass", "Fail"]:
        """Gate function: 농담에 punchline이 있는지 검증"""
        joke = state.get("joke", "")
        
        # 간단한 검증: "?" 또는 "!" 포함 여부 확인
        has_punchline = "?" in joke or "!" in joke
        
        if has_punchline:
            print("✅ Punchline 검증 통과")
            return "Pass"
        else:
            print("❌ Punchline 검증 실패 - 개선 필요")
            return "Fail"
    
    def improve_joke(self, state: ChainingState) -> ChainingState:
        """두 번째 LLM 호출: 농담 개선 (wordplay 추가)"""
        print("🔧 농담 개선 중...")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 농담을 더 재미있게 만들 수 있는 전문가입니다. 말장난이나 재치를 추가하세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"다음 농담을 더 재미있게 만들고 말장난을 추가해주세요:\n\n{state['joke']}"
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "improved_joke": response.content,
                "llm_calls": state.get("llm_calls", 0) + 1,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 농담 개선 중 오류 발생: {str(e)}"
            return {
                "improved_joke": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def polish_joke(self, state: ChainingState) -> ChainingState:
        """세 번째 LLM 호출: 최종 다듬기 (surprising twist 추가)"""
        print("✨ 농담 최종 완성 중...")
        
        # improved_joke 또는 joke 사용
        base_joke = state.get("improved_joke") or state.get("joke", "")
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 농담에 놀라운 반전을 추가할 수 있는 전문가입니다."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(
                content=f"다음 농담에 놀라운 반전을 추가해주세요:\n\n{base_joke}"
            )
            
            # LLM 호출
            response = self.model.invoke([system_message, human_message])
            
            # AI 메시지 추가
            ai_message = AIMessage(content=response.content)
            
            return {
                "messages": [ai_message],
                "final_joke": response.content,
                "llm_calls": state.get("llm_calls", 0) + 1,
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
        except Exception as e:
            error_msg = f"❌ 농담 완성 중 오류 발생: {str(e)}"
            return {
                "final_joke": error_msg,
                "llm_calls": state.get("llm_calls", 0) + 1
            }
    
    def build_graph(self):
        """LangGraph 빌드"""
        if not self.model:
            print("❌ 모델이 초기화되지 않아 그래프를 빌드할 수 없습니다.")
            return
        
        try:
            # StateGraph 생성
            track = StateGraph(ChainingState)
            
            # 노드 추가
            track.add_node("generate_joke", self.generate_joke)
            track.add_node("improve_joke", self.improve_joke)
            track.add_node("polish_joke", self.polish_joke)
            
            # 엣지 추가
            track.add_edge(START, "generate_joke")
            
            # 조건부 엣지 추가 (Gate function으로 라우팅)
            track.add_conditional_edges(
                "generate_joke",
                self.check_punchline,
                {
                    "Pass": END,  # 통과하면 바로 종료
                    "Fail": "improve_joke"  # 실패하면 개선
                }
            )
            
            track.add_edge("improve_joke", "polish_joke")
            track.add_edge("polish_joke", END)
            
            # 그래프 컴파일
            self.graph = track.compile()
            
            print("✅ LangGraph Chaining Agent가 성공적으로 빌드되었습니다.")
            
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
                "improved_joke": "",
                "final_joke": "",
                "llm_calls": 0,
                "iteration_count": 0
            }
            
            # 그래프 실행
            result = self.graph.invoke(initial_state)
            
            # 결과 포맷팅
            response = self._format_response(result)
            
            return response
            
        except Exception as e:
            return f"❌ 그래프 실행 중 오류 발생: {str(e)}"
    
    def _format_response(self, result: ChainingState) -> str:
        """응답 포맷팅"""
        topic = result.get("topic", "")
        joke = result.get("joke", "")
        improved_joke = result.get("improved_joke", "")
        final_joke = result.get("final_joke", "")
        llm_calls = result.get("llm_calls", 0)
        
        response = f"🎭 농담 생성 결과: {topic}\n"
        response += "=" * 50 + "\n\n"
        
        if joke:
            response += f"📝 초기 농담:\n{joke}\n\n"
        
        if improved_joke:
            response += f"🔧 개선된 농담:\n{improved_joke}\n\n"
        
        if final_joke:
            response += f"✨ 최종 농담:\n{final_joke}\n\n"
        
        # LLM 호출 횟수 표시
        response += f"📊 LLM 호출 횟수: {llm_calls}회\n"
        
        return response
    
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
                "improved_joke": "",
                "final_joke": "",
                "llm_calls": 0,
                "iteration_count": 0
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
        
        print(f"\n🎭 LangGraph Chaining Agent 시작")
        print("=" * 50)
        print("💡 농담 주제를 입력하세요 (예: 고양이, 프로그래머)")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("=" * 50)
        
        while True:
            try:
                # 사용자 입력 받기
                if query:
                    user_input = query
                    query = None  # 한 번만 사용
                else:
                    user_input = input("\n👤 농담 주제를 입력하세요: ").strip()
                
                # 종료 조건 확인
                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
                
                if not user_input:
                    print("❌ 주제를 입력해주세요.")
                    continue
                
                print(f"\n🎭 농담 생성 중: {user_input}")
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
                "type": "LangGraph Chaining Agent",
                "model": self.model_name,
                "architecture": "StateGraph 기반 + Prompt Chaining",
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "LangGraph Chaining Agent",
            "model": self.model_name,
            "architecture": "StateGraph 기반 + Prompt Chaining",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> generate_joke -> [Pass: END | Fail: improve_joke -> polish_joke -> END]",
            "state_schema": list(ChainingState.__annotations__.keys()),
            "features": [
                "상태 관리",
                "노드 기반",
                "Gate function 검증",
                "다단계 개선",
                "조건부 라우팅",
                "확장 가능",
                "디버깅 용이"
            ]
        }

