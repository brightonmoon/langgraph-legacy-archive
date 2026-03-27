"""
Worker 팩토리 및 헬퍼 모듈

작업 복잡도에 따라 적절한 Worker를 생성합니다.
- 복잡한 워크플로우 패턴 → LangGraph 직접 사용
- Planning + Filesystem + SubAgent 필요 → create_deep_agent()
- 간단한 tool-calling → LangGraph 직접 사용 (또는 create_agent() 선택적)
"""

import logging
import os
from typing import Optional, List, Dict, Any, Literal
from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated

# DeepAgents 관련 import (선택적)
try:
    from deepagents import create_deep_agent
    from deepagents.middleware.subagents import CompiledSubAgent
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    DEEPAGENTS_AVAILABLE = False
    create_deep_agent = None
    CompiledSubAgent = None

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper

logger = logging.getLogger(__name__)


# 간단한 Worker State 정의
class SimpleWorkerState(TypedDict):
    """간단한 Worker의 상태"""
    messages: Annotated[list, add_messages]
    task: str
    result: str
    evaluation_verdict: str  # Latest evaluation result: "accept" or "retry"
    retry_count: int  # Number of retries attempted


class WorkerFactory:
    """Worker 생성 팩토리 - 워크플로우 패턴과 기능 요구사항에 따라 적절한 Worker 선택"""
    
    def create_worker(
        self, 
        worker_type: str = "auto",
        model: Optional[str] = None, 
        tools: Optional[List] = None,
        workflow_pattern: Optional[str] = None,  # "prompt_chaining", "parallel", "evaluator_optimizer", "routing", None
        needs_planning: bool = False,
        needs_filesystem: bool = False,
        needs_subagent: bool = False
    ):
        """Worker 생성
        
        Args:
            worker_type: "auto" (자동 선택), "langgraph" (LangGraph 직접), 
                        "deepagent" (create_deep_agent), "agent" (create_agent - 선택적)
            model: 모델 문자열 (예: "ollama:gpt-oss:120b-cloud", "ollama:qwen2.5-coder:latest")
            tools: 도구 리스트
            workflow_pattern: 복잡한 워크플로우 패턴 (있으면 LangGraph 직접 사용)
            needs_planning: Planning 기능 필요 여부
            needs_filesystem: Filesystem 기능 필요 여부
            needs_subagent: SubAgent 기능 필요 여부
        
        Returns:
            Worker 인스턴스 (CompiledSubAgent 또는 Runnable)
        """
        # 복잡한 워크플로우 패턴이 있으면 LangGraph 직접 사용
        if workflow_pattern or worker_type == "langgraph":
            return self._create_langgraph_worker(
                model, tools, workflow_pattern
            )
        
        # Planning + Filesystem + SubAgent 모두 필요하면 create_deep_agent()
        if needs_planning and needs_filesystem and needs_subagent:
            if not DEEPAGENTS_AVAILABLE:
                raise ImportError(
                    "deepagents 라이브러리가 필요합니다. "
                    "설치: pip install deepagents"
                )
            return self._create_deepagent_worker(model, tools)
        
        # 그 외의 경우: LangGraph 직접 사용 (기본)
        if worker_type == "agent":
            # 선택적: 간단한 tool-calling만 필요한 경우
            # 하지만 LangGraph 직접 사용이 더 유연하므로 기본값으로 사용
            return self._create_langgraph_worker(model, tools, None)
        else:
            # 기본: LangGraph 직접 사용 (더 유연함)
            return self._create_langgraph_worker(model, tools, None)
    
    def _create_langgraph_worker(
        self, 
        model: Optional[str], 
        tools: Optional[List], 
        pattern: Optional[str] = None
    ):
        """LangGraph를 직접 사용하여 Worker 생성 - 복잡한 워크플로우 패턴 지원"""
        from langchain.messages import SystemMessage, HumanMessage
        
        # 모델 초기화
        if model is None:
            model = os.getenv("OLLAMA_MODEL_NAME", "ollama:qwen2.5-coder:latest")
        
        # Add ollama: prefix only if no known prefix is present
        known_prefixes = ("ollama:", "anthropic:", "openai:")
        if not any(model.startswith(prefix) for prefix in known_prefixes):
            model = f"ollama:{model}"
        
        chat_model = init_chat_model_helper(
            model_name=model,
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        
        if not chat_model:
            raise ValueError(f"모델 초기화 실패: {model}")

        # Bind tools to the model if provided
        if tools:
            chat_model = chat_model.bind_tools(tools)

        # 워크플로우 패턴에 따라 구성
        if pattern == "prompt_chaining":
            # Prompt Chaining 패턴
            workflow = StateGraph(SimpleWorkerState)
            
            def step1_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """첫 번째 단계"""
                messages = [SystemMessage(content="작업의 첫 번째 단계를 수행하세요.")]
                if state.get("task"):
                    messages.append(HumanMessage(content=state["task"]))
                response = chat_model.invoke(messages)
                return {"result": response.content if hasattr(response, 'content') else str(response)}
            
            def step2_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """두 번째 단계 (첫 번째 결과 기반)"""
                messages = [
                    SystemMessage(content="첫 번째 단계의 결과를 기반으로 두 번째 단계를 수행하세요."),
                    HumanMessage(content=f"첫 번째 결과: {state.get('result', '')}\n\n원래 작업: {state.get('task', '')}")
                ]
                response = chat_model.invoke(messages)
                return {"result": response.content if hasattr(response, 'content') else str(response)}
            
            workflow.add_node("step1", step1_node)
            workflow.add_node("step2", step2_node)
            workflow.add_edge(START, "step1")
            workflow.add_edge("step1", "step2")
            workflow.add_edge("step2", END)
        
        elif pattern == "parallel":
            # Parallelization 패턴
            workflow = StateGraph(SimpleWorkerState)
            
            def parallel_task1(state: SimpleWorkerState) -> SimpleWorkerState:
                """병렬 작업 1"""
                messages = [SystemMessage(content="작업 1을 수행하세요."), HumanMessage(content=state.get("task", ""))]
                response = chat_model.invoke(messages)
                return {"result": f"Task1: {response.content if hasattr(response, 'content') else str(response)}"}
            
            def parallel_task2(state: SimpleWorkerState) -> SimpleWorkerState:
                """병렬 작업 2"""
                messages = [SystemMessage(content="작업 2를 수행하세요."), HumanMessage(content=state.get("task", ""))]
                response = chat_model.invoke(messages)
                return {"result": f"Task2: {response.content if hasattr(response, 'content') else str(response)}"}
            
            def aggregator_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """결과 통합"""
                # 두 작업의 결과를 통합 (간단한 예시)
                result = state.get("result", "")
                return {"result": f"통합 결과: {result}"}
            
            workflow.add_node("task1", parallel_task1)
            workflow.add_node("task2", parallel_task2)
            workflow.add_node("aggregator", aggregator_node)
            workflow.add_edge(START, "task1")
            workflow.add_edge(START, "task2")
            workflow.add_edge("task1", "aggregator")
            workflow.add_edge("task2", "aggregator")
            workflow.add_edge("aggregator", END)
        
        elif pattern == "evaluator_optimizer":
            # Evaluator-Optimizer 패턴
            workflow = StateGraph(SimpleWorkerState)
            
            def generator_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """생성 노드"""
                messages = [SystemMessage(content="작업을 수행하세요."), HumanMessage(content=state.get("task", ""))]
                response = chat_model.invoke(messages)
                # Increment retry count when re-entering generator
                current_retry = state.get("retry_count", 0)
                new_retry = current_retry + 1 if state.get("evaluation_verdict") == "retry" else current_retry
                return {
                    "result": response.content if hasattr(response, 'content') else str(response),
                    "retry_count": new_retry
                }
            
            def evaluator_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """평가 노드"""
                messages = [
                    SystemMessage(content="작업 결과를 평가하고 'accept' 또는 'retry' 중 하나만 답하세요."),
                    HumanMessage(content=f"작업: {state.get('task', '')}\n\n결과: {state.get('result', '')}")
                ]
                response = chat_model.invoke(messages)
                evaluation = response.content.lower() if hasattr(response, 'content') else str(response).lower()
                # Store verdict in separate field to avoid accumulation
                verdict = "retry" if "retry" in evaluation else "accept"
                return {"evaluation_verdict": verdict}
            
            def route_based_on_evaluation(state: SimpleWorkerState) -> Literal["retry", "accept"]:
                """평가 결과에 따른 라우팅 (최대 3회 재시도)"""
                max_retries = 3
                retry_count = state.get("retry_count", 0)
                verdict = state.get("evaluation_verdict", "accept")

                # Max retries exceeded - always accept
                if retry_count >= max_retries:
                    return "accept"

                # Check verdict and increment retry count if needed
                if verdict == "retry":
                    return "retry"
                return "accept"
            
            workflow.add_node("generator", generator_node)
            workflow.add_node("evaluator", evaluator_node)
            workflow.add_edge(START, "generator")
            workflow.add_edge("generator", "evaluator")
            workflow.add_conditional_edges(
                "evaluator",
                route_based_on_evaluation,
                {"retry": "generator", "accept": END}
            )
        
        else:
            # 기본: 간단한 워크플로우
            workflow = StateGraph(SimpleWorkerState)
            
            def process_task_node(state: SimpleWorkerState) -> SimpleWorkerState:
                """작업 처리 노드"""
                messages = [SystemMessage(content="주어진 작업을 정확하고 효율적으로 수행하세요.")]
                if state.get("task"):
                    messages.append(HumanMessage(content=state["task"]))
                
                response = chat_model.invoke(messages)
                result = response.content if hasattr(response, 'content') else str(response)
                return {"result": result}
            
            workflow.add_node("process", process_task_node)
            workflow.add_edge(START, "process")
            workflow.add_edge("process", END)
        
        compiled_graph = workflow.compile()
        
        # 참고: CompiledSubAgent는 dict 타입이며, runnable 속성에 실제 그래프가 있음
        # 하지만 LangGraph Worker는 직접 compiled_graph를 반환하는 것이 더 간단함
        # CompiledSubAgent는 deepagents의 create_deep_agent 내부에서 subagents로 사용될 때만 필요
        
        # compiled_graph 자체가 Runnable이므로 직접 반환
        logger.info(f"   ✅ CompiledStateGraph 반환 (타입: {type(compiled_graph).__name__})")
        return compiled_graph
    
    def _create_deepagent_worker(self, model: Optional[str], tools: Optional[List]):
        """create_deep_agent()로 DeepAgent Worker 생성 - Planning + Filesystem + SubAgent 필요"""
        if not DEEPAGENTS_AVAILABLE:
            raise ImportError(
                "deepagents 라이브러리가 필요합니다. "
                "설치: pip install deepagents"
            )
        
        # 모델 설정
        if model is None:
            model = os.getenv("OLLAMA_MODEL_NAME", "ollama:qwen2.5-coder:latest")
        
        # ChatOllama 또는 init_chat_model 사용
        if model.startswith("ollama:"):
            # 로컬 Ollama 모델인 경우 ChatOllama 직접 사용 (API 키 불필요)
            model_name = model.replace("ollama:", "")
            chat_model = ChatOllama(model=model_name, temperature=0.7)
        else:
            # Cloud 모델인 경우 init_chat_model 사용
            chat_model = init_chat_model_helper(
                model_name=model,
                api_key=os.getenv("OLLAMA_API_KEY"),
                temperature=0.7
            )
            if not chat_model:
                raise ValueError(f"모델 초기화 실패: {model}")
        
        # create_deep_agent는 subagents 파라미터를 선택적으로 받을 수 있음
        # subagents는 dictionary 리스트 또는 CompiledSubAgent 객체 리스트여야 함
        # 현재는 기본 general-purpose subagent만 사용
        # 향후 특정 서브에이전트가 필요하면 subagents 파라미터 추가 가능
        
        try:
            deep_agent = create_deep_agent(
                model=chat_model,
                tools=tools or [],
                system_prompt="""당신은 전문 Worker입니다. 
주어진 작업을 계획하고 단계별로 수행하세요. 
필요시 파일 시스템을 사용하여 중간 결과를 저장하고, 
서브에이전트를 활용하세요."""
                # subagents 파라미터는 선택적 - 필요시 추가
                # subagents=[
                #     {
                #         "name": "specialized-worker",
                #         "description": "특정 작업을 수행하는 전문 Worker",
                #         "system_prompt": "...",
                #         "tools": [...]
                #     }
                # ]
            )
            
            # create_deep_agent()는 LangGraph Runnable을 반환해야 함
            if not hasattr(deep_agent, 'invoke'):
                raise ValueError(f"create_deep_agent()가 Runnable을 반환하지 않았습니다. 타입: {type(deep_agent)}")
            
            logger.info(f"   ✅ DeepAgent Worker 생성 완료 (타입: {type(deep_agent).__name__})")
            return deep_agent
            
        except Exception as e:
            raise ValueError(f"DeepAgent Worker 생성 실패: {str(e)}")

