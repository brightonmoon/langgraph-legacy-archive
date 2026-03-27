"""CSV Data Analysis Agent 사용 예제

CSV 파일을 읽고 분석하는 Agent의 사용 예제입니다.
"""
import os
from dotenv import load_dotenv

from examples._utils import PROJECT_ROOT, ensure_test_data_dir  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_separator,
    print_success,
    print_error,
    print_warning,
    print_info,
)

load_dotenv()

from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent


def example_basic_analysis():
    """기본 분석 예제"""
    print_header("CSV Data Analysis Agent - 기본 분석 예제")

    # 테스트용 CSV 파일 생성
    test_csv_path = ensure_test_data_dir() / "example_sales.csv"

    import pandas as pd

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "product": ["A", "B", "C"] * 3 + ["A"],
            "sales": [100, 150, 120, 110, 160, 130, 105, 155, 125, 115],
            "region": ["North", "South", "East"] * 3 + ["North"],
        }
    )
    df.to_csv(test_csv_path, index=False)
    print_success(f"테스트 CSV 파일 생성: {test_csv_path}")

    try:
        # Agent 생성
        print_info("Agent 생성 중...")
        agent = create_csv_data_analysis_agent()

        # 초기 상태 설정
        initial_state = {
            "csv_filepath": str(test_csv_path),
            "user_query": "제품별 평균 판매량과 지역별 판매량 분포를 분석하세요",
            "csv_metadata": None,
            "generated_code": "",
            "execution_result": "",
            "analysis_result": "",
            "final_report": "",
            "messages": [],
            "status": "start",
            "errors": [],
            "llm_calls": 0,
        }

        # Agent 실행
        print_info("Agent 실행 중...")
        print_separator()

        result = agent.invoke(initial_state)

        # 결과 출력
        print_section("분석 결과")

        print(f"\n   상태: {result['status']}")
        print(f"   LLM 호출: {result.get('llm_calls', 0)}회")

        if result.get("generated_code"):
            print_section("생성된 코드", level=2)
            code = result["generated_code"]
            print(code[:500] + "..." if len(code) > 500 else code)

        if result.get("execution_result"):
            print_section("실행 결과", level=2)
            exec_result = result["execution_result"]
            print(exec_result[:1000] + "..." if len(exec_result) > 1000 else exec_result)

        if result.get("final_report"):
            print_section("최종 보고서", level=2)
            print(result["final_report"])

        if result.get("errors"):
            print_section("에러", level=2)
            for error in result["errors"]:
                print_error(error)

    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        # 테스트 파일 정리
        if test_csv_path.exists():
            test_csv_path.unlink()
            print_info(f"테스트 파일 삭제: {test_csv_path}")


def example_custom_csv():
    """사용자 지정 CSV 파일 분석 예제"""
    print_header("CSV Data Analysis Agent - 사용자 지정 CSV 분석")

    from pathlib import Path

    # 사용자에게 CSV 파일 경로 입력 받기
    csv_path = input("\n   분석할 CSV 파일 경로를 입력하세요 (Enter로 건너뛰기): ").strip()

    if not csv_path:
        print_warning("CSV 파일 경로가 제공되지 않아 예제를 건너뜁니다.")
        return

    csv_file = Path(csv_path).expanduser()

    if not csv_file.exists():
        print_error(f"파일이 존재하지 않습니다: {csv_path}")
        return

    if not csv_file.suffix.lower() == ".csv":
        print_warning(f"CSV 파일이 아닙니다: {csv_path}")
        return

    # 사용자에게 분석 요청 입력 받기
    user_query = input("\n   분석 요청을 입력하세요 (Enter로 기본 요청 사용): ").strip()
    if not user_query:
        user_query = "데이터의 기본 통계와 주요 인사이트를 분석하세요"

    try:
        # Agent 생성
        print_info("Agent 생성 중...")
        agent = create_csv_data_analysis_agent()

        # 초기 상태 설정
        initial_state = {
            "csv_filepath": str(csv_file),
            "user_query": user_query,
            "csv_metadata": None,
            "generated_code": "",
            "execution_result": "",
            "analysis_result": "",
            "final_report": "",
            "messages": [],
            "status": "start",
            "errors": [],
            "llm_calls": 0,
        }

        # Agent 실행
        print_info("Agent 실행 중...")
        print_separator()

        result = agent.invoke(initial_state)

        # 결과 출력
        print_section("분석 결과")

        if result.get("final_report"):
            print_section("최종 보고서", level=2)
            print(result["final_report"])

        if result.get("errors"):
            print_section("에러", level=2)
            for error in result["errors"]:
                print_error(error)

    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def main():
    """메인 함수"""
    if not os.getenv("OLLAMA_API_KEY"):
        print_warning("OLLAMA_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 OLLAMA_API_KEY를 설정하세요.")
        return

    print("\n선택하세요:")
    print("1. 기본 분석 예제 (테스트 CSV 파일 사용)")
    print("2. 사용자 지정 CSV 파일 분석")

    choice = input("\n선택 (1 또는 2, Enter로 기본값 1): ").strip()

    if choice == "2":
        example_custom_csv()
    else:
        example_basic_analysis()


if __name__ == "__main__":
    main()
