"""
기본 LangChain Agent 모듈
"""

# 표준 라이브러리
import os
from datetime import datetime

# 서드파티
from langchain.messages import HumanMessage, SystemMessage

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


class BasicAgent(BaseAgent):
    """기본 LangChain Agent 클래스"""
    
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
        
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        if not self.model:
            return "❌ 모델이 초기화되지 않았습니다. OLLAMA_API_KEY를 확인하세요."
        
        try:
            # 시스템 메시지 설정
            system_message = SystemMessage(
                content="당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공하세요."
            )
            
            # 사용자 메시지 생성
            human_message = HumanMessage(content=query)
            
            # 메시지 리스트 구성
            messages = [system_message, human_message]
            
            # 모델 호출
            response = self.model.invoke(messages)
            
            return response.content
            
        except Exception as e:
            return f"❌ 응답 생성 중 오류 발생: {str(e)}"
    
    def stream(self, query: str):
        """스트리밍 응답 생성 (BasicAgent는 stream 미지원)"""
        # BasicAgent는 Graph 기반이 아니므로 일반 호출
        response = self.generate_response(query)
        yield {"response": response}
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return self.model is not None
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 Basic Agent 대화 시작")
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
        return {
            "type": "Basic LangChain Agent",
            "model": self.model_name,
            "architecture": "단순 클래스 기반",
            "ready": self.is_ready(),
            "features": ["기본 질문-답변", "간단한 구조", "빠른 응답"]
        }
