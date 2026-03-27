"""Checkpointer 예제

멀티 턴 대화 및 상태 지속성 테스트
"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_success,
    print_error,
)

from src.agents.study.langgraph_agent_tools import LangGraphAgentTools
from src.agents.memory.checkpointer import CheckpointerFactory, get_default_checkpointer


def test_basic_checkpointer():
    """기본 Checkpointer 테스트"""
    print_header("테스트 1: 기본 Checkpointer 생성")

    # 기본 메모리 Checkpointer 사용
    agent = LangGraphAgentTools()

    print_success("Agent가 Checkpointer와 함께 생성되었습니다.")
    print(f"   Checkpointer 타입: {type(agent.checkpointer).__name__}")

    # 기본 쿼리 실행
    response = agent.generate_response("안녕하세요!")
    print(f"\n   응답: {response[:100]}...")


def test_thread_based_conversation():
    """Thread 기반 멀티 턴 대화 테스트"""
    print_section("테스트 2: Thread 기반 멀티 턴 대화")
    print()

    # Checkpointer를 명시적으로 생성
    checkpointer = get_default_checkpointer()
    agent = LangGraphAgentTools(checkpointer=checkpointer)

    thread_id = "test-conversation-1"

    # 첫 번째 대화
    print("   첫 번째 질문: '안녕하세요. 제 이름은 홍길동입니다.'")
    response1 = agent.generate_response(
        "안녕하세요. 제 이름은 홍길동입니다.", thread_id=thread_id
    )
    print(f"   응답 1: {response1[:150]}...")

    # 두 번째 대화 (이전 대화 기억)
    print("\n   두 번째 질문: '제 이름이 뭐였죠?'")
    response2 = agent.generate_response("제 이름이 뭐였죠?", thread_id=thread_id)
    print(f"   응답 2: {response2[:150]}...")

    # 세 번째 대화
    print("\n   세 번째 질문: '제가 방금 말한 이름을 다시 말해주세요'")
    response3 = agent.generate_response(
        "제가 방금 말한 이름을 다시 말해주세요", thread_id=thread_id
    )
    print(f"   응답 3: {response3[:150]}...")


def test_multiple_threads():
    """여러 Thread 동시 관리 테스트"""
    print_section("테스트 3: 여러 Thread 동시 관리")
    print()

    checkpointer = get_default_checkpointer()
    agent = LangGraphAgentTools(checkpointer=checkpointer)

    # Thread 1: 수학 관련 대화
    print("   Thread 1 (수학): 2 + 2는 얼마인가요?")
    response1 = agent.generate_response("2 + 2는 얼마인가요?", thread_id="math-thread")
    print(f"   응답: {response1[:100]}...")

    # Thread 2: 날씨 관련 대화 (완전히 분리된 대화)
    print("\n   Thread 2 (날씨): 서울 날씨는 어때요?")
    response2 = agent.generate_response(
        "서울 날씨는 어때요?", thread_id="weather-thread"
    )
    print(f"   응답: {response2[:100]}...")

    # Thread 1로 돌아가기 (수학 대화 지속)
    print("\n   Thread 1 계속: 그럼 3 * 3은 얼마인가요?")
    response3 = agent.generate_response(
        "그럼 3 * 3은 얼마인가요?", thread_id="math-thread"
    )
    print(f"   응답: {response3[:100]}...")


def test_checkpointer_factory():
    """CheckpointerFactory 테스트"""
    print_section("테스트 4: CheckpointerFactory 기능")
    print()

    # 메모리 Checkpointer 생성
    memory_cp = CheckpointerFactory.create_in_memory()
    print_success(f"MemorySaver 생성: {type(memory_cp).__name__}")

    # 설정 기반 생성
    config = {"type": "memory"}
    config_cp = CheckpointerFactory.create_from_config(config)
    print_success(f"Config 기반 생성: {type(config_cp).__name__}")

    # 기본 Checkpointer
    default_cp = get_default_checkpointer()
    print_success(f"기본 Checkpointer: {type(default_cp).__name__}")


def main():
    """Checkpointer 통합 테스트"""
    print_header("Checkpointer 통합 테스트")
    print()

    try:
        test_basic_checkpointer()
        test_thread_based_conversation()
        test_multiple_threads()
        test_checkpointer_factory()

        print_section("결과")
        print_success("모든 테스트 완료!")

    except Exception as e:
        print_error(f"테스트 중 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
