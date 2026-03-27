"""
Base Middleware 클래스

모든 Middleware의 기본 클래스로 공통 기능을 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseMiddleware(ABC):
    """모든 Middleware의 기본 인터페이스"""
    
    def __init__(self, name: str = None):
        """
        Middleware 초기화
        
        Args:
            name: Middleware 이름
        """
        self.name = name or self.__class__.__name__
        self.created_at = datetime.now()
    
    @abstractmethod
    def process(self, state: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        상태를 처리하고 필요시 수정된 상태를 반환
        
        Args:
            state: 현재 Agent 상태
            **kwargs: 추가 파라미터
            
        Returns:
            수정된 상태 또는 None (수정 없음)
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Middleware 정보 반환"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "created_at": self.created_at.isoformat()
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

