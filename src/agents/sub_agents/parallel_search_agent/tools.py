"""
병렬 검색 에이전트용 검색 도구들

Tavily와 Brave Search API를 사용한 검색 도구를 제공합니다.
"""

import os
import json
from typing import Optional, Literal
from langchain.tools import tool
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


def create_tavily_search_tool(api_key: Optional[str] = None):
    """Tavily Search 도구 생성
    
    Tavily API를 사용한 웹 검색 도구입니다.
    langchain-tavily 패키지를 사용합니다.
    
    Args:
        api_key: Tavily API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        Tavily Search 도구 함수
    """
    try:
        # 새로운 langchain-tavily 패키지 사용
        from langchain_tavily import TavilySearch
        
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            print("⚠️  TAVILY_API_KEY가 설정되지 않았습니다.")
            print("   Tavily Search 도구를 사용하려면 TAVILY_API_KEY를 설정하세요.")
            return None
        
        # TavilySearch 도구 초기화 (새로운 API)
        tavily_search = TavilySearch(
            max_results=5,  # 상위 5개 결과만 가져오기
            api_key=api_key
        )
        
        @tool("tavily_search")
        def tavily_search_tool(query: str) -> str:
            """Tavily Search API를 사용하여 웹에서 정보를 검색합니다.
            
            Tavily는 AI 검색 엔진으로, 질문에 대한 답변 중심의 검색 결과를 제공합니다.
            
            Args:
                query: 검색할 키워드나 질문
                
            Returns:
                검색 결과 문자열
            """
            try:
                # TavilySearch는 Tool 인터페이스를 따르므로 _call()을 사용하여 원시 결과 가져오기
                # invoke()는 포맷된 문자열을 반환하지만, _call()은 원시 딕셔너리 결과를 반환
                try:
                    # _call() 메서드를 사용하여 원시 결과 가져오기
                    raw_results = tavily_search._call(query)
                except AttributeError:
                    # _call()이 없는 경우 invoke() 사용 (문자열 반환)
                    try:
                        search_results_str = tavily_search.invoke(query)
                        # 문자열이 반환된 경우 그대로 반환
                        if isinstance(search_results_str, str):
                            return f"🔍 [Tavily] '{query}' 검색 결과:\n\n{search_results_str}"
                        raw_results = search_results_str
                    except Exception:
                        # run() 시도
                        search_results_str = tavily_search.run(query)
                        if isinstance(search_results_str, str):
                            return f"🔍 [Tavily] '{query}' 검색 결과:\n\n{search_results_str}"
                        raw_results = search_results_str
                
                # 결과 포맷팅
                # raw_results는 딕셔너리 형식일 수 있음
                if isinstance(raw_results, dict):
                    # Tavily API 응답 형식: {"results": [...]} 또는 {"answer": "...", "results": [...]}
                    results_list = raw_results.get("results", [])
                    if results_list and len(results_list) > 0:
                        formatted_results = f"🔍 [Tavily] '{query}' 검색 결과:\n\n"
                        
                        # answer가 있으면 먼저 표시
                        if "answer" in raw_results and raw_results["answer"]:
                            formatted_results += f"**답변**: {raw_results['answer']}\n\n"
                        
                        for i, result in enumerate(results_list[:5], 1):
                            if isinstance(result, dict):
                                title = result.get('title', '제목 없음')
                                url = result.get('url', '')
                                content = result.get('content', result.get('snippet', result.get('raw_content', '요약 없음')))
                                
                                formatted_results += f"{i}. **{title}**\n"
                                formatted_results += f"   📎 {url}\n"
                                formatted_results += f"   📝 {content[:200]}...\n\n"  # 처음 200자만
                            else:
                                formatted_results += f"{i}. {str(result)}\n\n"
                        
                        formatted_results += f"💡 총 {len(results_list)}개의 검색 결과를 찾았습니다."
                        return formatted_results
                
                elif isinstance(raw_results, list) and len(raw_results) > 0:
                    # 리스트 형식인 경우
                    formatted_results = f"🔍 [Tavily] '{query}' 검색 결과:\n\n"
                    
                    for i, result in enumerate(raw_results[:5], 1):
                        if isinstance(result, dict):
                            title = result.get('title', '제목 없음')
                            url = result.get('url', '')
                            content = result.get('content', result.get('snippet', result.get('raw_content', '요약 없음')))
                            
                            formatted_results += f"{i}. **{title}**\n"
                            formatted_results += f"   📎 {url}\n"
                            formatted_results += f"   📝 {content[:200]}...\n\n"  # 처음 200자만
                        else:
                            formatted_results += f"{i}. {str(result)}\n\n"
                    
                    formatted_results += f"💡 총 {len(raw_results)}개의 검색 결과를 찾았습니다."
                    return formatted_results
                
                elif isinstance(raw_results, str):
                    # 문자열 형식인 경우 그대로 반환
                    return f"🔍 [Tavily] '{query}' 검색 결과:\n\n{raw_results}"
                
                else:
                    return f"🔍 [Tavily] '{query}'에 대한 검색 결과를 찾을 수 없습니다. (결과 형식: {type(raw_results)})"
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                return f"❌ [Tavily] 검색 중 오류 발생: {str(e)}\n상세: {error_detail}"
        
        return tavily_search_tool
        
    except ImportError:
        print("⚠️  langchain-tavily 패키지가 설치되지 않았습니다.")
        print("   pip install -U langchain-tavily 또는 uv add langchain-tavily")
        return None
    except Exception as e:
        print(f"⚠️  Tavily Search 도구 생성 중 오류: {str(e)}")
        return None


