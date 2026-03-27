"""Brave Search 도구 사용 예제"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_separator,
    print_error,
    run_example,
    check_agent_ready,
)

from src.agents.study.langgraph_agent_tools import LangGraphAgentTools


@run_example("Brave Search 도구 사용 예제")
def main():
    """Brave Search 도구 사용 예제"""
    # Agent 초기화
    agent = LangGraphAgentTools()

    if not check_agent_ready(agent):
        return

    # 테스트 쿼리들
    test_queries = [
        "오늘 날씨는 어때?",
        "2 + 3 * 4 계산해줘",
        "Python 최신 버전 정보",
        "인공지능 최신 동향",
        "LangChain 사용법",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n   테스트 {i}: {query}")
        print_separator("-", 30)

        try:
            response = agent.generate_response(query)
            print(response)
        except Exception as e:
            print_error(f"오류 발생: {e}")

        print_separator("-", 30)

        # 사용자 입력 대기 (선택사항)
        if i < len(test_queries):
            input("다음 테스트를 계속하려면 Enter를 누르세요...")


if __name__ == "__main__":
    main()
