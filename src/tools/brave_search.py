"""
Brave Search Tool - Brave Search API를 사용한 웹 검색 기능
"""

import os
import json
from typing import Optional, Dict, Any
from langchain.tools import tool


@tool("brave_search")
def brave_search_tool(query: str) -> str:
    """Brave Search API를 사용하여 웹에서 정보를 검색합니다.
    
    Args:
        query: 검색할 키워드나 질문
        
    Returns:
        검색 결과 문자열
    """
    try:
        # 환경변수에서 API 키 가져오기
        api_key = os.environ.get("BRAVE_API_KEY")
        if not api_key:
            return "❌ BRAVE_API_KEY 환경변수가 설정되지 않았습니다. Brave Search API 키를 설정해주세요."
        
        # LangChain의 BraveSearch 도구 사용
        from langchain_community.tools import BraveSearch
        
        # BraveSearch 도구 초기화 (검색 결과 개수 제한)
        search_tool = BraveSearch.from_api_key(
            api_key=api_key, 
            search_kwargs={"count": 5}  # 상위 5개 결과만 가져오기
        )
        
        # 검색 실행
        search_results = search_tool.run(query)
        
        # 결과가 문자열인 경우 JSON 파싱 시도
        if isinstance(search_results, str):
            try:
                results_data = json.loads(search_results)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 그대로 반환
                return f"🔍 검색 결과:\n{search_results}"
        else:
            results_data = search_results
        
        # 결과 포맷팅
        if isinstance(results_data, list) and len(results_data) > 0:
            formatted_results = f"🔍 '{query}' 검색 결과:\n\n"
            
            for i, result in enumerate(results_data[:5], 1):  # 상위 5개만 표시
                if isinstance(result, dict):
                    title = result.get('title', '제목 없음')
                    link = result.get('link', '')
                    snippet = result.get('snippet', '요약 없음')
                    
                    formatted_results += f"{i}. **{title}**\n"
                    formatted_results += f"   📎 {link}\n"
                    formatted_results += f"   📝 {snippet}\n\n"
                else:
                    formatted_results += f"{i}. {str(result)}\n\n"
            
            formatted_results += f"💡 총 {len(results_data)}개의 검색 결과를 찾았습니다."
            return formatted_results
        
        else:
            return f"🔍 '{query}'에 대한 검색 결과를 찾을 수 없습니다."
            
    except ImportError:
        return "❌ langchain-community 패키지가 설치되지 않았습니다. 'pip install langchain-community'를 실행해주세요."
    
    except Exception as e:
        return f"❌ 검색 중 오류 발생: {str(e)}"


def test_brave_search():
    """Brave Search 도구 테스트 함수"""
    print("🧪 Brave Search 도구 테스트 시작...")
    
    # API 키 확인
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("❌ BRAVE_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
    
    print(f"✅ API 키 확인됨: {api_key[:10]}...")
    
    # 테스트 검색 실행
    test_query = "Python programming"
    print(f"🔍 테스트 검색: '{test_query}'")
    
    result = brave_search_tool(test_query)
    print(f"📋 검색 결과:\n{result}")
    
    return True


if __name__ == "__main__":
    test_brave_search()
