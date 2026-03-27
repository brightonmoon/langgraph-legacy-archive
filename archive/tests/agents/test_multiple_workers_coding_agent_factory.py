"""
Factory를 통한 Multiple Workers Coding Agent 테스트
"""

import sys
from datetime import datetime
from src.agents.factory import AgentFactory


def test_factory_creation():
    """Factory를 통한 Agent 생성 테스트"""
    
    print(f"\n{'=' * 80}")
    print(f"🚀 Factory를 통한 Multiple Workers Coding Agent 테스트")
    print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")
    
    try:
        # 사용 가능한 Agent 목록 확인
        print("📋 사용 가능한 Agent 목록:")
        print("-" * 80)
        available_agents = AgentFactory.get_available_agents()
        for agent_type in available_agents:
            print(f"   - {agent_type}")
        print("-" * 80)
        
        # Factory를 통해 Agent 생성
        print("\n📦 Factory를 통해 Agent 생성 중...")
        agent = AgentFactory.create_agent("multiple_workers_coding")
        
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
        test_query = "Python으로 리스트에서 최댓값을 찾는 함수를 작성하세요"
        
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
    success = test_factory_creation()
    sys.exit(0 if success else 1)
