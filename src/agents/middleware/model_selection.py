"""
Model Selection Middleware

질문의 복잡도에 따라 동적으로 모델을 선택합니다.
"""

from typing import Dict, Any, Optional
from .base import BaseMiddleware


class ModelSelectionMiddleware(BaseMiddleware):
    """동적 모델 선택을 위한 Middleware"""
    
    def __init__(
        self, 
        name: str = "ModelSelectionMiddleware",
        simple_model: Any = None,
        complex_model: Any = None,
        complexity_threshold: int = 50
    ):
        """
        Model Selection Middleware 초기화
        
        Args:
            name: Middleware 이름
            simple_model: 단순 질문용 모델
            complex_model: 복잡한 질문용 모델
            complexity_threshold: 복잡도 임계값 (문자 수 기준)
        """
        super().__init__(name)
        self.simple_model = simple_model
        self.complex_model = complex_model
        self.complexity_threshold = complexity_threshold
    
    def process(self, state: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        질문 복잡도를 분석하고 적절한 모델 선택
        
        Args:
            state: 현재 Agent 상태
            **kwargs: 추가 파라미터
            
        Returns:
            선택된 모델 정보가 포함된 상태 또는 None
        """
        user_query = state.get("user_query", "")
        
        if not user_query:
            return None
        
        # 복잡도 분석
        complexity = self._analyze_complexity(user_query)
        
        # 모델 선택
        selected_model = self._select_model(complexity)
        
        if selected_model:
            print(f"[{self.name}] 질문 복잡도: {complexity}")
            print(f"[{self.name}] 선택된 모델: {selected_model.__class__.__name__}")
            
            return {
                "selected_model": selected_model,
                "complexity": complexity
            }
        
        return None
    
    def _analyze_complexity(self, query: str) -> str:
        """
        질문의 복잡도를 분석
        
        Args:
            query: 사용자 질문
            
        Returns:
            "simple" 또는 "complex"
        """
        # 간단한 복잡도 판정: 길이 기반
        query_length = len(query)
        
        # 복잡한 표현이 있는지 확인
        complex_indicators = [
            "분석", "비교", "설명", "평가", "계획", "전략",
            "예측", "최적화", "통합", "설계", "구현"
        ]
        
        has_complex_indicators = any(indicator in query for indicator in complex_indicators)
        
        if query_length > self.complexity_threshold or has_complex_indicators:
            return "complex"
        
        return "simple"
    
    def _select_model(self, complexity: str):
        """
        복잡도에 따라 모델 선택
        
        Args:
            complexity: "simple" 또는 "complex"
            
        Returns:
            선택된 모델 또는 None
        """
        if complexity == "complex" and self.complex_model:
            return self.complex_model
        elif complexity == "simple" and self.simple_model:
            return self.simple_model
        
        return None
    
    def configure_models(self, simple_model: Any, complex_model: Any):
        """
        모델 설정 업데이트
        
        Args:
            simple_model: 단순 질문용 모델
            complex_model: 복잡한 질문용 모델
        """
        self.simple_model = simple_model
        self.complex_model = complex_model