def create_brave_search_tool(api_key: Optional[str] = None):
    """Brave Search 도구 생성
    
    Brave Search API를 사용한 웹 검색 도구입니다.
    
    Args:
        api_key: Brave API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        Brave Search 도구 함수
    """
    try:
        from langchain_community.tools import BraveSearch
        
        api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not api_key:
            print("⚠️  BRAVE_API_KEY가 설정되지 않았습니다.")
            print("   Brave Search 도구를 사용하려면 BRAVE_API_KEY를 설정하세요.")
            return None
        
        # BraveSearch 도구 초기화
        brave_search_instance = BraveSearch.from_api_key(
            api_key=api_key,
            search_kwargs={"count": 5}  # 상위 5개 결과만 가져오기
        )
        
        @tool("brave_search")
        def brave_search_tool(query: str) -> str:
            """Brave Search API를 사용하여 웹에서 정보를 검색합니다.
            
            Brave Search는 프라이버시 중심의 검색 엔진으로, 일반적인 웹 검색 결과를 제공합니다.
            
            Args:
                query: 검색할 키워드나 질문
                
            Returns:
                검색 결과 문자열
            """
            try:
                # 검색 실행
                search_results = brave_search_instance.run(query)
                
                # 결과가 문자열인 경우 JSON 파싱 시도
                if isinstance(search_results, str):
                    try:
                        results_data = json.loads(search_results)
                    except json.JSONDecodeError:
                        # JSON이 아닌 경우 그대로 반환
                        return f"🔍 [Brave] 검색 결과:\n{search_results}"
                else:
                    results_data = search_results
                
                # 결과 포맷팅
                if isinstance(results_data, list) and len(results_data) > 0:
                    formatted_results = f"🔍 [Brave] '{query}' 검색 결과:\n\n"
                    
                    for i, result in enumerate(results_data[:5], 1):
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
                    return f"🔍 [Brave] '{query}'에 대한 검색 결과를 찾을 수 없습니다."
                    
            except Exception as e:
                return f"❌ [Brave] 검색 중 오류 발생: {str(e)}"
        
        return brave_search_tool
        
    except ImportError:
        print("⚠️  langchain-community 패키지가 설치되지 않았습니다.")
        print("   pip install langchain-community 또는 uv add langchain-community")
        return None
    except Exception as e:
        print(f"⚠️  Brave Search 도구 생성 중 오류: {str(e)}")
        return None


