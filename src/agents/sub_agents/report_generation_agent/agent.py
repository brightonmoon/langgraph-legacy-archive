"""
Report Generation Agent - 보고서 생성 전용 에이전트

다른 에이전트/도구들이 생성한 context를 받아서 보고서만 생성하는 특화 에이전트입니다.

핵심 설계 원칙:
1. 모델 분리: router/orchestrator와 완전히 독립적인 모델 사용
2. Context 기반: 다른 에이전트가 생성한 context를 입력으로 받음
3. 토큰 최소화: 보고서 생성만 담당하여 router/orchestrator의 토큰 사용 최소화
4. 확장 가능: 로컬 모델(gemma3:4b)부터 상용 API까지 유연하게 지원
"""

import os
from typing import TypedDict, Dict, Any, Optional
from typing_extensions import Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from .prompts import (
    DEFAULT_REPORT_GENERATION_SYSTEM_PROMPT,
    create_report_generation_user_prompt
)


class ReportGenerationState(TypedDict, total=False):
    """보고서 생성 에이전트의 상태
    
    LangGraph Studio에서 테스트 시:
    - context만 제공하면 자동으로 보고서 생성
    - messages는 선택적 (없으면 자동 생성)
    
    agent.py에서 서브 에이전트로 사용 시:
    - messages를 통해 다른 에이전트와 통신
    - context는 다른 에이전트가 생성한 정보
    
    핵심 필드:
    - messages: LangGraph 표준 메시지 리스트 (선택적, 없으면 자동 생성)
    - context: 다른 에이전트/도구가 생성한 컨텍스트 정보 (필수)
    - report_template: 사용할 보고서 템플릿 (선택적)
    - additional_instructions: 추가 지시사항 (선택적)
    - final_report: 생성된 최종 보고서 (출력)
    """
    messages: Annotated[list, add_messages]  # 선택적: 없으면 자동 생성
    context: Dict[str, Any]  # 필수: 다른 에이전트가 생성한 컨텍스트
    report_template: Optional[str]  # 선택적: 보고서 템플릿
    additional_instructions: Optional[str]  # 선택적: 추가 지시사항
    final_report: Optional[str]  # 출력: 생성된 보고서


def create_report_generation_agent(
    model: str = "ollama:gemma3:12b",
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
):
    """보고서 생성 전용 에이전트 생성
    
    Args:
        model: 사용할 모델 (기본값: gemma3:4b, 나중에 더 큰 모델로 업그레이드 가능)
              형식: "ollama:gemma3:4b", "anthropic:claude-sonnet-4-5-20250929" 등
        temperature: 모델 temperature (기본값: 0.7)
        system_prompt: 커스텀 시스템 프롬프트 (None이면 기본 프롬프트 사용)
    
    Returns:
        LangGraph CompiledStateGraph
    
    설계 원칙:
    - Router/orchestrator와 완전히 독립적인 모델 사용
    - Context를 입력으로 받아 보고서만 생성
    - 토큰 사용 최소화 (보고서 생성에만 집중)
    """
    # 모델 이름 정규화
    model = model.strip() if model else "ollama:gemma3:12b"
    
    # 모델 타입에 따라 API 키 가져오기
    api_key = None
    if model.startswith("ollama:"):
        api_key = os.getenv("OLLAMA_API_KEY")
    elif model.startswith("anthropic:"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
    elif model.startswith("openai:"):
        api_key = os.getenv("OPENAI_API_KEY")
    
    # 모델 초기화
    chat_model = init_chat_model_helper(
        model_name=model,
        api_key=api_key,
        temperature=temperature
    )
    
    if not chat_model:
        raise ValueError(
            f"보고서 생성 모델 초기화 실패: {model}\n"
            f"모델이 존재하는지 확인하세요."
        )
    
    # 시스템 프롬프트 결정
    final_system_prompt = system_prompt or DEFAULT_REPORT_GENERATION_SYSTEM_PROMPT
    
    # LangGraph 그래프 구성
    graph = StateGraph(ReportGenerationState)
    
    # 보고서 생성 노드 추가
    # 실제 보고서 생성은 모델을 호출해야 하므로, 노드를 래핑
    def generate_report_with_model(state: ReportGenerationState) -> ReportGenerationState:
        """모델을 사용하여 보고서 생성
        
        LangGraph Studio 테스트 시:
        - context만 제공하면 자동으로 보고서 생성
        - messages는 선택적 (없으면 자동 생성)
        """
        context = state.get("context", {})
        report_template = state.get("report_template")
        additional_instructions = state.get("additional_instructions")
        existing_messages = state.get("messages", [])
        
        if not context:
            error_msg = "Context가 제공되지 않았습니다."
            print(f"❌ {error_msg}")
            return {
                "final_report": f"오류: {error_msg}",
                "messages": existing_messages
            }
        
        # 사용자 프롬프트 생성
        user_prompt = create_report_generation_user_prompt(
            context=context,
            report_template=report_template,
            additional_instructions=additional_instructions
        )
        
        try:
            # 모델 호출
            print(f"📝 [Report Generation Agent] 모델 호출 중... (모델: {model})")
            response = chat_model.invoke([
                SystemMessage(content=final_system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            final_report = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ 보고서 생성 완료 (길이: {len(final_report)} 문자)")
            
            # messages 업데이트 (기존 messages가 있으면 추가, 없으면 새로 생성)
            updated_messages = existing_messages + [
                SystemMessage(content=final_system_prompt),
                HumanMessage(content=user_prompt),
                response
            ]
            
            return {
                "final_report": final_report,
                "messages": updated_messages
            }
        except Exception as e:
            error_msg = f"보고서 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "final_report": f"오류: {error_msg}",
                "messages": existing_messages
            }
    
    graph.add_node("generate_report", generate_report_with_model)
    
    # 엣지 구성
    graph.add_edge(START, "generate_report")
    graph.add_edge("generate_report", END)
    
    print("✅ 보고서 생성 에이전트가 성공적으로 생성되었습니다.")
    print(f"   모델: {model}")
    print(f"   Temperature: {temperature}")
    print(f"   특징: Router/orchestrator와 독립적인 모델 사용")
    
    return graph.compile()


# LangGraph Studio용 agent 변수 (lazy initialization)
_agent_cache = None

def _get_default_agent():
    """기본 보고서 생성 에이전트 그래프 생성 (lazy initialization with caching)"""
    global _agent_cache
    if _agent_cache is None:
        try:
            _agent_cache = create_report_generation_agent()
        except Exception as e:
            print(f"⚠️ 에이전트 생성 실패: {str(e)}")
            print("   환경변수가 설정되어 있는지 확인하세요.")
            raise
    return _agent_cache

# LangGraph Studio에서 참조할 agent 변수
try:
    agent = _get_default_agent()
except Exception:
    # 초기화 실패 시에도 모듈 로드는 성공하도록 함
    agent = None

