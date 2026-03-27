"""
Agent 팩토리 모듈 - Agent 생성 및 관리
"""

import logging
from typing import Dict, Type
from .base import BaseAgent
from .study.basic_agent import BasicAgent
from .study.langgraph_agent import LangGraphAgent
from .study.langgraph_agent_tools import LangGraphAgentTools
from .study.langgraph_agent_mcp import LangGraphAgentMCP
from .study.langgraph_agent_tools_middleware import LangGraphAgentToolsMiddleware
from .study.langgraph_agent_chaining import LangGraphAgentChaining
from .study.langgraph_agent_parallel import LangGraphAgentParallel
from .study.coding_agent import CodingAgent
from .study.multiple_workers_coding_agent import MultipleWorkersCodingAgent
from .agent import OrchestratorAgent

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent 생성 팩토리 클래스"""

    @classmethod
    def _get_registry(cls) -> Dict[str, Type[BaseAgent]]:
        """Agent 레지스트리 반환 (매번 새 딕셔너리 반환하여 mutation 방지)"""
        return {
            "basic": BasicAgent,
            "langgraph": LangGraphAgent,
            "langgraph_tools": LangGraphAgentTools,
            "langgraph_mcp": LangGraphAgentMCP,
            "langgraph_tools_middleware": LangGraphAgentToolsMiddleware,
            "langgraph_chaining": LangGraphAgentChaining,
            "langgraph_parallel": LangGraphAgentParallel,
            "coding": CodingAgent,
            "multiple_workers_coding": MultipleWorkersCodingAgent,
            "orchestrator": OrchestratorAgent,
        }
    
    @classmethod
    def create_agent(cls, agent_type: str, model_name: str = None) -> BaseAgent:
        """지정된 타입의 Agent 생성

        Args:
            agent_type: Agent 타입 ("deep"은 더 이상 지원하지 않음 - "orchestrator" 사용 권장)
            model_name: 사용할 모델명 (None이면 기본값 사용)
        """
        # 레거시 "deep" 타입 지원 (orchestrator로 리다이렉트)
        if agent_type == "deep":
            logger.warning("⚠️  'deep' 타입은 더 이상 지원하지 않습니다. 'orchestrator' 타입으로 자동 전환합니다.")
            agent_type = "orchestrator"

        registry = cls._get_registry()
        if agent_type not in registry:
            raise ValueError(
                f"지원하지 않는 Agent 타입: {agent_type}\n"
                f"사용 가능한 타입: {', '.join(registry.keys())}"
            )

        # 모델명이 지정된 경우에만 전달
        if model_name:
            # OrchestratorAgent는 orchestrator_model 파라미터 사용
            if agent_type == "orchestrator":
                return registry[agent_type](orchestrator_model=model_name)
            else:
                return registry[agent_type](model_name=model_name)
        else:
            return registry[agent_type]()
    
    
    @classmethod
    def get_available_agents(cls) -> list:
        """사용 가능한 Agent 타입 목록 반환"""
        return list(cls._get_registry().keys())
    
    @classmethod
    def get_agent_info(cls, agent_type: str) -> dict:
        """Agent 타입에 대한 정보 반환"""
        registry = cls._get_registry()
        if agent_type not in registry:
            return {"error": f"지원하지 않는 Agent 타입: {agent_type}"}

        agent_class = registry[agent_type]
        return {
            "type": agent_type,
            "class": agent_class.__name__,
            "module": agent_class.__module__,
            "description": agent_class.__doc__ or "Agent 클래스"
        }
