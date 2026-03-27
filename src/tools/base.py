"""
Base Tool 클래스 - 모든 Tool의 기본 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from langchain.tools import BaseTool as LangChainBaseTool


class BaseTool(ABC):
    """모든 Tool의 기본 인터페이스"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Tool 이름 반환"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Tool 설명 반환"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Tool 실행"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Tool 정보 반환"""
        return {
            "name": self.get_name(),
            "description": self.get_description(),
            "type": self.__class__.__name__
        }
    
    def to_langchain_tool(self) -> LangChainBaseTool:
        """LangChain BaseTool로 변환"""
        from langchain.tools import tool
        
        def tool_func(**kwargs) -> str:
            """Tool 실행 함수"""
            return self.execute(**kwargs)
        
        # Tool 메타데이터 설정
        tool_func.__name__ = self.get_name()
        tool_func.__doc__ = self.get_description()
        
        # @tool 데코레이터 적용
        langchain_tool = tool(tool_func)
        langchain_tool.name = self.get_name()
        langchain_tool.description = self.get_description()
        
        return langchain_tool
