"""LangGraph Parallel Agent 예제

Parallelization 패턴을 사용한 병렬 콘텐츠 생성 워크플로우 예제
"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_agent_info,
    print_test_case,
    print_success,
    print_error,
    run_example,
    check_agent_ready,
)

from src.agents.study.langgraph_agent_parallel import LangGraphAgentParallel
import time


@run_example("LangGraph Parallel Agent 예제")
def main():
    """LangGraph Parallel Agent 예제 실행"""
    # Agent 생성
    agent = LangGraphAgentParallel()

    if not check_agent_ready(agent):
        return

    # Agent 정보 출력
    print_section("Agent 정보")
    info = agent.get_info()
    print_agent_info(info)

    # 예제 실행
    test_cases = ["고양이", "봄", "프로그래밍"]

    for i, topic in enumerate(test_cases, 1):
        print_test_case(i, f"{topic} 콘텐츠 생성 (병렬 처리)")

        try:
            start_time = time.time()
            response = agent.generate_response(topic)
            end_time = time.time()

            print(response)
            print(f"\n⏱️ 실행 시간: {end_time - start_time:.2f}초")

        except Exception as e:
            print_error(f"오류 발생: {str(e)}")


if __name__ == "__main__":
    main()
