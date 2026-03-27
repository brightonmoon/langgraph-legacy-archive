"""
Logging Middleware

Agent의 실행 과정을 로깅하고 분석합니다.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseMiddleware


class LoggingMiddleware(BaseMiddleware):
    """Agent 실행 과정을 로깅하는 Middleware"""
    
    def __init__(self, name: str = "LoggingMiddleware", verbose: bool = True):
        """
        Logging Middleware 초기화
        
        Args:
            name: Middleware 이름
            verbose: 상세 로그 출력 여부
        """
        super().__init__(name)
        self.verbose = verbose
        self.logs = []
        self.stats = {
            "total_calls": 0,
            "tool_calls": 0,
            "errors": 0,
            "average_time": 0.0
        }
    
    def process(self, state: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        상태를 처리하고 로깅
        
        Args:
            state: 현재 Agent 상태
            **kwargs: 추가 파라미터 (start_time: 시작 시간여부)
            
        Returns:
            None (상태 수정 없음)
        """
        start_time_flag = kwargs.get('start_time', None)
        
        if start_time_flag is None:
            # 시작 시간 기록
            if not hasattr(self, 'start_time'):
                self.start_time = time.time()
            self._log("🤖 Agent 실행 시작", state)
            return None
        
        # 실행 시간 계산
        if hasattr(self, 'start_time'):
            elapsed = time.time() - self.start_time
        else:
            elapsed = 0
        self.stats["total_calls"] += 1
        
        # 도구 호출 수집
        tool_calls = state.get("tool_calls", [])
        if tool_calls:
            self.stats["tool_calls"] += len(tool_calls)
            self._log(f"🔧 {len(tool_calls)}개의 도구 호출", state)
        
        # 에러 확인 (응답이 "❌"로 시작하거나 명확한 에러 메시지가 있는 경우만)
        model_response = state.get("model_response", "")
        is_error = (
            model_response.startswith("❌") or 
            "응답 생성 중 오류 발생" in model_response or
            "그래프 실행 중 오류 발생" in model_response or
            "초기화되지 않았습니다" in model_response
        )
        
        if is_error:
            self.stats["errors"] += 1
            self._log(f"❌ 에러 발생: {model_response[:100]}", state)
        
        # 평균 시간 업데이트
        self.stats["average_time"] = (
            (self.stats["average_time"] * (self.stats["total_calls"] - 1) + elapsed) 
            / self.stats["total_calls"]
        )
        
        self._log(f"✅ 실행 완료 (소요 시간: {elapsed:.2f}초)", state)
        
        return None
    
    def _log(self, message: str, state: Dict[str, Any]):
        """로그 메시지 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "state_keys": list(state.keys())
        }
        self.logs.append(log_entry)
        
        if self.verbose:
            print(f"[{self.name}] {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            **self.stats,
            "total_logs": len(self.logs),
            "middleware_info": self.get_info()
        }
    
    def clear_logs(self):
        """로그 초기화"""
        self.logs = []
        self.stats = {
            "total_calls": 0,
            "tool_calls": 0,
            "errors": 0,
            "average_time": 0.0
        }
        # start_time도 함께 리셋
        if hasattr(self, 'start_time'):
            delattr(self, 'start_time')
    
    def reset_start_time(self):
        """시작 시간 리셋 (새로운 Agent 실행 시작)"""
        if hasattr(self, 'start_time'):
            delattr(self, 'start_time')

