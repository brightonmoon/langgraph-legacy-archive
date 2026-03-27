"""
상위 에이전트 - 서브 에이전트 및 Worker 조율 및 라우팅

이 에이전트는 사용자 요청을 분석하고 적절한 서브 에이전트 또는 Worker에게 작업을 위임하여
최종 결과를 생성하는 상위 LLM 에이전트입니다.

두 가지 라우팅 모드 지원:
1. 서브 에이전트 기반: 특정 서브 에이전트로 직접 라우팅
2. Worker 기반: Worker 팩토리를 통해 복잡한 워크플로우 패턴 지원
"""

import os
import json
import logging
import re
import threading
from typing import TypedDict, Annotated, Dict, Any, Optional, Literal
from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from src.utils.errors import (
    AgentError,
    format_error_message,
    format_error_for_state,
    increment_error_count
)
from .prompts import (
    create_main_agent_user_prompt,
    TASK_ANALYSIS_SYSTEM_PROMPT,
    create_task_analysis_user_prompt,
    RESULT_SYNTHESIS_SYSTEM_PROMPT,
    create_result_synthesis_user_prompt,
)

# 서브 에이전트 import
from .sub_agents.csv_data_analysis_agent import agent as csv_data_analysis_agent
from .sub_agents.parallel_search_agent import agent as parallel_search_agent
from .sub_agents.report_generation_agent import agent as report_generation_agent

# Worker 팩토리 import
from .worker import WorkerFactory

# BaseAgent import (OrchestratorAgent 클래스용)
from .base import BaseAgent

logger = logging.getLogger(__name__)

load_dotenv()
setup_langsmith_disabled()


class MainAgentState(MessagesState, total=False):
    """상위 에이전트의 상태"""
    task_type: Optional[str]  # 작업 유형 (csv_analysis, report_generation, other)
    task_analysis: Optional[Dict[str, Any]]  # 작업 분석 결과
    routing_mode: Optional[str]  # 라우팅 모드 ("subagent" 또는 "worker")
    subagent_name: Optional[str]  # 선택된 서브 에이전트 이름
    subagent_result: Optional[Dict[str, Any]]  # 서브 에이전트 실행 결과
    worker_requirements: Optional[Dict[str, Any]]  # Worker 요구사항 분석
    worker_result: Optional[Dict[str, Any]]  # Worker 실행 결과
    final_result: Optional[str]  # 최종 통합 결과
    status: Optional[str]  # 현재 상태


