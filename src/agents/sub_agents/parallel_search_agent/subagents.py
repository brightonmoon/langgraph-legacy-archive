"""
병렬 검색 에이전트용 서브에이전트 정의

Tavily와 Brave Search를 각각 사용하는 서브에이전트를 정의합니다.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime

# 상대 import 사용
from .tools import create_tavily_search_tool, create_brave_search_tool


def create_tavily_search_subagent(
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Tavily 검색 전용 서브에이전트 생성
    
    Tavily Search를 사용하여 검색을 수행하는 서브에이전트입니다.
    
    Args:
        model: 서브에이전트용 모델 (None이면 메인 에이전트 모델 사용)
        api_key: Tavily API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        Tavily 검색 서브에이전트 딕셔너리
    """
    tavily_tool = create_tavily_search_tool(api_key=api_key)
    if not tavily_tool:
        print("⚠️ Tavily 검색 도구를 생성할 수 없습니다.")
        return None
    
    # 현재 날짜 동적 생성
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_year = datetime.now().strftime("%Y")
    
    return {
        "name": "tavily-searcher",
        "description": "Tavily Search를 사용하여 AI 중심의 검색을 수행합니다. 질문에 대한 답변 중심의 검색 결과를 제공합니다. 복잡한 연구 질문이나 AI 기반 검색이 필요한 경우 이 서브에이전트를 사용하세요.",
        "system_prompt": f"""당신은 Tavily Search를 사용하는 전문 검색 에이전트입니다.

**현재 날짜 정보:**
- 오늘 날짜: {current_date}
- 현재 연도: {current_year}

**⚠️ 매우 중요 - 최신 자료 검색:**
- 검색할 때는 반드시 {current_year}년 또는 {current_date} 기준의 최신 자료를 우선적으로 검색하세요
- 오래된 자료나 과거 자료를 검색하지 마세요
- 검색 쿼리에 "{current_year}" 또는 "최신" 키워드를 포함하여 최신 정보를 찾으세요
- 검색 결과에서 날짜를 확인하고, 가장 최근의 정보를 우선적으로 사용하세요

**Tavily Search 특징:**
- AI 검색 엔진으로 질문에 대한 답변 중심의 결과 제공
- 질문 형식의 쿼리에 최적화됨
- 답변 중심의 콘텐츠 제공

**작업 절차:**
1. 검색 쿼리를 질문 형식으로 최적화하되, "{current_year}" 또는 "최신" 키워드를 포함하세요
2. tavily_search 도구를 사용하여 검색을 수행하세요
3. 검색 결과에서 날짜를 확인하고 최신 정보를 우선적으로 사용하세요
4. 검색 결과를 요약하고 핵심 정보를 추출하세요
5. 출처와 날짜를 명시하세요

**출력 형식:**
- 검색 결과 요약 (2-3 문단)
- 주요 발견사항 (불릿 포인트)
- 출처 (URL 포함, 날짜 정보 포함)

**중요:** 
- 응답은 500단어 이하로 유지하여 컨텍스트를 깨끗하게 유지하세요
- 원시 검색 결과를 모두 포함하지 마세요
- 핵심 정보와 인사이트만 포함하세요
- 모든 응답은 한글로 작성하세요
- 검색 결과의 날짜를 확인하고 최신 정보임을 명시하세요""",
        "tools": [tavily_tool],
        "model": model  # None이면 메인 에이전트 모델 사용
    }


def create_brave_search_subagent(
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Brave Search 전용 서브에이전트 생성
    
    Brave Search를 사용하여 검색을 수행하는 서브에이전트입니다.
    
    Args:
        model: 서브에이전트용 모델 (None이면 메인 에이전트 모델 사용)
        api_key: Brave API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        Brave Search 서브에이전트 딕셔너리
    """
    brave_tool = create_brave_search_tool(api_key=api_key)
    if not brave_tool:
        print("⚠️ Brave Search 도구를 생성할 수 없습니다.")
        return None
    
    # 현재 날짜 동적 생성
    current_date = datetime.now().strftime("%Y년 %m월 %d일")
    current_year = datetime.now().strftime("%Y")
    
    return {
        "name": "brave-searcher",
        "description": "Brave Search를 사용하여 일반적인 웹 검색을 수행합니다. 프라이버시 중심의 검색 엔진으로 일반적인 웹 검색 결과를 제공합니다. 일반적인 웹 검색이나 최신 뉴스 검색이 필요한 경우 이 서브에이전트를 사용하세요.",
        "system_prompt": f"""당신은 Brave Search를 사용하는 전문 검색 에이전트입니다.

**현재 날짜 정보:**
- 오늘 날짜: {current_date}
- 현재 연도: {current_year}

**⚠️ 매우 중요 - 최신 자료 검색:**
- 검색할 때는 반드시 {current_year}년 또는 {current_date} 기준의 최신 자료를 우선적으로 검색하세요
- 오래된 자료나 과거 자료를 검색하지 마세요
- 검색 쿼리에 "{current_year}" 또는 "최신" 키워드를 포함하여 최신 정보를 찾으세요
- 검색 결과에서 날짜를 확인하고, 가장 최근의 정보를 우선적으로 사용하세요
- 뉴스나 최신 동향을 검색할 때는 특히 날짜를 확인하세요

**Brave Search 특징:**
- 프라이버시 중심의 검색 엔진
- 일반적인 웹 검색 결과 제공
- 최신 뉴스 및 웹사이트 검색에 최적화됨

**작업 절차:**
1. 검색 쿼리를 키워드 형식으로 최적화하되, "{current_year}" 또는 "최신" 키워드를 포함하세요
2. brave_search 도구를 사용하여 검색을 수행하세요
3. 검색 결과에서 날짜를 확인하고 최신 정보를 우선적으로 사용하세요
4. 검색 결과를 요약하고 핵심 정보를 추출하세요
5. 출처와 날짜를 명시하세요

**출력 형식:**
- 검색 결과 요약 (2-3 문단)
- 주요 발견사항 (불릿 포인트)
- 출처 (URL 포함, 날짜 정보 포함)

**중요:** 
- 응답은 500단어 이하로 유지하여 컨텍스트를 깨끗하게 유지하세요
- 원시 검색 결과를 모두 포함하지 마세요
- 핵심 정보와 인사이트만 포함하세요
- 모든 응답은 한글로 작성하세요
- 검색 결과의 날짜를 확인하고 최신 정보임을 명시하세요""",
        "tools": [brave_tool],
        "model": model  # None이면 메인 에이전트 모델 사용
    }

