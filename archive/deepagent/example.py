#!/usr/bin/env python3
"""
DeepAgent 간단한 예제 스크립트

deepagents 라이브러리를 사용하는 기본 예제를 실행합니다.
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from deepagent.agent import DeepAgentLibrary


def main():
    """간단한 예제 실행"""
    print("=" * 60)
    print("DeepAgent 라이브러리 예제")
    print("=" * 60)
    
    try:
        # 에이전트 생성
        print("\n1. 에이전트 생성 중...")
        agent = DeepAgentLibrary(use_ollama=True)
        
        # 에이전트 정보 출력
        print("\n2. 에이전트 정보:")
        info = agent.get_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # 간단한 쿼리 실행
        print("\n3. 쿼리 실행 예제:")
        query = "안녕하세요! 간단히 자기소개를 해주세요."
        print(f"   쿼리: {query}")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"   ❌ 오류: {result['error']}")
            return 1
        
        if result.get("messages"):
            response = result["messages"][-1].content
            print(f"\n   응답:\n   {response}\n")
        
        print("=" * 60)
        print("✅ 예제 실행 완료!")
        print("=" * 60)
        print("\n💡 더 많은 기능을 테스트하려면:")
        print("   - python deepagent/run.py           (대화형 모드)")
        print("   - python deepagent/test.py         (전체 테스트)")
        print("   - python deepagent/example.py      (이 예제)")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())














