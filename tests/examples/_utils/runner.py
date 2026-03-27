"""예제 실행 공통 패턴

예제 파일들에서 사용하는 공통 실행 패턴을 제공합니다.
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Any, TypeVar

from .display import print_header, print_success, print_error

F = TypeVar("F", bound=Callable[..., Any])


def run_example(name: str, emoji: str = "") -> Callable[[F], F]:
    """동기 예제 실행 데코레이터

    예제 함수를 래핑하여 헤더 출력, 시간 측정, 에러 핸들링을 제공합니다.

    Args:
        name: 예제 이름
        emoji: 헤더에 표시할 이모지 (선택)

    Example:
        @run_example("LangGraph Parallel Agent")
        def main():
            agent = LangGraphAgentParallel()
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            print_header(name, emoji)
            print()

            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                print(f"\n⏱️ 실행 시간: {elapsed:.2f}초")
                print_success("예제 실행 완료")
                return result
            except KeyboardInterrupt:
                print("\n⚠️ 사용자에 의해 중단됨")
                raise
            except Exception as e:
                print_error(f"오류 발생: {str(e)}")
                raise

        return wrapper  # type: ignore

    return decorator


def run_async_example(name: str, emoji: str = "") -> Callable[[F], F]:
    """비동기 예제 실행 데코레이터

    비동기 예제 함수를 래핑하여 헤더 출력, 시간 측정, 에러 핸들링을 제공합니다.

    Args:
        name: 예제 이름
        emoji: 헤더에 표시할 이모지 (선택)

    Example:
        @run_async_example("MCP Agent 예제")
        async def main():
            agent = MCPLangGraphAgent()
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            print_header(name, emoji)
            print()

            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                print(f"\n⏱️ 실행 시간: {elapsed:.2f}초")
                print_success("예제 실행 완료")
                return result
            except KeyboardInterrupt:
                print("\n⚠️ 사용자에 의해 중단됨")
                raise
            except Exception as e:
                print_error(f"오류 발생: {str(e)}")
                raise

        return wrapper  # type: ignore

    return decorator


def run_test_cases(
    agent,
    test_cases: list[str],
    method_name: str = "generate_response",
    is_async: bool = False,
) -> list[Any]:
    """테스트 케이스 실행 헬퍼

    여러 테스트 케이스를 순차적으로 실행합니다.

    Args:
        agent: Agent 인스턴스
        test_cases: 테스트 입력 리스트
        method_name: 호출할 메서드 이름
        is_async: 비동기 메서드 여부

    Returns:
        각 테스트 케이스의 결과 리스트
    """
    from .display import print_test_case, print_separator

    results = []
    method = getattr(agent, method_name)

    for i, test_input in enumerate(test_cases, 1):
        print_test_case(i, test_input)

        try:
            start = time.time()

            if is_async:
                result = asyncio.get_event_loop().run_until_complete(method(test_input))
            else:
                result = method(test_input)

            elapsed = time.time() - start

            print(result)
            print(f"\n⏱️ 실행 시간: {elapsed:.2f}초")
            results.append(result)

        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            results.append(None)

        print_separator()

    return results


def check_agent_ready(agent, exit_on_fail: bool = True) -> bool:
    """Agent 준비 상태 확인

    Args:
        agent: Agent 인스턴스
        exit_on_fail: 실패 시 함수 종료 여부

    Returns:
        Agent 준비 상태
    """
    print("📝 Agent 초기화 중...")

    if not agent.is_ready():
        print("❌ Agent 초기화 실패")
        return False

    print("✅ Agent 초기화 완료")
    return True
