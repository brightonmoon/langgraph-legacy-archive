"""
LLM 토큰 사용량 추적 유틸리티 모듈

LangChain의 UsageMetadataCallbackHandler를 사용하여 토큰 사용량을 추적하고,
State에 저장하기 위한 유틸리티 클래스를 제공합니다.
"""

from typing import Dict, Any, Optional
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain.messages import AIMessage


class TokenUsageTracker:
    """LLM 토큰 사용량 추적 유틸리티 클래스"""
    
    def __init__(self):
        """TokenUsageTracker 초기화"""
        self.usage_metadata_callback = UsageMetadataCallbackHandler()
    
    def get_callback(self) -> UsageMetadataCallbackHandler:
        """Callback 반환 (모델 호출 시 사용)
        
        Returns:
            UsageMetadataCallbackHandler: 토큰 사용량 추적을 위한 콜백 핸들러
        """
        return self.usage_metadata_callback
    
    def extract_from_message(self, message: AIMessage) -> Optional[Dict[str, Any]]:
        """AIMessage에서 토큰 정보 추출
        
        Args:
            message: AIMessage 객체
            
        Returns:
            토큰 사용량 정보 딕셔너리 또는 None
        """
        if hasattr(message, 'usage_metadata') and message.usage_metadata:
            return {
                'input_tokens': message.usage_metadata.get('input_tokens', 0),
                'output_tokens': message.usage_metadata.get('output_tokens', 0),
                'total_tokens': message.usage_metadata.get('total_tokens', 0),
                'input_token_details': message.usage_metadata.get('input_token_details', {}),
                'output_token_details': message.usage_metadata.get('output_token_details', {})
            }
        return None
    
    def extract_from_callback(self) -> Dict[str, Any]:
        """Callback에서 토큰 정보 추출
        
        Returns:
            모델별 토큰 사용량 정보 딕셔너리
        """
        if not self.usage_metadata_callback.usage_metadata:
            return {}
        
        return self.usage_metadata_callback.usage_metadata
    
    def aggregate_usage(
        self, 
        current_state: Dict[str, Any], 
        new_usage: Dict[str, Any],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """기존 State의 토큰 사용량과 새로운 사용량 집계
        
        Args:
            current_state: 현재 State의 token_usage 딕셔너리
            new_usage: 새로운 토큰 사용량 정보
            model_name: 모델명 (선택적, callback에서 추출한 경우 자동 감지)
            
        Returns:
            집계된 토큰 사용량 정보 딕셔너리
        """
        # 기본 구조 초기화
        if not current_state:
            current_state = {
                "total": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                "by_model": {}
            }
        
        # new_usage가 callback에서 추출한 경우 (모델별 정보)
        if model_name is None and isinstance(new_usage, dict):
            # callback의 usage_metadata는 모델명을 키로 가짐
            if len(new_usage) > 0:
                # 첫 번째 모델의 정보 사용 (일반적으로 하나의 모델만 사용)
                model_name = list(new_usage.keys())[0]
                model_usage = new_usage[model_name]
                
                input_tokens = model_usage.get('input_tokens', 0)
                output_tokens = model_usage.get('output_tokens', 0)
                total_tokens = model_usage.get('total_tokens', 0)
            else:
                # 사용량 정보가 없는 경우
                return current_state
        else:
            # 직접 전달된 사용량 정보
            input_tokens = new_usage.get('input_tokens', 0)
            output_tokens = new_usage.get('output_tokens', 0)
            total_tokens = new_usage.get('total_tokens', 0)
        
        # 총합 업데이트
        current_state["total"]["input_tokens"] += input_tokens
        current_state["total"]["output_tokens"] += output_tokens
        current_state["total"]["total_tokens"] += total_tokens
        
        # 모델별 집계
        if model_name:
            if model_name not in current_state["by_model"]:
                current_state["by_model"][model_name] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "call_count": 0
                }
            
            current_state["by_model"][model_name]["input_tokens"] += input_tokens
            current_state["by_model"][model_name]["output_tokens"] += output_tokens
            current_state["by_model"][model_name]["total_tokens"] += total_tokens
            current_state["by_model"][model_name]["call_count"] += 1
        
        return current_state
    
    def update_token_usage(
        self,
        current_state: Dict[str, Any],
        response: AIMessage,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """응답에서 토큰 정보를 추출하고 State에 업데이트
        
        Args:
            current_state: 현재 State의 token_usage 딕셔너리
            response: AIMessage 응답 객체
            model_name: 모델명 (선택적)
            
        Returns:
            업데이트된 토큰 사용량 정보 딕셔너리
        """
        # 방법 1: AIMessage에서 직접 추출 (최우선)
        usage_from_message = self.extract_from_message(response)
        
        if usage_from_message:
            return self.aggregate_usage(current_state, usage_from_message, model_name)
        
        # 방법 2: Callback에서 추출
        usage_from_callback = self.extract_from_callback()
        if usage_from_callback:
            return self.aggregate_usage(current_state, usage_from_callback, model_name)
        
        # 방법 3: Fallback - 사용량 정보가 없는 경우
        return current_state if current_state else {
            "total": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            },
            "by_model": {}
        }
    
    def get_summary(self, token_usage: Dict[str, Any]) -> str:
        """토큰 사용량 요약 문자열 반환 (로깅용)
        
        Args:
            token_usage: 토큰 사용량 정보 딕셔너리
            
        Returns:
            요약 문자열
        """
        if not token_usage:
            return "토큰 사용량: 정보 없음"
        
        total = token_usage.get("total", {})
        by_model = token_usage.get("by_model", {})
        
        summary = f"토큰 사용량 - 총: {total.get('total_tokens', 0)} (입력: {total.get('input_tokens', 0)}, 출력: {total.get('output_tokens', 0)})"
        
        if by_model:
            summary += "\n모델별 사용량:"
            for model_name, usage in by_model.items():
                summary += f"\n  • {model_name}: {usage.get('total_tokens', 0)} 토큰 (호출: {usage.get('call_count', 0)}회)"
        
        return summary
    
    def reset(self):
        """Callback 상태 초기화 (새로운 추적 시작 시 사용)"""
        self.usage_metadata_callback = UsageMetadataCallbackHandler()

