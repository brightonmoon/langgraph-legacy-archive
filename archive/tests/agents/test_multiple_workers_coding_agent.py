"""
Multiple Workers Coding Agent 테스트 스크립트
"""

import sys
from datetime import datetime
from src.agents.study.multiple_workers_coding_agent import MultipleWorkersCodingAgent


def test_multiple_workers_coding_agent():
    """Multiple Workers Coding Agent 테스트"""
    
    print(f"\n{'=' * 80}")
    print(f"🚀 Multiple Workers Coding Agent 테스트 시작")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")
    
    try:
        # Agent 초기화
        print("📦 Agent 초기화 중...")
        agent = MultipleWorkersCodingAgent()
        
        # Agent 정보 출력
        print("\n📊 Agent 정보:")
        print("-" * 80)
        info = agent.get_info()
        for key, value in info.items():
            if isinstance(value, list):
                print(f"   {key}:")
                for item in value:
                    print(f"      - {item}")
            else:
                print(f"   {key}: {value}")
        print("-" * 80)
        
        # 간단한 테스트 쿼리
        test_query = "Python으로 두 개의 숫자를 받아서 합을 반환하는 함수를 작성하세요"
        
        print(f"\n🎯 테스트 쿼리: {test_query}")
        print("-" * 80)
        
        # 응답 생성
        response = agent.generate_response(test_query)
        
        # 결과 출력
        print(response)
        
        print(f"\n{'=' * 80}")
        print(f"✅ 테스트 완료")
        print(f"{'=' * 80}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_multiple_workers_coding_agent()
    sys.exit(0 if success else 1)
