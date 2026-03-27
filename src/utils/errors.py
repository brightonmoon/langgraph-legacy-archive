"""
공통 에러 처리 시스템

에이전트, 도구, 코드 실행 등에서 일관된 에러 처리를 위한 커스텀 예외 클래스와 유틸리티 함수를 제공합니다.
"""

import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime


# ========== 커스텀 예외 클래스 ==========

class AgenticAIError(Exception):
    """기본 에러 클래스 - 모든 커스텀 예외의 베이스"""
    
    def __init__(
        self,
        message: str,
        error_type: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Args:
            message: 에러 메시지
            error_type: 에러 타입 (예: "agent", "tool", "execution")
            details: 추가 상세 정보
            original_error: 원본 예외 (있는 경우)
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """에러 정보를 딕셔너리로 변환"""
        result = {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }
        
        if self.original_error:
            result["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            }
        
        return result


class AgentError(AgenticAIError):
    """에이전트 관련 에러"""
    
    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        node_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        details = details or {}
        if agent_name:
            details["agent_name"] = agent_name
        if node_name:
            details["node_name"] = node_name
        
        super().__init__(
            message=message,
            error_type="agent",
            details=details,
            original_error=original_error
        )


class ToolError(AgenticAIError):
    """도구 관련 에러"""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        details = details or {}
        if tool_name:
            details["tool_name"] = tool_name
        if tool_args:
            details["tool_args"] = tool_args
        
        super().__init__(
            message=message,
            error_type="tool",
            details=details,
            original_error=original_error
        )


class ExecutionError(AgenticAIError):
    """코드 실행 관련 에러"""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
        node_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        details = details or {}
        if code:
            details["code_preview"] = code[:200] if code else None  # 코드 일부만 저장
        if execution_result:
            details["execution_result"] = execution_result
        if agent_name:
            details["agent_name"] = agent_name
        if node_name:
            details["node_name"] = node_name
        
        super().__init__(
            message=message,
            error_type="execution",
            details=details,
            original_error=original_error
        )


class ValidationError(AgenticAIError):
    """검증 관련 에러"""
    
    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        errors: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        details = details or {}
        if validation_type:
            details["validation_type"] = validation_type
        if errors:
            details["errors"] = errors
        
        super().__init__(
            message=message,
            error_type="validation",
            details=details,
            original_error=original_error
        )


class ConfigurationError(AgenticAIError):
    """설정 관련 에러"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_type="configuration",
            details=details,
            original_error=original_error
        )


# ========== 에러 포맷팅 유틸리티 ==========

def format_error_message(
    error: Exception,
    prefix: str = "❌",
    include_traceback: bool = False
) -> str:
    """에러 메시지를 일관된 형식으로 포맷팅
    
    Args:
        error: 예외 객체
        prefix: 메시지 접두사 (기본: "❌")
        include_traceback: 트레이스백 포함 여부
    
    Returns:
        포맷팅된 에러 메시지
    """
    if isinstance(error, AgenticAIError):
        message = f"{prefix} [{error.error_type.upper()}] {error.message}"
        
        # 상세 정보 추가
        if error.details:
            details_str = ", ".join([
                f"{k}={v}" for k, v in error.details.items()
                if k not in ["code_preview", "execution_result"]  # 너무 긴 필드는 제외
            ])
            if details_str:
                message += f" ({details_str})"
    else:
        error_type = type(error).__name__
        message = f"{prefix} [{error_type}] {str(error)}"
    
    if include_traceback:
        tb = traceback.format_exc()
        message += f"\n{tb}"
    
    return message


def format_error_for_state(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """에러를 상태 딕셔너리 형식으로 변환
    
    Args:
        error: 예외 객체
        include_traceback: 트레이스백 포함 여부
    
    Returns:
        상태에 추가할 딕셔너리
    """
    if isinstance(error, AgenticAIError):
        error_dict = error.to_dict()
        error_message = format_error_message(error, include_traceback=include_traceback)
    else:
        error_message = format_error_message(error, include_traceback=include_traceback)
        error_dict = {
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "errors": [error_message],
        "error_info": error_dict,
        "status": "error"
    }


def extract_error_summary(error: Exception, max_length: int = 200) -> str:
    """에러 요약 추출 (로깅용)
    
    Args:
        error: 예외 객체
        max_length: 최대 길이
    
    Returns:
        에러 요약 문자열
    """
    if isinstance(error, AgenticAIError):
        summary = f"[{error.error_type}] {error.message}"
    else:
        summary = f"[{type(error).__name__}] {str(error)}"
    
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary


# ========== 에러 핸들러 데코레이터 ==========

def handle_errors(
    error_type: str = "unknown",
    return_error_state: bool = True,
    log_traceback: bool = True
):
    """에러를 처리하는 데코레이터
    
    Args:
        error_type: 에러 타입 (예: "agent", "tool", "execution")
        return_error_state: True면 에러 상태 딕셔너리 반환, False면 예외 재발생
        log_traceback: 트레이스백 로깅 여부
    
    Usage:
        @handle_errors(error_type="agent", return_error_state=True)
        def my_node_function(state: Dict[str, Any]) -> Dict[str, Any]:
            # 노드 로직
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AgenticAIError as e:
                # 커스텀 예외는 그대로 사용
                if log_traceback:
                    print(format_error_message(e, include_traceback=True))
                else:
                    print(format_error_message(e))
                
                if return_error_state:
                    # 첫 번째 인자가 state 딕셔너리라고 가정
                    if args and isinstance(args[0], dict):
                        state = args[0].copy()
                        state.update(format_error_for_state(e))
                        return state
                    else:
                        return format_error_for_state(e)
                else:
                    raise
            
            except Exception as e:
                # 일반 예외를 적절한 커스텀 예외로 변환
                if error_type == "agent":
                    custom_error = AgentError(
                        message=str(e),
                        original_error=e
                    )
                elif error_type == "tool":
                    custom_error = ToolError(
                        message=str(e),
                        original_error=e
                    )
                elif error_type == "execution":
                    custom_error = ExecutionError(
                        message=str(e),
                        original_error=e
                    )
                else:
                    custom_error = AgenticAIError(
                        message=str(e),
                        error_type=error_type,
                        original_error=e
                    )
                
                if log_traceback:
                    print(format_error_message(custom_error, include_traceback=True))
                else:
                    print(format_error_message(custom_error))
                
                if return_error_state:
                    if args and isinstance(args[0], dict):
                        state = args[0].copy()
                        state.update(format_error_for_state(custom_error))
                        return state
                    else:
                        return format_error_for_state(custom_error)
                else:
                    raise custom_error
        
        return wrapper
    return decorator


# ========== 에러 카운팅 유틸리티 ==========

def increment_error_count(state: Dict[str, Any], increment: int = 1) -> int:
    """에러 카운트 증가
    
    Args:
        state: 상태 딕셔너리
        increment: 증가량
    
    Returns:
        새로운 에러 카운트
    """
    current_count = state.get("error_count", 0)
    new_count = current_count + increment
    state["error_count"] = new_count
    return new_count


def check_error_threshold(
    state: Dict[str, Any],
    threshold: int = 3
) -> bool:
    """에러 임계값 확인
    
    Args:
        state: 상태 딕셔너리
        threshold: 임계값
    
    Returns:
        임계값 초과 여부
    """
    error_count = state.get("error_count", 0)
    return error_count >= threshold

