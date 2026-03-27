"""
CSV Data Analysis Agent IPython 모드 테스트

IPython 기반 코드 생성 및 실행을 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent
from src.utils.paths import get_data_directory


def test_csv_agent_ipython_mode():
    """CSV 에이전트 IPython 모드 테스트"""
    print("=" * 60)
    print("CSV Data Analysis Agent - IPython 모드 테스트")
    print("=" * 60)
    
    # 테스트용 CSV 파일 확인
    data_dir = get_data_directory()
    test_csv = data_dir / "test_data.csv"
    
    if not test_csv.exists():
        print(f"⚠️ 테스트 CSV 파일이 없습니다: {test_csv}")
        print("   test_data.csv 파일을 생성합니다...")
        
        # 간단한 테스트 데이터 생성
        import pandas as pd
        test_data = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'score': [85, 90, 88]
        })
        test_data.to_csv(test_csv, index=False)
        print(f"✅ 테스트 CSV 파일 생성: {test_csv}")
    
    # CSV 에이전트 생성 (기본 모델 사용, IPython 모드)
    print("\n" + "=" * 60)
    print("1. CSV 에이전트 생성")
    print("=" * 60)
    
    agent = create_csv_data_analysis_agent(
        model="ollama:gpt-oss:120b-cloud",  # 기본 모델
        enable_hitl=False  # 테스트를 위해 HITL 비활성화
    )
    
    print("✅ CSV 에이전트 생성 완료")
    
    # 테스트 쿼리
    query = f"CSV 파일 {test_csv.name}의 기본 통계를 분석해주세요."
    
    print("\n" + "=" * 60)
    print("2. CSV 분석 실행")
    print("=" * 60)
    print(f"쿼리: {query}")
    print(f"CSV 파일: {test_csv}")
    
    # 에이전트 실행
    initial_state = {
        "messages": [],
        "CSV_file_path": str(test_csv),
        "query": query
    }
    
    try:
        result = agent.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print("3. 실행 결과")
        print("=" * 60)
        
        # 생성된 코드 확인
        generated_code = result.get("generated_code", "")
        if generated_code:
            print(f"✅ 코드 생성 완료 ({len(generated_code)} 문자)")
            print("\n생성된 코드 미리보기:")
            print("-" * 60)
            print(generated_code[:500])
            if len(generated_code) > 500:
                print("...")
            print("-" * 60)
        else:
            print("⚠️ 생성된 코드가 없습니다.")
        
        # 실행 결과 확인
        execution_result = result.get("execution_result", "")
        if execution_result:
            print(f"\n✅ 실행 결과 수신 완료 ({len(execution_result)} 문자)")
            print("\n실행 결과:")
            print("-" * 60)
            print(execution_result[:1000])
            if len(execution_result) > 1000:
                print("...")
            print("-" * 60)
        else:
            print("\n⚠️ 실행 결과가 없습니다.")
        
        # 최종 보고서 확인
        final_report = result.get("final_report", "")
        if final_report:
            print(f"\n✅ 최종 보고서 생성 완료 ({len(final_report)} 문자)")
            print("\n최종 보고서:")
            print("-" * 60)
            print(final_report[:1000])
            if len(final_report) > 1000:
                print("...")
            print("-" * 60)
        else:
            print("\n⚠️ 최종 보고서가 없습니다.")
        
        # 상태 확인
        status = result.get("status", "")
        print(f"\n상태: {status}")
        
        # 에러 확인
        errors = result.get("errors", [])
        if errors:
            print(f"\n⚠️ 에러 발생 ({len(errors)}개):")
            for error in errors:
                print(f"  - {error}")
        
        print("\n" + "=" * 60)
        print("테스트 완료")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_csv_agent_ipython_mode()
    
    if result:
        print("\n✅ 테스트 성공")
    else:
        print("\n❌ 테스트 실패")
        sys.exit(1)


