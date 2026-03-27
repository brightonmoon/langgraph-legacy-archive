"""
CSV Data Analysis Agent - Planning Tool 활성화 테스트

Orchestrator의 전략적 계획을 코드 생성 에이전트의 Planning Tool이 
구체적 플랜으로 변환하는지 테스트합니다.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경변수 로드
load_dotenv()

from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent


def test_planning_tool_enabled():
    """Planning Tool 활성화 테스트"""
    print("=" * 60)
    print("📋 CSV Data Analysis Agent - Planning Tool 활성화 테스트")
    print("=" * 60)
    
    # 테스트용 CSV 파일 생성
    test_csv_path = project_root / "tests" / "test_data" / "test_planning.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    import pandas as pd
    df = pd.DataFrame({
        "id": range(1, 21),
        "name": [f"Product_{i}" for i in range(1, 21)],
        "price": [10.5, 20.3, 15.7, 25.9, 18.2, 30.1, 12.4, 22.6, 19.8, 28.4] * 2,
        "category": ["A", "B", "A", "C", "B", "C", "A", "B", "A", "C"] * 2,
        "sales": [100, 150, 120, 200, 180, 250, 110, 160, 140, 220] * 2
    })
    df.to_csv(test_csv_path, index=False)
    print(f"✅ 테스트 CSV 파일 생성: {test_csv_path}")
    print(f"   데이터: {len(df)}행, {len(df.columns)}컬럼")
    
    try:
        # Agent 생성 (Planning Tool 활성화됨)
        print("\n🤖 Agent 생성 중 (Planning Tool 활성화)...")
        agent = create_csv_data_analysis_agent(enable_hitl=False)  # HITL 비활성화로 자동 진행
        
        # 초기 상태 설정
        initial_state = {
            "CSV_file_path": str(test_csv_path),
            "query": "제품 가격과 판매량의 상관관계를 분석하고, 카테고리별 평균 가격을 계산하세요."
        }
        
        print("\n📊 CSV 분석 시작...")
        print(f"   파일: {test_csv_path.name}")
        print(f"   요청: {initial_state['query']}")
        print("\n" + "-" * 60)
        
        # Agent 실행
        result = agent.invoke(initial_state)
        
        # 결과 확인
        print("\n" + "=" * 60)
        print("📋 결과 확인")
        print("=" * 60)
        
        # Planning 결과 확인
        planning_result = result.get("planning_result", "")
        planning_todos = result.get("planning_todos", [])
        
        if planning_result or planning_todos:
            print("✅ Planning Tool이 실행되었습니다!")
            print(f"   Planning 결과: {'있음' if planning_result else '없음'}")
            print(f"   하위 작업 수: {len(planning_todos)}개")
            if planning_todos:
                print("\n   생성된 하위 작업:")
                for i, todo in enumerate(planning_todos[:10], 1):  # 최대 10개 출력
                    todo_desc = todo.get("description", todo.get("task", str(todo)))
                    print(f"     {i}. {todo_desc}")
                if len(planning_todos) > 10:
                    print(f"     ... 외 {len(planning_todos) - 10}개")
        else:
            print("⚠️ Planning 결과가 없습니다. (코드 생성 에이전트가 사용되지 않았을 수 있음)")
        
        # 코드 생성 확인
        generated_code = result.get("generated_code", "")
        if generated_code:
            print(f"\n✅ 코드 생성 완료 ({len(generated_code)} 문자)")
            print(f"   코드 파일: {result.get('generated_code_file', 'N/A')}")
        else:
            print("\n⚠️ 생성된 코드가 없습니다.")
        
        # 실행 결과 확인
        execution_result = result.get("execution_result", "")
        if execution_result:
            print(f"\n✅ 코드 실행 완료")
            print(f"   실행 결과 길이: {len(execution_result)} 문자")
            print(f"   실행 결과 미리보기:")
            print("   " + "\n   ".join(execution_result.split("\n")[:10]))
            if len(execution_result.split("\n")) > 10:
                print(f"   ... 외 {len(execution_result.split('\n')) - 10}줄")
        else:
            print("\n⚠️ 실행 결과가 없습니다.")
        
        # 최종 보고서 확인
        final_report = result.get("final_report", "")
        if final_report:
            print(f"\n✅ 최종 보고서 생성 완료 ({len(final_report)} 문자)")
            print(f"   보고서 미리보기:")
            print("   " + "\n   ".join(final_report.split("\n")[:15]))
            if len(final_report.split("\n")) > 15:
                print(f"   ... 외 {len(final_report.split('\n')) - 15}줄")
        else:
            print("\n⚠️ 최종 보고서가 없습니다.")
        
        # 상태 확인
        status = result.get("status", "unknown")
        print(f"\n📊 최종 상태: {status}")
        
        # 에러 확인
        errors = result.get("errors", [])
        if errors:
            print(f"\n❌ 에러 발생 ({len(errors)}개):")
            for error in errors:
                print(f"   - {error}")
        else:
            print("\n✅ 에러 없음")
        
        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)
        
        # 정리: 테스트 파일 삭제 (에러 발생 시에도 삭제)
        # 주의: Agent 실행 중에는 파일이 필요하므로 여기서 삭제하지 않음
        # 대신 테스트 종료 시 삭제하도록 변경
        
        return result
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 정리: 테스트 파일 삭제는 finally 블록에서 처리
        raise
    finally:
        # 정리: 테스트 파일 삭제
        if test_csv_path.exists():
            test_csv_path.unlink()
            print(f"\n🧹 테스트 파일 삭제: {test_csv_path}")


def test_planning_with_orchestrator_prompt():
    """Orchestrator의 전략적 계획을 Planning Tool에 전달하는 테스트"""
    print("\n" + "=" * 60)
    print("📋 Orchestrator 전략적 계획 → Planning Tool 변환 테스트")
    print("=" * 60)
    
    # 테스트용 CSV 파일 생성
    test_csv_path = project_root / "tests" / "test_data" / "test_planning_orchestrator.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    import pandas as pd
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=30, freq="D"),
        "revenue": [1000 + i * 10 + (i % 7) * 50 for i in range(30)],
        "expenses": [500 + i * 5 + (i % 5) * 20 for i in range(30)],
        "profit": [500 + i * 5 + (i % 7) * 30 for i in range(30)]
    })
    df.to_csv(test_csv_path, index=False)
    print(f"✅ 테스트 CSV 파일 생성: {test_csv_path}")
    
    try:
        # Agent 생성
        print("\n🤖 Agent 생성 중...")
        agent = create_csv_data_analysis_agent(enable_hitl=False)
        
        # 초기 상태 설정 (Orchestrator가 생성한 전략적 계획 시뮬레이션)
        initial_state = {
            "CSV_file_path": str(test_csv_path),
            "query": "수익성 분석을 수행하세요",
            # Orchestrator가 생성한 전략적 계획을 시뮬레이션
            # 실제로는 augment_prompt_node에서 생성되지만, 여기서는 직접 설정
        }
        
        print("\n📊 CSV 분석 시작...")
        print(f"   파일: {test_csv_path.name}")
        print(f"   요청: {initial_state['query']}")
        print("\n" + "-" * 60)
        
        # Agent 실행
        result = agent.invoke(initial_state)
        
        # Planning 결과 확인
        print("\n" + "=" * 60)
        print("📋 Planning Tool 실행 결과")
        print("=" * 60)
        
        # 코드 생성 에이전트가 사용되었는지 확인
        # (Planning Tool은 코드 생성 에이전트 내부에서 실행됨)
        generated_code = result.get("generated_code", "")
        if generated_code:
            print("✅ 코드 생성 에이전트가 사용되었습니다.")
            print("   → Planning Tool이 실행되었을 가능성이 높습니다.")
        else:
            print("⚠️ 코드 생성 에이전트가 사용되지 않았습니다.")
            print("   → Worker 모델을 직접 사용했을 수 있습니다.")
        
        # 실행 결과 확인
        execution_result = result.get("execution_result", "")
        if execution_result:
            print(f"\n✅ 분석 완료")
            print(f"   실행 결과 미리보기:")
            print("   " + "\n   ".join(execution_result.split("\n")[:15]))
        else:
            print("\n⚠️ 실행 결과가 없습니다.")
        
        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 정리: 테스트 파일 삭제
        if test_csv_path.exists():
            test_csv_path.unlink()
            print(f"\n🧹 테스트 파일 삭제: {test_csv_path}")


if __name__ == "__main__":
    print("🚀 Planning Tool 활성화 테스트 시작\n")
    
    try:
        # 테스트 1: Planning Tool 활성화 확인
        test_planning_tool_enabled()
        
        # 테스트 2: Orchestrator 전략적 계획 전달 확인
        test_planning_with_orchestrator_prompt()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

