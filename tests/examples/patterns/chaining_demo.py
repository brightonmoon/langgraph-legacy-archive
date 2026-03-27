"""LangGraph Chaining Agent 예제

Prompt Chaining 패턴을 사용한 농담 생성 워크플로우 예제
"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_section,
    print_agent_info,
    print_test_case,
    print_error,
    run_example,
    check_agent_ready,
)

from src.agents.study.langgraph_agent_chaining import LangGraphAgentChaining


@run_example("LangGraph Chaining Agent 예제")
def main():
    """LangGraph Chaining Agent 예제 실행"""
    # Agent 생성
    agent = LangGraphAgentChaining()

    if not check_agent_ready(agent):
        return

    # Agent 정보 출력
    print_section("Agent 정보")
    info = agent.get_info()
    print_agent_info(info)

    # 예제 실행
    test_cases = ["고양이", "프로그래머", "코딩"]

    for i, topic in enumerate(test_cases, 1):
        print_test_case(i, f"{topic} 농담 생성")

        try:
            response = agent.generate_response(topic)
            print(response)
        except Exception as e:
            print_error(f"오류 발생: {str(e)}")


if __name__ == "__main__":
    main()
