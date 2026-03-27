"""
DESeq2_counts.csv 파일 분석 테스트

실제 쿼리로 CSV 데이터 분석 에이전트가 제대로 동작하는지 테스트합니다.
수정된 파일 경로 처리 로직이 올바르게 작동하는지 확인합니다.
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


def test_deseq2_analysis():
    """DESeq2_counts.csv 파일 분석 테스트"""
    print("=" * 80)
    print("DESeq2_counts.csv 파일 분석 테스트")
    print("=" * 80)
    
    # API 키 확인
    if not os.getenv("OLLAMA_API_KEY"):
        print("❌ OLLAMA_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일을 확인하거나 환경 변수를 설정해주세요.")
        return False
    
    # 파일 경로 확인
    csv_file_path = project_root / "data" / "DESeq2_counts.csv"
    if not csv_file_path.exists():
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_file_path}")
        return False
    
    print(f"\n✅ CSV 파일 확인: {csv_file_path}")
    print(f"   파일 크기: {csv_file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        # Agent 생성
        print("\n🔧 Agent 생성 중...")
        agent = create_csv_data_analysis_agent(
            model="ollama:gpt-oss:120b-cloud",
            code_generation_model="ollama:codegemma:latest",
            enable_hitl=False  # 테스트를 위해 HITL 비활성화
        )
        print("✅ Agent 생성 완료\n")
        
        # 실제 쿼리
        test_query = f"{csv_file_path} 해당 파일을 읽고, 이파일에서 padj < 0.05, |log2FoldChange| > 1 인 유전자를 추출하여 환자데이터를 가지고 설명을 해줘"
        
        print("=" * 80)
        print("테스트 쿼리 실행")
        print("=" * 80)
        print(f"쿼리: {test_query}\n")
        
        # Agent 실행
        print("🚀 Agent 실행 중... (시간이 걸릴 수 있습니다)\n")
        result = agent.invoke({
            "messages": [{
                "role": "user",
                "content": test_query
            }],
            "CSV_file_path": str(csv_file_path)  # 명시적으로 파일 경로 제공
        })
        
        print("\n" + "=" * 80)
        print("실행 결과")
        print("=" * 80)
        
        # 결과 출력
        if "final_report" in result and result["final_report"]:
            print("\n📊 최종 보고서:")
            print("-" * 80)
            print(result["final_report"])
            print("-" * 80)
        
        if "execution_result" in result and result["execution_result"]:
            print("\n🚀 실행 결과 (처음 1000자):")
            print("-" * 80)
            execution_result = result["execution_result"]
            if len(execution_result) > 1000:
                print(execution_result[:1000] + "...")
            else:
                print(execution_result)
            print("-" * 80)
        
        if "docker_execution_result" in result:
            docker_result = result["docker_execution_result"]
            if isinstance(docker_result, dict):
                if docker_result.get("success"):
                    print("\n✅ 도커 실행 성공")
                else:
                    print("\n❌ 도커 실행 실패")
                    if docker_result.get("stderr"):
                        print(f"에러: {docker_result['stderr'][:500]}")
        
        if "errors" in result and result["errors"]:
            print("\n❌ 에러:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        if "status" in result:
            print(f"\n📌 상태: {result['status']}")
        
        if "call_count" in result:
            print(f"📊 LLM 호출 횟수: {result['call_count']}")
        
        # 파일 경로 관련 정보 확인
        if "executed_code_file" in result and result["executed_code_file"]:
            print(f"\n📝 실행된 코드 파일: {result['executed_code_file']}")
        
        print("\n" + "=" * 80)
        print("테스트 완료")
        print("=" * 80)
        
        # 성공 여부 판단
        success = (
            result.get("status") not in ["error", "code_execution_failed"] and
            not (result.get("errors") and len(result["errors"]) > 0)
        )
        
        return success
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_deseq2_analysis()
    sys.exit(0 if success else 1)

