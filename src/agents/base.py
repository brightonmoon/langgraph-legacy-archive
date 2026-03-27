"""
Agent 모듈 - 기본 Agent와 LangGraph Agent의 공통 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


class BaseAgent(ABC):
    """모든 Agent의 기본 인터페이스"""
    
    def __init__(self, checkpointer: Optional["BaseCheckpointSaver"] = None):
        """
        Agent 초기화
        
        Args:
            checkpointer: 상태 지속성을 위한 Checkpointer (선택사항)
        """
        self.checkpointer = checkpointer
    
    @abstractmethod
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Agent 정보 반환"""
        pass
    
    def stream(self, query: str) -> Iterator[Dict[str, Any]]:
        """
        스트리밍 응답 생성

        기본 구현은 generate_response()를 호출하여 전체 응답을 한번에 반환합니다.
        진정한 스트리밍이 필요한 서브클래스는 이 메서드를 오버라이드하세요.

        Args:
            query: 사용자 쿼리

        Yields:
            각 노드 실행 후의 상태 딕셔너리
        """
        # 기본 구현: generate_response를 호출하고 결과를 yield (non-streaming fallback)
        # 서브클래스에서 LangGraph의 stream() 메서드를 사용하여 진정한 스트리밍 구현 가능
        response = self.generate_response(query)
        yield {"response": response, "done": True}
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스"""
        print(f"\n🤖 Agent 응답:")
        print("-" * 30)
        
        if query:
            response = self.generate_response(query)
            print(response)
        else:
            print("❌ 쿼리가 제공되지 않았습니다.")
        
        print("-" * 30)