def create_main_agent(
    model: str = "ollama:gpt-oss:120b-cloud"
):
    """상위 에이전트 생성

    Args:
        model: 사용할 모델명 (기본값: ollama:gpt-oss:120b-cloud)

    Returns:
        LangGraph CompiledStateGraph
    """
    # 모델 초기화
    model_str = model.strip() if model else os.getenv("OLLAMA_MODEL_NAME", "ollama:gpt-oss:120b-cloud")
    if not model_str.startswith("ollama:") and not model_str.startswith("anthropic:") and not model_str.startswith("openai:"):
        model_str = f"ollama:{model_str}"

    main_model = init_chat_model_helper(
        model_name=model_str,
        api_key=os.getenv("OLLAMA_API_KEY"),
        temperature=0.7
    )

    if not main_model:
        raise ValueError(f"모델 초기화 실패: {model_str}")

    logger.info(f"✅ 상위 에이전트 모델 로드 완료: {model_str}")

    # Worker 팩토리 초기화
    worker_factory = WorkerFactory()

    # 헬퍼 함수들 정의 (노드 함수들보다 먼저)
    def _extract_user_query(messages: list) -> str:
        """메시지 리스트에서 사용자 쿼리 추출"""
        for message in reversed(messages):
            if isinstance(message, dict):
                if message.get("role") == "user" or message.get("type") == "human":
                    return message.get("content", "")
            elif hasattr(message, 'content'):
                return message.content
        return ""

    def _determine_worker_type(
        workflow_pattern: Optional[str],
        needs_planning: bool,
        needs_filesystem: bool,
        needs_subagent: bool
    ) -> str:
        """Worker 타입 결정 로직"""
        # 복잡한 워크플로우 패턴이 있으면 LangGraph 직접 사용
        if workflow_pattern:
            return "langgraph"

        # Planning + Filesystem이 필요하면 deepagent 사용
        if needs_planning and needs_filesystem:
            return "deepagent"

        # 기본: LangGraph 직접 사용
        return "langgraph"

    def _select_worker_model(complexity: str) -> str:
        """작업 복잡도에 따른 Worker 모델 선택"""
        if complexity == "high":
            return os.getenv("OLLAMA_MODEL_NAME", "ollama:gpt-oss:120b-cloud")
        else:
            return "ollama:qwen2.5-coder:latest"

    # 노드 함수들 정의

    def analyze_task_node(state: MainAgentState) -> MainAgentState:
        """작업 분석 노드 - 사용자 요청을 분석하여 작업 유형 결정"""
        logger.info("🔍 [Main Agent] 작업 분석 중...")

        messages = state.get("messages", [])
        if not messages:
            return {
                "status": "error",
                "final_result": "사용자 메시지가 없습니다."
            }

        # 마지막 사용자 메시지 추출
        user_query = _extract_user_query(messages)

        if not user_query:
            return {
                "status": "error",
                "final_result": "사용자 요청을 찾을 수 없습니다."
            }

        # LLM으로 작업 분석
        try:
            response = main_model.invoke([
                SystemMessage(content=TASK_ANALYSIS_SYSTEM_PROMPT),
                HumanMessage(content=create_task_analysis_user_prompt(user_query))
            ])

            response_text = response.content if hasattr(response, 'content') else str(response)

            # JSON 추출
            task_analysis = None
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    task_analysis = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # 폴백: 규칙 기반 분석
            if not task_analysis:
                task_lower = user_query.lower()
                requires_search = any(keyword in task_lower for keyword in ["조사", "검색", "정보", "최신", "트렌드", "동향", "research", "search", "investigate"])
                requires_report = any(keyword in task_lower for keyword in ["보고서", "정리", "요약", "분석", "report", "summary", "analyze"])

                if requires_search and requires_report:
                    task_analysis = {
                        "task_type": "search_and_report",
                        "complexity": "high",
                        "requires_subagent": True,
                        "requires_search": True,
                        "requires_report": True,
                        "subagent_name": None,
                        "workflow_chain": ["parallel_search_agent", "report_generation_agent"],
                        "requires_planning": False,
                        "requires_filesystem": False,
                        "workflow_pattern": None,
                        "parameters": {
                            "query": user_query
                        }
                    }
                elif requires_search:
                    task_analysis = {
                        "task_type": "search",
                        "complexity": "medium",
                        "requires_subagent": True,
                        "requires_search": True,
                        "requires_report": False,
                        "subagent_name": "parallel_search_agent",
                        "workflow_chain": None,
                        "requires_planning": False,
                        "requires_filesystem": False,
                        "workflow_pattern": None,
                        "parameters": {
                            "query": user_query
                        }
                    }
                elif "csv" in task_lower or ".csv" in task_lower:
                    task_analysis = {
                        "task_type": "csv_analysis",
                        "complexity": "medium",
                        "requires_subagent": True,
                        "requires_search": False,
                        "requires_report": False,
                        "subagent_name": "csv_data_analysis_agent",
                        "workflow_chain": None,
                        "requires_planning": False,
                        "requires_filesystem": False,
                        "workflow_pattern": None,
                        "parameters": {
                            "query": user_query
                        }
                    }
                else:
                    task_analysis = {
                        "task_type": "other",
                        "complexity": "medium",
                        "requires_subagent": False,
                        "requires_search": False,
                        "requires_report": False,
                        "subagent_name": None,
                        "workflow_chain": None,
                        "requires_planning": False,
                        "requires_filesystem": False,
                        "workflow_pattern": None,
                        "parameters": {
                            "query": user_query
                        }
                    }

            # Worker 요구사항 결정 (orchestrator.py 로직 통합)
            workflow_pattern = task_analysis.get("workflow_pattern")
            needs_planning = task_analysis.get("requires_planning", False)
            needs_filesystem = task_analysis.get("requires_filesystem", False)
            needs_subagent = task_analysis.get("requires_subagent", False)
            complexity = task_analysis.get("complexity", "medium")

            # 라우팅 모드 결정: 서브 에이전트가 명시적으로 있거나 워크플로우 체인이 있으면 subagent, 아니면 worker
            workflow_chain = task_analysis.get("workflow_chain", [])
            routing_mode = "subagent" if (needs_subagent and (task_analysis.get("subagent_name") or workflow_chain)) else "worker"

            # Worker 요구사항 결정
            worker_requirements = {
                "workflow_pattern": workflow_pattern,
                "needs_planning": needs_planning,
                "needs_filesystem": needs_filesystem,
                "needs_subagent": needs_subagent,
                "complexity": complexity,
                "worker_type": _determine_worker_type(workflow_pattern, needs_planning, needs_filesystem, needs_subagent),
                "worker_model": _select_worker_model(complexity)
            }

            logger.info(f"✅ 작업 분석 완료: {task_analysis.get('task_type', 'unknown')}, 라우팅 모드: {routing_mode}")

            return {
                "task_type": task_analysis.get("task_type", "other"),
                "task_analysis": task_analysis,
                "routing_mode": routing_mode,
                "subagent_name": task_analysis.get("subagent_name"),
                "worker_requirements": worker_requirements,
                "status": "analyzed"
            }
        except Exception as e:
            logger.error(f"❌ 작업 분석 실패: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "final_result": f"작업 분석 중 오류 발생: {str(e)}"
            }

    def _execute_workflow_chain(state: MainAgentState, chain: list) -> MainAgentState:
        """워크플로우 체인 실행 (검색 → 보고서)"""
        logger.info(f"🔗 [Main Agent] 워크플로우 체인 실행: {' → '.join(chain)}")

        messages = state.get("messages", [])
        # 사용자 쿼리 추출
        user_query = _extract_user_query(messages)

        task_analysis = state.get("task_analysis", {})

        try:
            # 1단계: parallel_search_agent 실행
            if "parallel_search_agent" in chain:
                logger.info("🔍 [Step 1] 병렬 검색 에이전트 실행 중...")
                search_state = {
                    "messages": [{"role": "user", "content": user_query}]
                }
                search_result = parallel_search_agent.invoke(search_state)

                # 검색 결과 추출
                search_output = ""
                if "messages" in search_result:
                    search_messages = search_result["messages"]
                    if search_messages:
                        last_msg = search_messages[-1]
                        if hasattr(last_msg, 'content'):
                            search_output = last_msg.content
                        elif isinstance(last_msg, dict):
                            search_output = last_msg.get("content", "")
                if not search_output:
                    search_output = str(search_result)

                logger.info(f"✅ 검색 완료 (결과 길이: {len(search_output)} 문자)")

                # 2단계: report_generation_agent 실행
                if "report_generation_agent" in chain:
                    logger.info("📝 [Step 2] 보고서 생성 에이전트 실행 중...")
                    report_state = {
                        "context": {
                            "search_query": user_query,
                            "search_results": search_output,
                            "source": "parallel_search_agent",
                            "task_analysis": task_analysis
                        },
                        "report_template": None,
                        "additional_instructions": f"다음 검색 결과를 바탕으로 종합 보고서를 작성하세요:\n\n{search_output}"
                    }
                    report_result = report_generation_agent.invoke(report_state)

                    final_report = report_result.get("final_report", "")
                    if not final_report:
                        # messages에서 추출 시도
                        report_messages = report_result.get("messages", [])
                        if report_messages:
                            last_msg = report_messages[-1]
                            if hasattr(last_msg, 'content'):
                                final_report = last_msg.content
                            elif isinstance(last_msg, dict):
                                final_report = last_msg.get("content", "")

                    logger.info(f"✅ 보고서 생성 완료 (길이: {len(final_report)} 문자)")

                    return {
                        "subagent_result": {
                            "status": "completed",
                            "final_report": final_report,
                            "search_results": search_output,
                            "workflow_chain": chain
                        },
                        "status": "subagent_completed"
                    }
                else:
                    # 검색만 실행한 경우
                    return {
                        "subagent_result": {
                            "status": "completed",
                            "search_results": search_output,
                            "workflow_chain": chain
                        },
                        "status": "subagent_completed"
                    }

            return {
                "status": "error",
                "final_result": "워크플로우 체인 실행 실패: parallel_search_agent가 체인에 없습니다."
            }
        except Exception as e:
            error_msg = f"워크플로우 체인 실행 중 오류: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "status": "error",
                "subagent_result": {"error": error_msg},
                "final_result": error_msg
            }

    def route_to_subagent_node(state: MainAgentState) -> MainAgentState:
        """서브 에이전트 라우팅 노드 - 적절한 서브 에이전트 선택 및 실행"""
        logger.info("🚀 [Main Agent] 서브 에이전트로 라우팅 중...")

        task_analysis = state.get("task_analysis", {})
        subagent_name = state.get("subagent_name")
        workflow_chain = task_analysis.get("workflow_chain", [])

        # 워크플로우 체인이 있는 경우 (검색 → 보고서)
        if workflow_chain and len(workflow_chain) >= 1:
            return _execute_workflow_chain(state, workflow_chain)

        if not subagent_name:
            return {
                "status": "error",
                "final_result": "서브 에이전트를 선택할 수 없습니다."
            }

        # 서브 에이전트 선택 및 실행
        try:
            messages = state.get("messages", [])
            # 사용자 쿼리 추출
            user_query = _extract_user_query(messages)

            if subagent_name == "csv_data_analysis_agent":
                logger.info("📊 CSV 분석 서브 에이전트 호출 중...")

                # CSV 데이터 분석 에이전트 호출
                subagent_state = {
                    "messages": [{"role": "user", "content": user_query}],
                    "CSV_file_path": task_analysis.get("parameters", {}).get("csv_path"),
                    "query": task_analysis.get("parameters", {}).get("query", user_query)
                }

                result = csv_data_analysis_agent.invoke(subagent_state)

                logger.info("✅ 서브 에이전트 실행 완료")

                return {
                    "subagent_result": {
                        "status": result.get("status", "unknown"),
                        "final_report": result.get("final_report", ""),
                        "execution_result": result.get("execution_result", ""),
                        "analysis_result": result.get("analysis_result", "")
                    },
                    "status": "subagent_completed"
                }

            elif subagent_name == "parallel_search_agent":
                logger.info("🔍 병렬 검색 서브 에이전트 호출 중...")

                search_state = {
                    "messages": [{"role": "user", "content": user_query}]
                }
                result = parallel_search_agent.invoke(search_state)

                # 검색 결과 추출
                search_output = ""
                if "messages" in result:
                    result_messages = result["messages"]
                    if result_messages:
                        last_msg = result_messages[-1]
                        if hasattr(last_msg, 'content'):
                            search_output = last_msg.content
                        elif isinstance(last_msg, dict):
                            search_output = last_msg.get("content", "")
                if not search_output:
                    search_output = str(result)

                logger.info("✅ 검색 완료")

                return {
                    "subagent_result": {
                        "status": "completed",
                        "search_results": search_output,
                        "messages": result.get("messages", [])
                    },
                    "status": "subagent_completed"
                }

            elif subagent_name == "report_generation_agent":
                logger.info("📝 보고서 생성 서브 에이전트 호출 중...")

                # 보고서 생성을 위한 context 필요
                # 단독 실행 시 기본 context 사용
                report_state = {
                    "context": {
                        "query": user_query,
                        "source": "main_agent",
                        "task_analysis": task_analysis
                    },
                    "report_template": None,
                    "additional_instructions": f"다음 요청에 대한 보고서를 작성하세요: {user_query}"
                }

                result = report_generation_agent.invoke(report_state)

                final_report = result.get("final_report", "")
                if not final_report:
                    report_messages = result.get("messages", [])
                    if report_messages:
                        last_msg = report_messages[-1]
                        if hasattr(last_msg, 'content'):
                            final_report = last_msg.content
                        elif isinstance(last_msg, dict):
                            final_report = last_msg.get("content", "")

                logger.info("✅ 보고서 생성 완료")

                return {
                    "subagent_result": {
                        "status": "completed",
                        "final_report": final_report
                    },
                    "status": "subagent_completed"
                }

            else:
                return {
                    "status": "error",
                    "final_result": f"지원하지 않는 서브 에이전트: {subagent_name}"
                }
        except Exception as e:
            error_msg = f"서브 에이전트 실행 중 오류: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "status": "error",
                "subagent_result": {"error": error_msg},
                "final_result": error_msg
            }

    def synthesize_result_node(state: MainAgentState) -> MainAgentState:
        """결과 통합 노드 - 서브 에이전트 또는 Worker 결과를 종합하여 최종 응답 생성"""
        logger.info("📝 [Main Agent] 결과 통합 중...")

        subagent_result = state.get("subagent_result", {})
        worker_result = state.get("worker_result", {})
        routing_mode = state.get("routing_mode", "subagent")
        messages = state.get("messages", [])

        # 원래 사용자 요청 추출
        user_query = _extract_user_query(messages)

        # 결과 추출 (서브 에이전트 또는 Worker)
        if routing_mode == "subagent":
            if not subagent_result:
                return {
                    "status": "error",
                    "final_result": "서브 에이전트 결과가 없습니다."
                }

            # 에러가 있는 경우
            if "error" in subagent_result:
                return {
                    "status": "error",
                    "final_result": f"오류: {subagent_result['error']}"
                }

            # LLM으로 결과 통합
            try:
                response = main_model.invoke([
                    SystemMessage(content=RESULT_SYNTHESIS_SYSTEM_PROMPT),
                    HumanMessage(content=create_result_synthesis_user_prompt(
                        original_query=user_query,
                        subagent_result=subagent_result,
                        subagent_name=state.get("subagent_name")
                    ))
                ])

                final_result = response.content if hasattr(response, 'content') else str(response)

                logger.info("✅ 결과 통합 완료")

                return {
                    "final_result": final_result,
                    "status": "completed"
                }
            except Exception as e:
                # 폴백: 서브 에이전트 결과를 그대로 사용
                logger.warning(f"⚠️ 결과 통합 실패, 서브 에이전트 결과 사용: {str(e)}")
                fallback_result = subagent_result.get("final_report") or subagent_result.get("execution_result") or str(subagent_result)
                return {
                    "final_result": fallback_result,
                    "status": "completed"
                }

        else:  # Worker 모드
            if not worker_result:
                return {
                    "status": "error",
                    "final_result": "Worker 결과가 없습니다."
                }

            # 에러가 있는 경우
            if "error" in worker_result:
                return {
                    "status": "error",
                    "final_result": f"오류: {worker_result['error']}"
                }

            # Worker 결과 추출 (orchestrator.py 로직)
            if isinstance(worker_result, dict):
                if "messages" in worker_result:
                    messages_list = worker_result["messages"]
                    if messages_list and len(messages_list) > 0:
                        last_message = messages_list[-1]
                        worker_output = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    else:
                        worker_output = str(worker_result)
                elif "result" in worker_result:
                    worker_output = worker_result["result"]
                else:
                    worker_output = str(worker_result)
            else:
                worker_output = str(worker_result)

            # 복잡도에 따라 결과 통합
            task_analysis = state.get("task_analysis", {})
            complexity = task_analysis.get("complexity", "medium") if task_analysis else "medium"

            if complexity == "low" or not task_analysis:
                # 간단한 작업은 Worker 결과 그대로 반환
                final_result = worker_output
            else:
                # 복잡한 작업은 LLM으로 통합
                try:
                    system_message = SystemMessage(
                        content="당신은 결과 통합 전문가입니다. Worker의 결과를 분석하고 종합하여 최종 응답을 생성하세요."
                    )

                    human_message = HumanMessage(
                        content=f"""원래 작업: {user_query}

Worker 실행 결과:
{worker_output}

위 결과를 바탕으로 최종 응답을 생성하세요."""
                    )

                    response = main_model.invoke([system_message, human_message])
                    final_result = response.content if hasattr(response, 'content') else str(response)
                except Exception as e:
                    logger.warning(f"⚠️ 결과 통합 실패, Worker 결과 사용: {str(e)}")
                    final_result = worker_output

            logger.info("✅ 결과 통합 완료")

            return {
                "final_result": final_result,
                "status": "completed"
            }

    def route_to_worker_node(state: MainAgentState) -> MainAgentState:
        """Worker 라우팅 노드 - Worker 팩토리를 통해 적절한 Worker 선택 및 실행"""
        logger.info("🚀 [Main Agent] Worker로 라우팅 중...")

        task_analysis = state.get("task_analysis", {})
        worker_requirements = state.get("worker_requirements", {})

        # 사용자 메시지에서 작업 추출
        messages = state.get("messages", [])
        user_query = _extract_user_query(messages)

        if not user_query:
            return {
                "status": "error",
                "final_result": "사용자 요청을 찾을 수 없습니다."
            }

        # 작업 분석 결과를 바탕으로 필요한 도구 결정
        tools = []
        task_lower = user_query.lower()

        # 웹 검색이 필요한 경우
        if any(keyword in task_lower for keyword in ["주식", "주가", "조사", "검색", "정보", "stock", "research", "search"]):
            from src.tools.factory import ToolFactory
            all_tools = ToolFactory.get_all_tools()
            for tool in all_tools:
                if tool.name == "brave_search":
                    tools.append(tool)
                    logger.info(f"   ✅ {tool.name} 도구 추가됨")
                    break

        # Worker 생성
        try:
            worker = worker_factory.create_worker(
                worker_type=worker_requirements.get("worker_type", "langgraph"),
                model=worker_requirements.get("worker_model", "ollama:qwen2.5-coder:latest"),
                tools=tools,
                workflow_pattern=worker_requirements.get("workflow_pattern"),
                needs_planning=worker_requirements.get("needs_planning", False),
                needs_filesystem=worker_requirements.get("needs_filesystem", False),
                needs_subagent=worker_requirements.get("needs_subagent", False)
            )
            logger.info(f"   ✅ Worker 생성 완료: 타입={type(worker).__name__}")
        except Exception as e:
            error = AgentError(
                message=f"Worker 생성 실패: {str(e)}",
                agent_name="main_agent",
                node_name="route_to_worker_node",
                details={
                    "worker_type": worker_requirements.get("worker_type"),
                    "worker_model": worker_requirements.get("worker_model")
                },
                original_error=e
            )
            logger.error(format_error_message(error, include_traceback=True))

            error_state = format_error_for_state(error)
            error_state["worker_result"] = {"error": error.message}
            error_state["final_result"] = error.message
            increment_error_count(error_state)
            return error_state

        # Worker 실행
        try:
            worker_type = worker_requirements.get("worker_type", "langgraph")

            # Worker 타입 확인 및 실행 (orchestrator.py 로직)
            if isinstance(worker, dict) and "runnable" in worker:
                actual_worker = worker["runnable"]
                logger.info("   📌 CompiledSubAgent에서 runnable 추출")

                if worker_type == "deepagent":
                    result = actual_worker.invoke({
                        "messages": [{"role": "user", "content": user_query}]
                    })
                else:
                    try:
                        result = actual_worker.invoke({
                            "messages": [{"role": "user", "content": user_query}],
                            "task": user_query
                        })
                    except Exception as e1:
                        try:
                            result = actual_worker.invoke({"task": user_query})
                        except Exception as e2:
                            raise ValueError(f"Worker 호출 실패: {e1}, {e2}")
            elif hasattr(worker, 'invoke') and callable(getattr(worker, 'invoke', None)):
                if worker_type == "deepagent":
                    result = worker.invoke({
                        "messages": [{"role": "user", "content": user_query}]
                    })
                else:
                    try:
                        result = worker.invoke({
                            "messages": [{"role": "user", "content": user_query}],
                            "task": user_query
                        })
                    except Exception as e1:
                        try:
                            result = worker.invoke({"task": user_query})
                        except Exception as e2:
                            raise ValueError(f"Worker 호출 실패: {e1}, {e2}")
            elif isinstance(worker, dict):
                raise ValueError(f"Worker가 dict 형식입니다. Worker 타입: {worker_type}, 키: {list(worker.keys())}")
            elif callable(worker):
                result = worker({"task": user_query})
            else:
                raise ValueError(f"알 수 없는 Worker 타입: {type(worker)}")

            logger.info("✅ Worker 실행 완료")

            # 결과 정규화
            if isinstance(result, dict):
                worker_result = result
            else:
                worker_result = {"result": str(result)}

            return {
                "worker_result": worker_result,
                "status": "worker_completed"
            }

        except Exception as e:
            error = AgentError(
                message=f"Worker 실행 중 오류 발생: {str(e)}",
                agent_name="main_agent",
                node_name="route_to_worker_node",
                details={
                    "worker_type": worker_requirements.get("worker_type"),
                    "user_query": user_query[:100]  # 일부만 저장
                },
                original_error=e
            )
            logger.error(format_error_message(error, include_traceback=True))

            error_state = format_error_for_state(error)
            error_state["worker_result"] = {"error": error.message}
            error_state["final_result"] = error.message
            increment_error_count(error_state)
            return error_state

    def route_based_on_task_type(state: MainAgentState) -> Literal["route_to_subagent", "route_to_worker", "synthesize", "end"]:
        """작업 유형에 따른 조건부 라우팅"""
        status = state.get("status", "")
        routing_mode = state.get("routing_mode", "subagent")

        if status == "analyzed":
            if routing_mode == "subagent":
                return "route_to_subagent"
            elif routing_mode == "worker":
                return "route_to_worker"
            else:
                return "synthesize"  # 직접 처리

        if status == "subagent_completed" or status == "worker_completed":
            return "synthesize"

        if status == "error":
            return "end"

        return "end"

    # 그래프 구성
    graph = StateGraph(MainAgentState)

    # 노드 추가
    graph.add_node("analyze_task", analyze_task_node)
    graph.add_node("route_to_subagent", route_to_subagent_node)
    graph.add_node("route_to_worker", route_to_worker_node)
    graph.add_node("synthesize", synthesize_result_node)

    # 엣지 및 조건부 라우팅
    graph.add_edge(START, "analyze_task")
    graph.add_conditional_edges(
        "analyze_task",
        route_based_on_task_type,
        {
            "route_to_subagent": "route_to_subagent",
            "route_to_worker": "route_to_worker",
            "synthesize": "synthesize",
            "end": END
        }
    )
    graph.add_edge("route_to_subagent", "synthesize")
    graph.add_edge("route_to_worker", "synthesize")
    graph.add_edge("synthesize", END)

    compiled_graph = graph.compile()

    logger.info("✅ 상위 에이전트 생성 완료")
    logger.info(f"   모델: {model_str}")
    logger.info(f"   서브 에이전트: csv_data_analysis_agent, parallel_search_agent, report_generation_agent")
    logger.info(f"   워크플로우 체인: parallel_search_agent → report_generation_agent")
    logger.info(f"   Worker 팩토리: 활성화")
    logger.info(f"   라우팅 모드: 서브 에이전트 + Worker")

    return compiled_graph


