"""
병렬 검색 에이전트

Tavily와 Brave Search를 병렬로 사용하여 검색 결과를 취합하고 보고서를 작성하는 에이전트입니다.
"""

from .agent import ParallelSearchAgent, create_parallel_search_agent_graph
from .tools import create_tavily_search_tool, create_brave_search_tool, create_parallel_search_tool
from .subagents import create_tavily_search_subagent, create_brave_search_subagent

__all__ = [
    "ParallelSearchAgent",
    "create_parallel_search_agent_graph",
    "create_tavily_search_tool",
    "create_brave_search_tool",
    "create_parallel_search_tool",
    "create_tavily_search_subagent",
    "create_brave_search_subagent",
]

# LangGraph Studio용 agent 변수 (lazy initialization)
try:
    from .agent import agent
except Exception:
    agent = None

