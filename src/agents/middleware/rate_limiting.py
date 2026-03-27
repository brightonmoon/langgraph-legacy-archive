"""
Rate Limiting Middleware

API 호출 빈도를 제한하여 비용을 관리합니다.
"""

import time
from typing import Dict, Any, Optional
from collections import deque
from .base import BaseMiddleware


class RateLimitingMiddleware(BaseMiddleware):
    """API 호출 빈도를 제한하는 Middleware"""
    
    def __init__(
        self,
        name: str = "RateLimitingMiddleware",
        max_calls_per_minute: int = 60,
        max_calls_per_hour: int = 1000
    ):
        """
        Rate Limiting Middleware 초기화
        
        Args:
            name: Middleware 이름
            max_calls_per_minute: 분당 최대 호출 수
            max_calls_per_hour: 시간당 최대 호출 수
        """
        super().__init__(name)
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_hour = max_calls_per_hour
        
        # 호출 기록 (타임스탬프 리스트)
        self.call_history = deque()
        self.hourly_calls = deque()
    
    def process(self, state: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        호출 빈도를 확인하고 제한
        
        Args:
            state: 현재 Agent 상태
            **kwargs: 추가 파라미터
            
        Returns:
            제한으로 인한 지연 시간이 포함된 상태 또는 None
        """
        current_time = time.time()
        
        # 1분 이내의 호출 필터링
        one_minute_ago = current_time - 60
        while self.call_history and self.call_history[0] < one_minute_ago:
            self.call_history.popleft()
        
        # 1시간 이내의 호출 필터링
        one_hour_ago = current_time - 3600
        while self.hourly_calls and self.hourly_calls[0] < one_hour_ago:
            self.hourly_calls.popleft()
        
        # 분당 제한 확인
        if len(self.call_history) >= self.max_calls_per_minute:
            wait_time = 60 - (current_time - self.call_history[0])
            if wait_time > 0:
                print(f"[{self.name}] Rate limit 도달: {wait_time:.1f}초 대기")
                time.sleep(wait_time)
        
        # 시간당 제한 확인
        if len(self.hourly_calls) >= self.max_calls_per_hour:
            wait_time = 3600 - (current_time - self.hourly_calls[0])
            if wait_time > 0:
                print(f"[{self.name}] 시간당 제한 도달: {wait_time:.1f}초 대기")
                return {"rate_limited": True, "wait_time": wait_time}
        
        # 호출 기록 추가
        self.call_history.append(current_time)
        self.hourly_calls.append(current_time)
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "calls_in_last_minute": len(self.call_history),
            "calls_in_last_hour": len(self.hourly_calls),
            "max_per_minute": self.max_calls_per_minute,
            "max_per_hour": self.max_calls_per_hour,
            "middleware_info": self.get_info()
        }
    
    def reset(self):
        """호출 기록 초기화"""
        self.call_history.clear()
        self.hourly_calls.clear()

