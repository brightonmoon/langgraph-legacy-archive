#!/usr/bin/env python3
"""
Subagent 사용 예제

LangChain Deep Agents의 subagent 기능을 사용하는 예제입니다.
현재 프로젝트의 코드 스타일에 맞춰 구현되었습니다.
"""

import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from deepagent.agent import DeepAgentLibrary
from deepagent.tools import (
    create_brave_search_tool,
    create_research_subagent,
    create_csv_analysis_subagent,
    create_data_collector_subagent,
    create_report_writer_subagent
)

# 환경변수 로드
load_dotenv()


def example_1_basic_research_subagent():
    """예제 1: 기본 연구 서브에이전트 사용
    
    LangChain 문서의 예제를 현재 프로젝트 스타일에 맞게 변환한 예제입니다.
    """
    print("=" * 60)
    print("예제 1: 기본 연구 서브에이전트 사용")
    print("=" * 60)
    
    # 연구 서브에이전트 생성 (헬퍼 함수 사용)
    research_subagent = create_research_subagent()
    
    if not research_subagent:
        print("⚠️ 연구 서브에이전트를 생성할 수 없습니다.")
        print("   BRAVE_API_KEY를 확인하세요.")
        return
    
    # 에이전트 생성 (subagents 파라미터 사용)
    agent = DeepAgentLibrary(
        model="anthropic:claude-sonnet-4-5-20250929",  # 또는 None으로 자동 결정
        subagents=[research_subagent],
        system_prompt="""당신은 작업을 조율하는 메인 에이전트입니다.
        
복잡한 연구 작업이 필요한 경우, research-agent 서브에이전트에게 위임하세요.
task(name="research-agent", task="연구할 내용") 형식으로 위임할 수 있습니다."""
    )
    
    # 쿼리 실행
    query = "최신 AI 트렌드에 대해 조사해주세요. research-agent 서브에이전트를 활용하세요."
    print(f"\n📝 쿼리: {query}\n")
    
    result = agent.invoke(query)
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
    elif result.get("messages"):
        response = result["messages"][-1].content
        print(f"✅ 응답:\n{response}\n")


