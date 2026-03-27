"""
CSV Data Analysis Agent 워크플로우 테스트

Orchestrator-Worker 패턴이 제대로 작동하는지 테스트합니다.
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


def test_csv_agent_workflow():
    """CSV Data Analysis Agent 전체 워크플로우 테스트"""
    print("=" * 70)
    print("CSV Data Analysis Agent 워크플로우 테스트")
    print("=" * 70)
    
    # API 키 확인
    if not os.getenv("OLLAMA_API_KEY"):
        print("❌ OLLAMA_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일을 확인하거나 환경 변수를 설정해주세요.")
        return False
    
    # 테스트용 CSV 파일 생성
    test_csv_content = """name,age,city,score
Alice,25,Seoul,85
Bob,30,Busan,92
Charlie,28,Seoul,78
Diana,35,Incheon,95
Eve,22,Seoul,88"""
    
    test_csv_path = project_root / "tests" / "test_data.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    test_csv_path.write_text(test_csv_content, encoding='utf-8')
    print(f"\n📝 테스트 CSV 파일 생성: {test_csv_path}")
    
    try:
        # Agent 생성
        print("\n🔧 Agent 생성 중...")
        agent = create_csv_data_analysis_agent(
            model="ollama:gpt-oss:120b-cloud",
            code_generation_model="ollama:codegemma:latest",
            enable_hitl=False  # 테스트를 위해 HITL 비활성화
        )
        print("✅ Agent 생성 완료\n")
        
        # 테스트 쿼리
        test_query = f"{test_csv_path.name} 파일을 분석하여 평균 점수를 계산하고, 도시별 평균 점수를 출력해주세요."
        
        print("=" * 70)
        print("테스트 쿼리 실행")
        print("=" * 70)
        print(f"쿼리: {test_query}\n")
        
        # Agent 실행
        result = agent.invoke({
            "messages": [{
                "role": "user",
                "content": test_query
            }]
        })
        
        print("\n" + "=" * 70)
        print("실행 결과")
        print("=" * 70)
        
        # 결과 출력
        if "final_report" in result:
            print("\n📊 최종 보고서:")
            print("-" * 70)
            print(result["final_report"])
            print("-" * 70)
        
        if "execution_result" in result:
            print("\n🚀 실행 결과:")
            print("-" * 70)
            print(result["execution_result"][:500] + "..." if len(result["execution_result"]) > 500 else result["execution_result"])
            print("-" * 70)
        
        if "errors" in result and result["errors"]:
            print("\n❌ 에러:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        if "status" in result:
            print(f"\n📌 상태: {result['status']}")
        
        if "call_count" in result:
            print(f"📊 LLM 호출 횟수: {result['call_count']}")
        
        print("\n" + "=" * 70)
        print("테스트 완료")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 테스트 파일 정리 (선택사항)
        # test_csv_path.unlink(missing_ok=True)
        pass


if __name__ == "__main__":
    success = test_csv_agent_workflow()
    sys.exit(0 if success else 1)