# LangGraph Studio용 agent 변수
_agent_cache = None
_agent_cache_lock = threading.Lock()

def _get_default_agent():
    """기본 상위 에이전트 그래프 생성 (thread-safe lazy initialization with caching)"""
    global _agent_cache
    if _agent_cache is None:
        with _agent_cache_lock:
            if _agent_cache is None:  # Double-checked locking
                try:
                    _agent_cache = create_main_agent()
                except Exception as e:
                    logger.warning(f"⚠️ 에이전트 생성 실패: {str(e)}")
                    logger.warning("   환경변수 OLLAMA_API_KEY가 설정되어 있는지 확인하세요.")
                    raise
    return _agent_cache

# Lazy initialization - use _get_default_agent() to get the agent instance
# Do NOT create agent at module level to prevent import side effects
agent = None


# ========== OrchestratorAgent 클래스 (BaseAgent 인터페이스 지원) ==========

class OrchestratorAgent(BaseAgent):
    """상위 Orchestrator Agent - BaseAgent 인터페이스 구현

    이 클래스는 agent.py의 create_main_agent() 함수를 래핑하여
    BaseAgent 인터페이스를 제공합니다. CLI 및 팩토리 패턴 호환성을 위해 제공됩니다.

    주의: LangGraph dev 환경에서는 create_main_agent() 함수를 직접 사용하는 것을 권장합니다.
    """

    def __init__(self, orchestrator_model: Optional[str] = None):
        """OrchestratorAgent 초기화

        Args:
            orchestrator_model: 사용할 모델명 (기본값: ollama:gpt-oss:120b-cloud)
        """
        super().__init__()

        # 모델 초기화
        model_str = orchestrator_model or os.getenv("OLLAMA_MODEL_NAME", "ollama:gpt-oss:120b-cloud")
        if not model_str.startswith("ollama:") and not model_str.startswith("anthropic:") and not model_str.startswith("openai:"):
            model_str = f"ollama:{model_str}"

        self.model_name = model_str

        # 그래프 생성 (create_main_agent 함수 사용)
        try:
            self.graph = create_main_agent(model=model_str)
            logger.info(f"✅ OrchestratorAgent 초기화 완료 (모델: {model_str})")
        except Exception as e:
            logger.error(f"❌ OrchestratorAgent 초기화 실패: {str(e)}")
            self.graph = None

    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        if not self.graph:
            return "❌ 그래프가 초기화되지 않았습니다."

        try:
            # MessagesState 형식으로 초기 상태 설정
            initial_state = {
                "messages": [{"role": "user", "content": query}]
            }

            # 그래프 실행
            result = self.graph.invoke(initial_state)

            # 최종 결과 추출
            final_result = result.get("final_result", "")
            if not final_result:
                # messages에서 마지막 메시지 추출
                messages = result.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        final_result = last_message.get("content", "")
                    elif hasattr(last_message, 'content'):
                        final_result = last_message.content
                    else:
                        final_result = str(last_message)

            return final_result if final_result else "응답을 생성할 수 없습니다."

        except Exception as e:
            return f"❌ 응답 생성 중 오류 발생: {str(e)}"

    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return self.graph is not None

    def get_info(self) -> Dict[str, Any]:
        """Agent 정보 반환"""
        return {
            "type": "OrchestratorAgent",
            "model": self.model_name,
            "architecture": "LangGraph StateGraph (서브 에이전트 + Worker 하이브리드)",
            "ready": self.is_ready(),
            "features": [
                "작업 분석",
                "서브 에이전트 라우팅",
                "Worker 자동 선택",
                "복잡한 워크플로우 패턴 지원",
                "결과 통합",
                "하이브리드 아키텍처"
            ],
            "nodes": ["analyze_task", "route_to_subagent", "route_to_worker", "synthesize"] if self.graph else []
        }
