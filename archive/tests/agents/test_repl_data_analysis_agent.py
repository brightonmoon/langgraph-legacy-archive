"""
REPL Data Analysis Agent 테스트

REPL 기반 하이브리드 스키마 데이터 분석 에이전트를 테스트합니다.
- REPL 세션 기반 상태 유지
- 반복적 코드 생성 및 개선
- 데이터 분석 특화 기능

테스트 스키마:
1. 기본 CSV 데이터 분석
2. 통계 정보 추출
3. 데이터 시각화 코드 생성
4. 반복 루프 동작 확인
5. 에러 처리 및 재시도
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경변수 로드
load_dotenv()

from src.agents.sub_agents.repl_data_analysis_agent import create_repl_data_analysis_agent
from src.utils.paths import get_data_directory


def test_basic_csv_analysis():
    """테스트 1: 기본 CSV 데이터 분석"""
    print("\n" + "="*70)
    print("테스트 1: 기본 CSV 데이터 분석")
    print("="*70)
    
    try:
        # 에이전트 생성
        agent = create_repl_data_analysis_agent(
            model="ollama:codegemma:latest",
            max_iterations=3
        )
        
        # 테스트 데이터 파일 경로
        data_dir = get_data_directory()
        csv_file = data_dir / "test_planning.csv"
        
        if not csv_file.exists():
            print(f"⚠️ 테스트 파일이 없습니다: {csv_file}")
            print("   test_planning.csv 파일을 data/ 디렉토리에 생성해주세요.")
            return False
        
        initial_state = {
            "messages": [],
            "query": "CSV 파일의 기본 통계 정보를 출력하세요",
            "data_file_paths": [str(csv_file)],
            "max_iterations": 3,
            "iteration_count": 0,
            "should_retry": False
        }
        
        print(f"📊 분석할 파일: {csv_file}")
        print(f"📝 쿼리: {initial_state['query']}")
        print("\n실행 중...")
        
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 실행 완료")
        print(f"   상태: {result.get('status', 'N/A')}")
        print(f"   반복 횟수: {result.get('iteration_count', 0)}")
        
        if result.get('final_result'):
            print(f"\n📊 최종 결과:")
            print(result['final_result'][:500] + "..." if len(result.get('final_result', '')) > 500 else result.get('final_result', ''))
        
        if result.get('insights'):
            print(f"\n💡 인사이트:")
            for insight in result['insights']:
                print(f"   - {insight}")
        
        return result.get('status') == 'completed'
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics_extraction():
    """테스트 2: 통계 정보 추출"""
    print("\n" + "="*70)
    print("테스트 2: 통계 정보 추출")
    print("="*70)
    
    try:
        agent = create_repl_data_analysis_agent(
            model="ollama:codegemma:latest",
            max_iterations=3
        )
        
        data_dir = get_data_directory()
        csv_file = data_dir / "test_planning.csv"
        
        if not csv_file.exists():
            print(f"⚠️ 테스트 파일이 없습니다: {csv_file}")
            return False
        
        initial_state = {
            "messages": [],
            "query": "각 카테고리별 평균 가격과 총 판매량을 계산하세요",
            "data_file_paths": [str(csv_file)],
            "max_iterations": 3,
            "iteration_count": 0,
            "should_retry": False
        }
        
        print(f"📊 분석할 파일: {csv_file}")
        print(f"📝 쿼리: {initial_state['query']}")
        print("\n실행 중...")
        
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 실행 완료")
        print(f"   상태: {result.get('status', 'N/A')}")
        print(f"   반복 횟수: {result.get('iteration_count', 0)}")
        
        if result.get('execution_result'):
            print(f"\n📊 실행 결과:")
            print(result['execution_result'][:500] + "..." if len(result.get('execution_result', '')) > 500 else result.get('execution_result', ''))
        
        return result.get('status') in ['completed', 'execution_success']
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_retry_loop():
    """테스트 3: 반복 루프 동작 확인"""
    print("\n" + "="*70)
    print("테스트 3: 반복 루프 동작 확인")
    print("="*70)
    
    try:
        agent = create_repl_data_analysis_agent(
            model="ollama:codegemma:latest",
            max_iterations=2  # 낮은 반복 횟수로 테스트
        )
        
        data_dir = get_data_directory()
        csv_file = data_dir / "test_planning.csv"
        
        if not csv_file.exists():
            print(f"⚠️ 테스트 파일이 없습니다: {csv_file}")
            return False
        
        initial_state = {
            "messages": [],
            "query": "데이터를 분석하고 시각화하세요",
            "data_file_paths": [str(csv_file)],
            "max_iterations": 2,
            "iteration_count": 0,
            "should_retry": False
        }
        
        print(f"📊 분석할 파일: {csv_file}")
        print(f"📝 쿼리: {initial_state['query']}")
        print(f"🔄 최대 반복 횟수: {initial_state['max_iterations']}")
        print("\n실행 중...")
        
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 실행 완료")
        print(f"   상태: {result.get('status', 'N/A')}")
        print(f"   반복 횟수: {result.get('iteration_count', 0)}")
        print(f"   재시도 여부: {result.get('should_retry', False)}")
        
        if result.get('retry_reason'):
            print(f"   재시도 이유: {result.get('retry_reason')}")
        
        # 반복 루프가 동작했는지 확인
        iteration_count = result.get('iteration_count', 0)
        return iteration_count > 0
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """테스트 4: 에러 처리 및 재시도"""
    print("\n" + "="*70)
    print("테스트 4: 에러 처리 및 재시도")
    print("="*70)
    
    try:
        agent = create_repl_data_analysis_agent(
            model="ollama:codegemma:latest",
            max_iterations=2
        )
        
        # 존재하지 않는 파일로 테스트
        initial_state = {
            "messages": [],
            "query": "데이터를 분석하세요",
            "data_file_paths": ["nonexistent_file.csv"],
            "max_iterations": 2,
            "iteration_count": 0,
            "should_retry": False
        }
        
        print(f"📝 쿼리: {initial_state['query']}")
        print(f"📁 파일: {initial_state['data_file_paths'][0]} (존재하지 않음)")
        print("\n실행 중...")
        
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 실행 완료")
        print(f"   상태: {result.get('status', 'N/A')}")
        
        # 에러가 적절히 처리되었는지 확인
        if result.get('status') == 'error':
            print(f"   에러 메시지: {result.get('execution_error', 'N/A')}")
            return True  # 에러가 적절히 처리됨
        
        return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_session_persistence():
    """테스트 5: 세션 상태 유지 확인"""
    print("\n" + "="*70)
    print("테스트 5: 세션 상태 유지 확인")
    print("="*70)
    
    try:
        agent = create_repl_data_analysis_agent(
            model="ollama:codegemma:latest",
            max_iterations=2
        )
        
        data_dir = get_data_directory()
        csv_file = data_dir / "test_planning.csv"
        
        if not csv_file.exists():
            print(f"⚠️ 테스트 파일이 없습니다: {csv_file}")
            return False
        
        initial_state = {
            "messages": [],
            "query": "데이터를 읽고 기본 정보를 출력하세요",
            "data_file_paths": [str(csv_file)],
            "max_iterations": 2,
            "iteration_count": 0,
            "should_retry": False
        }
        
        print(f"📊 분석할 파일: {csv_file}")
        print(f"📝 쿼리: {initial_state['query']}")
        print("\n실행 중...")
        
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 실행 완료")
        print(f"   상태: {result.get('status', 'N/A')}")
        print(f"   세션 ID: {result.get('repl_session_id', 'N/A')}")
        
        if result.get('accumulated_output'):
            print(f"\n📜 누적 출력 (일부):")
            output = result['accumulated_output']
            print(output[:300] + "..." if len(output) > 300 else output)
        
        # 세션 ID가 생성되었는지 확인
        return result.get('repl_session_id') is not None
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("REPL Data Analysis Agent 테스트 시작")
    print("="*70)
    print("목적: REPL 기반 하이브리드 스키마 데이터 분석 에이전트 동작 확인")
    print("특징:")
    print("   - REPL 세션 기반 상태 유지")
    print("   - 반복적 코드 생성 및 개선")
    print("   - 데이터 분석 특화 기능")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    results.append(("기본 CSV 데이터 분석", test_basic_csv_analysis()))
    results.append(("통계 정보 추출", test_statistics_extraction()))
    results.append(("반복 루프 동작 확인", test_retry_loop()))
    results.append(("에러 처리 및 재시도", test_error_handling()))
    results.append(("세션 상태 유지 확인", test_session_persistence()))
    
    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