def create_parallel_search_tool(
    tavily_api_key: Optional[str] = None,
    brave_api_key: Optional[str] = None
):
    """병렬 검색 도구 생성
    
    Tavily와 Brave Search를 내부에서 병렬로 실행하는 통합 검색 도구입니다.
    이 도구를 사용하면 하나의 호출로 두 검색 엔진이 동시에 실행됩니다.
    
    Args:
        tavily_api_key: Tavily API 키 (None이면 환경변수에서 가져옴)
        brave_api_key: Brave API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        병렬 검색 도구 함수
    """
    # 개별 검색 도구 생성
    tavily_tool = create_tavily_search_tool(api_key=tavily_api_key)
    brave_tool = create_brave_search_tool(api_key=brave_api_key)
    
    if not tavily_tool and not brave_tool:
        print("⚠️  Tavily와 Brave Search 도구를 모두 생성할 수 없습니다.")
        return None
    
    @tool("parallel_search")
    def parallel_search_tool(query: str) -> str:
        """Tavily와 Brave Search를 병렬로 사용하여 웹에서 정보를 검색합니다.
        
        이 도구는 내부에서 두 검색 엔진을 동시에 실행하여 결과를 취합합니다.
        병렬 실행으로 더 빠른 검색 결과를 제공합니다.
        
        Args:
            query: 검색할 키워드나 질문
            
        Returns:
            두 검색 엔진의 결과를 통합한 검색 결과 문자열
        """
        # 현재 날짜 정보 추가
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        current_year = datetime.now().strftime("%Y")
        
        # 검색 쿼리에 날짜 정보 추가 (없는 경우)
        if current_year not in query and "최신" not in query:
            optimized_query = f"{query} {current_year} 최신"
        else:
            optimized_query = query
        
        results = {}
        errors = {}
        
        # 병렬 실행을 위한 함수
        def run_tavily():
            if tavily_tool:
                try:
                    # @tool 데코레이터로 생성된 StructuredTool은 invoke() 메서드 사용
                    # tavily_search_tool은 query: str 인자를 받으므로 딕셔너리로 전달
                    result = tavily_tool.invoke({"query": optimized_query})
                    return ("tavily", result)
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    return ("tavily", f"❌ [Tavily] 검색 중 오류 발생: {str(e)}\n상세: {error_detail}")
            return None
        
        def run_brave():
            if brave_tool:
                try:
                    # @tool 데코레이터로 생성된 StructuredTool은 invoke() 메서드 사용
                    # brave_search_tool은 query: str 인자를 받으므로 딕셔너리로 전달
                    result = brave_tool.invoke({"query": optimized_query})
                    return ("brave", result)
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    return ("brave", f"❌ [Brave] 검색 중 오류 발생: {str(e)}\n상세: {error_detail}")
            return None
        
        # ThreadPoolExecutor를 사용한 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            if tavily_tool:
                futures.append(executor.submit(run_tavily))
            if brave_tool:
                futures.append(executor.submit(run_brave))
            
            # 결과 수집
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        engine_name, result_data = result
                        results[engine_name] = result_data
                except Exception as e:
                    print(f"⚠️ 병렬 검색 실행 중 오류: {str(e)}")
        
        # 결과 통합
        if not results:
            return f"❌ 검색 결과를 가져올 수 없습니다. API 키를 확인하세요."
        
        # 통합 결과 생성
        combined_result = f"""🔍 병렬 검색 결과 (병렬 실행 완료): '{optimized_query}'

**현재 날짜**: {current_date}
**검색 연도**: {current_year}

"""
        
        if "tavily" in results:
            combined_result += f"\n{'='*60}\n[Tavily Search 결과]\n{'='*60}\n{results['tavily']}\n"
        
        if "brave" in results:
            combined_result += f"\n{'='*60}\n[Brave Search 결과]\n{'='*60}\n{results['brave']}\n"
        
        combined_result += f"\n💡 두 검색 엔진이 병렬로 실행되어 결과를 취합했습니다."
        
        return combined_result
    
    return parallel_search_tool

