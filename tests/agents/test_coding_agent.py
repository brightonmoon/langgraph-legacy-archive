#!/usr/bin/env python3
"""
코딩 에이전트 테스트 스크립트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agents import AgentFactory


def test_coding_agent():
    """코딩 에이전트 테스트"""
    print("\n" + "=" * 60)
    print("🧪 코딩 에이전트 테스트")
    print("=" * 60)
    
    try:
        # Agent 생성
        print("\n1️⃣ Agent 생성 중...")
        agent = AgentFactory.create_agent("coding")
        
        if not agent.is_ready():
            print("❌ Agent 초기화 실패")
            return
        
        print("✅ Agent 준비 완료!")
        
        # Agent 정보 표시
        info = agent.get_info()
        print(f"\n📊 Agent 정보:")
        print(f"   타입: {info['type']}")
        print(f"   모델: {info['model']}")
        print(f"   아키텍처: {info['architecture']}")
        print(f"   기능: {', '.join(info['features'])}")
        
        # 간단한 코딩 작업 테스트
        print("\n2️⃣ 코딩 작업 테스트...")
        test_query = "Python으로 숫자 리스트를 정렬하는 함수를 작성해줘"
        print(f"   요청: {test_query}")
        
        print("\n3️⃣ 응답 생성 중...")
        response = agent.generate_response(test_query)
        
        print("\n4️⃣ 결과:")
        print(response)
        
        print("\n✅ 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_coding_agent()

