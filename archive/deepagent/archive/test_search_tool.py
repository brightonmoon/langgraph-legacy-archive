#!/usr/bin/env python3
"""
Brave Search 도구 단독 테스트 스크립트

검색 도구가 정상적으로 작동하는지 확인합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import create_brave_search_tool


def test_brave_search_tool():
    """Brave Search 도구 직접 테스트"""
    print("=" * 60)
    print("Brave Search 도구 단독 테스트")
    print("=" * 60)
    
    # API 키 확인
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        print("\n⚠️  BRAVE_API_KEY가 설정되지 않았습니다.")
        print("   환경변수에 BRAVE_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        return False
    
    print(f"\n✅ API 키 확인됨: {api_key[:10]}...")
    
    # 도구 생성
    print("\n🔧 Brave Search 도구 생성 중...")
    search_tool = create_brave_search_tool()
    
    if not search_tool:
        print("❌ 도구 생성 실패")
        return False
    
    print("✅ 도구 생성 성공")
    
    # 테스트 검색 실행
    test_query = "Python programming"
    print(f"\n🔍 테스트 검색 실행: '{test_query}'")
    print("-" * 60)
    
    try:
        result = search_tool.invoke({"query": test_query})
        print(f"\n📋 검색 결과:\n{result}\n")
        print("=" * 60)
        print("✅ 검색 도구 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 검색 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_brave_search_tool()
    sys.exit(0 if success else 1)







