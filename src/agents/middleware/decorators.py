"""
Middleware 데코레이터

Middleware를 쉽게 적용할 수 있는 데코레이터를 제공합니다.
"""

from functools import wraps
from typing import Callable, List, Any, Dict


def apply_middleware(
    middleware_list: List[Any],
    stage: str = "before"
):
    """
    함수에 Middleware를 적용하는 데코레이터
    
    Args:
        middleware_list: 적용할 Middleware 리스트
        stage: 적용 시점 ("before", "after", "around")
    
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Dict[str, Any], *args, **kwargs) -> Any:
            # Before stage: 각 middleware로 상태 처리
            if stage in ["before", "around"]:
                for middleware in middleware_list:
                    result = middleware.process(state, **kwargs)
                    if result:
                        state.update(result)
            
            # 원본 함수 실행
            try:
                result = func(state, *args, **kwargs)
            except Exception as e:
                # 에러 발생 시 각 middleware에 알림
                for middleware in middleware_list:
                    if hasattr(middleware, 'handle_error'):
                        middleware.handle_error(e, state)
                raise
            
            # After stage: 결과 후처리
            if stage in ["after", "around"]:
                if isinstance(result, dict):
                    for middleware in middleware_list:
                        processed = middleware.process(result, **kwargs)
                        if processed:
                            result.update(processed)
            
            return result
        
        return wrapper
    return decorator


def middleware_chain(middleware_list: List[Any]):
    """
    Middleware 체인을 생성하는 헬퍼 함수
    
    Args:
        middleware_list: Middleware 리스트
        
    Returns:
        체인 실행 함수
    """
    def execute(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        current_state = state.copy()
        
        for middleware in middleware_list:
            result = middleware.process(current_state, **kwargs)
            if result:
                current_state.update(result)
        
        return current_state
    
    return execute

