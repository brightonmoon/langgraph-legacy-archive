"""Cursor 스타일 에이전트 사용 예제

실시간으로 코드를 생성하고 터미널에서 권한을 요청한 후 즉시 실행하는 예제입니다.
"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_separator,
    print_success,
    print_error,
    print_info,
)

from src.agents.study.cursor_style_agent import CursorStyleAgent
from langgraph.types import Command


def example_basic_usage():
    """기본 사용 예제"""
    print_header("예제 1: 기본 사용")

    agent = CursorStyleAgent(enable_permission_request=False)  # 자동 승인 모드

    query = "리스트를 정렬하는 함수를 작성하고 테스트하세요"
    result = agent.generate_response(query)

    print(result)


def example_with_permission():
    """권한 요청 포함 예제"""
    print_header("예제 2: 권한 요청 포함")

    agent = CursorStyleAgent(enable_permission_request=True)

    # Thread ID 설정
    thread_id = "test_session_001"
    config = {"configurable": {"thread_id": thread_id}}

    query = "1부터 10까지의 합을 계산하는 코드를 작성하세요"

    # 초기 실행 (코드 생성 후 interrupt)
    initial_state = {
        "user_query": query,
        "generated_code": "",
        "execution_approved": False,
        "execution_result": "",
        "code_modified": "",
        "errors": [],
        "iteration_count": 0,
        "llm_calls": 0,
        "status": "start",
        "messages": [],
    }

    try:
        result = agent.graph.invoke(initial_state, config=config)

        # interrupt 발생 시 처리
        if "__interrupt__" in result:
            print("\n⚠️ Interrupt 발생!")
            interrupt_data = result["__interrupt__"][0]
            interrupt_value = (
                interrupt_data.value
                if hasattr(interrupt_data, "value")
                else interrupt_data
            )

            code = interrupt_value.get("code", "")
            print("\n생성된 코드:")
            print(code)
            print("\n코드를 실행하시겠습니까?")

            # 사용자 입력 시뮬레이션 (실제로는 터미널에서 입력)
            user_input = "y"  # 또는 "n", "e"

            if user_input == "y":
                result = agent.graph.invoke(
                    Command(resume={"action": "approve"}), config=config
                )
                print_success("코드 실행 승인됨")
            elif user_input == "e":
                modified_code = """
def calculate_sum(n):
    return sum(range(1, n + 1))

result = calculate_sum(10)
print(f"1부터 10까지의 합: {result}")
"""
                result = agent.graph.invoke(
                    Command(resume={"action": "edit", "modified_code": modified_code}),
                    config=config,
                )
                print_success("코드 수정됨")
            else:
                result = agent.graph.invoke(
                    Command(resume={"action": "reject"}), config=config
                )
                print_error("코드 실행 거부됨")

        # 최종 결과 출력
        if "execution_result" in result:
            print("\n실행 결과:")
            print(result["execution_result"])

    except Exception as e:
        print_error(f"오류 발생: {str(e)}")


def example_streaming_mode():
    """스트리밍 모드 예제"""
    print_header("예제 3: 스트리밍 모드")

    print_info("실제 사용 시: agent.stream_with_permission(query)")
    print("   터미널에서 직접 권한 요청을 받습니다.")


def example_comparison():
    """Cursor 방식 vs IPython 방식 비교"""
    print_header("예제 4: 방식 비교")

    print_section("Cursor 방식")
    print("   - 코드 생성 -> 터미널 권한 요청 -> 즉시 실행")
    print("   - 각 실행이 독립적")
    print("   - 상태 유지 없음")
    print("   - 로우레벨 제어")

    print_section("IPython 방식")
    print("   - IPython 세션 시작 -> 코드 생성 -> 세션 내 실행")
    print("   - 상태 유지 (변수, import 등)")
    print("   - 대화형 실행")
    print("   - 세션 단위 관리")

    print_section("차이점")
    print("   - Cursor: 빠른 피드백, 명확한 권한 제어")
    print("   - IPython: 상태 유지, 효율적인 개발")


def main():
    """Cursor 스타일 에이전트 예제"""
    print_header("Cursor 스타일 에이전트 예제")

    example_basic_usage()
    print_separator()

    example_with_permission()
    print_separator()

    example_streaming_mode()
    print_separator()

    example_comparison()

    print_separator("=")
    print_success("예제 완료")


if __name__ == "__main__":
    main()