def example_2_langchain_docs_style():
    """예제 2: LangChain 문서 스타일 직접 구현
    
    LangChain 문서의 예제 코드를 그대로 사용하는 방식입니다.
    """
    print("\n" + "=" * 60)
    print("예제 2: LangChain 문서 스타일 직접 구현")
    print("=" * 60)
    
    # Tavily 검색 도구 생성 (LangChain 문서 예제와 동일)
    try:
        from tavily import TavilyClient
        from typing import Literal
        
        tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
        
        def internet_search(
            query: str,
            max_results: int = 5,
            topic: Literal["general", "news", "finance"] = "general",
            include_raw_content: bool = False,
        ):
            """웹 검색 실행"""
            return tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
        
        # LangChain 문서 스타일로 subagent 정의
        research_subagent = {
            "name": "research-agent",
            "description": "웹 검색을 통한 심층 연구 작업을 수행합니다. 복잡한 연구 질문이나 여러 검색이 필요한 경우 이 서브에이전트를 사용하세요.",
            "system_prompt": """당신은 전문 연구원입니다. 웹 검색을 통해 정보를 수집하고 종합적인 보고서를 작성합니다.

**작업 절차:**
1. 연구 질문을 검색 가능한 쿼리로 분해하세요
2. internet_search 도구를 사용하여 관련 정보를 수집하세요
3. 수집한 정보를 종합하여 간결한 요약을 작성하세요
4. 출처를 명시하세요

**출력 형식:**
- 요약 (2-3 문단)
- 주요 발견사항 (불릿 포인트)
- 출처 (URL 포함)

**중요:** 응답은 500단어 이하로 유지하여 컨텍스트를 깨끗하게 유지하세요.""",
            "tools": [internet_search],
            "model": "openai:gpt-4o",  # 서브에이전트용 모델 (선택사항)
        }
        
        # 에이전트 생성
        agent = DeepAgentLibrary(
            model="anthropic:claude-sonnet-4-5-20250929",
            subagents=[research_subagent]
        )
        
        # 쿼리 실행
        query = "양자 컴퓨팅의 최신 동향에 대해 조사해주세요."
        print(f"\n📝 쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
        elif result.get("messages"):
            response = result["messages"][-1].content
            print(f"✅ 응답:\n{response[:500]}...\n")  # 처음 500자만 표시
            
    except ImportError:
        print("⚠️ Tavily 패키지가 설치되지 않았습니다.")
        print("   pip install tavily-python 또는 uv add tavily-python")
    except KeyError:
        print("⚠️ TAVILY_API_KEY가 설정되지 않았습니다.")


def example_3_multiple_specialized_subagents():
    """예제 3: 여러 전문 서브에이전트 사용
    
    데이터 수집 → 분석 → 보고서 작성의 파이프라인을 구성합니다.
    """
    print("\n" + "=" * 60)
    print("예제 3: 여러 전문 서브에이전트 사용")
    print("=" * 60)
    
    # 여러 서브에이전트 생성
    subagents = []
    
    # 1. 데이터 수집 서브에이전트
    data_collector = create_data_collector_subagent()
    if data_collector:
        subagents.append(data_collector)
    
    # 2. CSV 분석 서브에이전트
    csv_analyzer = create_csv_analysis_subagent()
    if csv_analyzer:
        subagents.append(csv_analyzer)
    
    # 3. 보고서 작성 서브에이전트
    report_writer = create_report_writer_subagent()
    if report_writer:
        subagents.append(report_writer)
    
    if not subagents:
        print("⚠️ 서브에이전트를 생성할 수 없습니다.")
        return
    
    # 에이전트 생성
    agent = DeepAgentLibrary(
        model="anthropic:claude-sonnet-4-5-20250929",
        subagents=subagents,
        system_prompt="""당신은 작업을 조율하는 메인 에이전트입니다.

**서브에이전트 활용:**
- data-collector: 데이터 수집 작업 위임
- csv-analyzer: CSV 파일 분석 작업 위임
- report-writer: 보고서 작성 작업 위임

복잡한 작업은 적절한 서브에이전트에게 위임하여 컨텍스트를 깨끗하게 유지하세요."""
    )
    
    # 쿼리 실행
    query = """다음 작업을 수행하세요:
1. data-collector를 사용하여 AI 트렌드 데이터를 수집하세요
2. 수집한 데이터를 바탕으로 report-writer가 보고서를 작성하세요"""
    
    print(f"\n📝 쿼리: {query}\n")
    
    result = agent.invoke(query)
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
    elif result.get("messages"):
        response = result["messages"][-1].content
        print(f"✅ 응답:\n{response[:500]}...\n")  # 처음 500자만 표시


def example_4_custom_subagent():
    """예제 4: 커스텀 서브에이전트 정의
    
    프로젝트에 맞는 커스텀 서브에이전트를 직접 정의합니다.
    """
    print("\n" + "=" * 60)
    print("예제 4: 커스텀 서브에이전트 정의")
    print("=" * 60)
    
    # 커스텀 도구 정의
    from langchain.tools import tool
    
    @tool("calculate")
    def calculator_tool(expression: str) -> str:
        """수학 계산을 수행합니다."""
        try:
            allowed_chars = set("0123456789+-*/(). ")
            if not all(c in allowed_chars for c in expression):
                return "❌ 허용되지 않은 문자가 포함되어 있습니다."
            result = eval(expression)
            return f"결과: {result}"
        except Exception as e:
            return f"❌ 계산 오류: {str(e)}"
    
    # 커스텀 서브에이전트 정의
    math_subagent = {
        "name": "math-solver",
        "description": "수학 문제를 해결합니다. 복잡한 계산이나 수식 분석이 필요한 경우 이 서브에이전트를 사용하세요.",
        "system_prompt": """당신은 수학 전문가입니다. 수학 문제를 해결하고 계산을 수행합니다.

**작업 절차:**
1. 수학 문제를 분석하세요
2. calculate 도구를 사용하여 계산을 수행하세요
3. 결과를 명확하게 설명하세요

**출력 형식:**
- 문제 분석
- 계산 과정
- 최종 결과

**중요:** 응답은 300단어 이하로 유지하세요.""",
        "tools": [calculator_tool],
        "model": None  # 메인 에이전트 모델 사용
    }
    
    # 에이전트 생성
    agent = DeepAgentLibrary(
        model="anthropic:claude-sonnet-4-5-20250929",
        subagents=[math_subagent]
    )
    
    # 쿼리 실행
    query = "복잡한 수학 계산을 수행해주세요: (123 + 456) * 789 / 100"
    print(f"\n📝 쿼리: {query}\n")
    
    result = agent.invoke(query)
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
    elif result.get("messages"):
        response = result["messages"][-1].content
        print(f"✅ 응답:\n{response}\n")


def main():
    """메인 함수"""
    print("\n🚀 Subagent 사용 예제 시작\n")
    
    examples = [
        ("기본 연구 서브에이전트", example_1_basic_research_subagent),
        ("LangChain 문서 스타일", example_2_langchain_docs_style),
        ("여러 전문 서브에이전트", example_3_multiple_specialized_subagents),
        ("커스텀 서브에이전트", example_4_custom_subagent),
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ {name} 예제 실행 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 모든 예제 실행 완료")
    print("=" * 60)
    print("\n💡 참고:")
    print("   - Subagent는 컨텍스트 격리를 통해 메인 에이전트의 컨텍스트를 깨끗하게 유지합니다")
    print("   - 복잡한 작업은 적절한 서브에이전트에게 위임하세요")
    print("   - 각 서브에이전트는 전문적인 작업에 집중할 수 있습니다")


if __name__ == "__main__":
    main()




