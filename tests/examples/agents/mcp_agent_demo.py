"""MCP Agent 사용 예제"""
import asyncio
from datetime import datetime

from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_separator,
    print_success,
    print_error,
    print_info,
    run_async_example,
)

from src.mcp.agent import MCPLangGraphAgent
from src.mcp.config.manager import get_config_manager


@run_async_example("MCP Agent 사용 예제")
async def main():
    """MCP Agent 사용 예제"""
    print_info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 설정 관리자 확인
        print_section("MCP 설정 확인", level=1)
        config_manager = get_config_manager()
        config_manager.show_status()

        # 2. MCP Agent 생성
        print_section("MCP Agent 생성", level=1)
        agent = MCPLangGraphAgent()

        # 초기화 대기
        await asyncio.sleep(3)

        # 3. Agent 상태 확인
        print_section("Agent 상태 확인", level=1)
        if agent.is_ready():
            print_success("Agent가 준비되었습니다.")
            info = agent.get_info()
            print(f"   - 타입: {info['type']}")
            print(f"   - 준비 상태: {info['ready']}")
            print(f"   - 총 도구 수: {info['total_tools']}")
            print(f"   - 로컬 도구: {len(info['local_tools'])}")
            print(f"   - MCP 도구: {len(info['mcp_tools'])}")
        else:
            print_error("Agent가 준비되지 않았습니다.")
            return

        # 4. 테스트 쿼리 실행
        print_section("테스트 쿼리 실행", level=1)

        test_queries = [
            "안녕하세요!",
            "5 + 3 * 2를 계산해주세요",
            "서울의 날씨를 알려주세요",
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n   테스트 {i}: {query}")
            print_separator("-", 40)

            try:
                response = await agent.generate_response(query)
                print(response)
            except Exception as e:
                print_error(f"테스트 {i} 실패: {str(e)}")

            print_separator("-", 40)

        # 5. 대화형 모드 테스트 (선택사항)
        print_section("대화형 모드 테스트 (선택사항)", level=1)
        print_info("대화형 모드를 테스트하려면 'y'를 입력하세요.")
        user_input = input("대화형 모드 테스트? (y/N): ").strip().lower()

        if user_input == "y":
            print("\n   대화형 모드 시작...")
            agent.chat()

        # 6. 정리
        print_section("리소스 정리", level=1)
        await agent.cleanup()

        print_success("MCP Agent 사용 예제 완료!")

    except Exception as e:
        print_error(f"예제 실행 중 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
