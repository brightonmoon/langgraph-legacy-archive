#!/usr/bin/env python3
"""DeepAgent Subagents 사용 예제

각 subagent가 다른 프롬프트와 도구를 사용하는 예제를 보여줍니다.
"""
import sys
from dotenv import load_dotenv

from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_success,
    print_error,
    print_warning,
    print_info,
)

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

load_dotenv()


def internet_search_tool(query: str, max_results: int = 5):
    """웹 검색 도구 (예시)"""
    return f"검색 결과: {query} ({max_results}개 결과)"


def data_analysis_tool(data: str):
    """데이터 분석 도구 (예시)"""
    return f"데이터 분석 결과: {data}"


def code_generation_tool(requirement: str):
    """코드 생성 도구 (예시)"""
    return f"생성된 코드: {requirement}"


def example_1_dict_subagents():
    """예제 1: Dictionary 기반 Subagents 사용"""
    print_header("예제 1: Dictionary 기반 Subagents")

    chat_model = init_chat_model("anthropic:claude-sonnet-4-20250514")

    research_subagent = {
        "name": "research-agent",
        "description": "웹 검색 및 리서치를 수행하는 전문가",
        "system_prompt": """당신은 전문 연구원입니다.
        웹 검색을 통해 정보를 수집하고, 신뢰할 수 있는 소스에서
        정확한 정보를 찾아 정리된 보고서를 작성하세요.""",
        "tools": [internet_search_tool],
        "model": "openai:gpt-4o",
    }

    data_analyst_subagent = {
        "name": "data-analyst",
        "description": "데이터 분석 및 통계 처리 전문가",
        "system_prompt": """당신은 데이터 분석 전문가입니다.
        데이터를 분석하고, 통계적 인사이트를 도출하며,
        시각화와 보고서를 작성하세요.""",
        "tools": [data_analysis_tool],
    }

    coder_subagent = {
        "name": "code-generator",
        "description": "코드 생성 및 개발 작업 전문가",
        "system_prompt": """당신은 고급 소프트웨어 엔지니어입니다.
        요구사항을 분석하고, 효율적이고 유지보수 가능한 코드를 작성하세요.
        코드 리뷰와 테스트도 수행하세요.""",
        "tools": [code_generation_tool],
        "model": "qwen2.5-coder:latest",
    }

    subagents = [research_subagent, data_analyst_subagent, coder_subagent]

    agent = create_deep_agent(
        model=chat_model,
        tools=[],
        system_prompt="당신은 작업을 분석하고 적절한 서브에이전트에게 위임하는 관리자입니다.",
        subagents=subagents,
    )

    print_success("각 subagent가 다른 프롬프트와 도구를 가진 에이전트 생성 완료!")

    print_section("Subagent 정보")
    for subagent in subagents:
        print(f"   - {subagent['name']}: {subagent['description']}")
        print(f"     프롬프트: {subagent['system_prompt'][:50]}...")
        print(f"     도구: {len(subagent['tools'])}개")
        if "model" in subagent:
            print(f"     모델: {subagent['model']}")
        print()

    return agent


def example_2_custom_graph_subagents():
    """예제 2: CompiledSubAgent를 사용한 커스텀 그래프"""
    print_section("예제 2: CompiledSubAgent 기반 커스텀 그래프")

    try:
        from deepagents import CompiledSubAgent
        from langgraph.prebuilt import create_agent_supervisor

        chat_model = init_chat_model("anthropic:claude-sonnet-4-20250514")

        custom_data_analyzer = create_agent_supervisor(
            model=chat_model,
            tools=[data_analysis_tool],
            system_prompt="전문 데이터 분석가입니다. 데이터를 깊이 있게 분석하세요.",
        )

        custom_coder = create_agent_supervisor(
            model=chat_model,
            tools=[code_generation_tool],
            system_prompt="전문 소프트웨어 엔지니어입니다. 효율적인 코드를 작성하세요.",
        )

        data_analyzer_subagent = CompiledSubAgent(
            name="custom-data-analyzer",
            description="복잡한 데이터 분석을 수행하는 커스텀 에이전트",
            runnable=custom_data_analyzer,
        )

        coder_subagent = CompiledSubAgent(
            name="custom-code-generator",
            description="복잡한 코드 생성 작업을 수행하는 커스텀 에이전트",
            runnable=custom_coder,
        )

        subagents = [data_analyzer_subagent, coder_subagent]

        agent = create_deep_agent(
            model=chat_model,
            tools=[],
            system_prompt="작업을 분석하고 적절한 커스텀 서브에이전트에게 위임하세요.",
            subagents=subagents,
        )

        print_success("커스텀 그래프를 사용한 subagent 생성 완료!")

        print_section("커스텀 Subagent 정보", level=2)
        for subagent in subagents:
            print(f"   - {subagent.name}: {subagent.description}")
            print(f"     타입: {type(subagent.runnable).__name__}")
            print()

        return agent

    except ImportError as e:
        print_warning(f"Import 오류: {e}")
        print("   CompiledSubAgent를 사용하려면 추가 패키지가 필요할 수 있습니다.")
        return None


def example_3_mixed_approach():
    """예제 3: Dictionary와 CompiledSubAgent 혼합 사용"""
    print_section("예제 3: Dictionary와 CompiledSubAgent 혼합")

    chat_model = init_chat_model("anthropic:claude-sonnet-4-20250514")

    research_subagent = {
        "name": "research-agent",
        "description": "웹 검색 전문가",
        "system_prompt": "웹 검색을 통해 정보를 수집하세요.",
        "tools": [internet_search_tool],
    }

    subagents = [research_subagent]

    agent = create_deep_agent(
        model=chat_model,
        tools=[],
        system_prompt="작업을 분석하고 적절한 서브에이전트에게 위임하세요.",
        subagents=subagents,
    )

    print_success("Dictionary 기반 subagent 생성 완료!")
    return agent


def main():
    """DeepAgent Subagents 예제"""
    print_header("DeepAgent Subagents 예제")

    try:
        agent1 = example_1_dict_subagents()
        agent2 = example_2_custom_graph_subagents()
        agent3 = example_3_mixed_approach()

        print_section("결과")
        print_success("모든 예제 실행 완료!")

        print_info("핵심 포인트:")
        print("   1. 각 subagent는 독립적인 프롬프트를 가질 수 있습니다")
        print("   2. 각 subagent는 독립적인 도구 집합을 가질 수 있습니다")
        print("   3. 각 subagent는 다른 모델을 사용할 수 있습니다")
        print("   4. Dictionary 방식과 CompiledSubAgent 방식을 혼합 사용 가능합니다")
        print("   5. 메인 에이전트와 subagent는 서로 다른 설정을 가질 수 있습니다")

        return 0

    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
