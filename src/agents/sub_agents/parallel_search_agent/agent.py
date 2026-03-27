"""
병렬 검색 에이전트

Tavily와 Brave Search를 병렬로 사용하여 검색 결과를 취합하고 보고서를 작성하는 메인 에이전트입니다.
"""

import os
import warnings
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# Pydantic serializer 경고 억제
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


def setup_langsmith_disabled():
    """LangSmith 완전 비활성화"""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGSMITH_API_KEY"] = ""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


class ParallelSearchAgent:
    """병렬 검색 에이전트 클래스
    
    Tavily와 Brave Search를 병렬로 사용하여 검색 결과를 취합하고 보고서를 작성합니다.
    
    특징:
    - 병렬 검색: Tavily와 Brave Search 서브에이전트가 동시에 검색 수행
    - 결과 취합: 메인 에이전트가 두 검색 결과를 종합하여 보고서 작성
    - 컨텍스트 격리: 각 서브에이전트가 독립적으로 동작하여 컨텍스트 보호
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        checkpointer: Optional[Any] = None,
        interrupt_on: Optional[Dict[str, Any]] = None
    ):
        """병렬 검색 에이전트 초기화
        
        Args:
            model: 사용할 모델명 (예: "claude-sonnet-4-5-20250929", "gpt-4o")
                  None이면 환경변수에서 자동 결정 (Ollama 우선, 없으면 Claude/OpenAI)
            system_prompt: 커스텀 시스템 프롬프트
            checkpointer: Checkpointer 인스턴스 (휴먼 루프 사용 시 필수)
            interrupt_on: 인터럽트 설정 딕셔너리 (휴먼 루프 사용 시)
        
        Note:
            - TAVILY_API_KEY와 BRAVE_API_KEY가 환경변수에 설정되어 있어야 합니다
            - API 키는 환경변수에서 자동으로 가져옴 (.env 파일 사용)
        """
        # 환경변수 로드
        load_dotenv()
        
        # LangSmith 비활성화
        setup_langsmith_disabled()
        
        # 모델 자동 결정 (환경변수 기반)
        if model is None:
            # Ollama 우선 확인
            ollama_model_name = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
            ollama_api_key = os.getenv("OLLAMA_API_KEY")
            if ollama_api_key:
                model = f"ollama:{ollama_model_name}"
                api_key = ollama_api_key
            else:
                # Claude 확인
                anthropic_key = os.getenv("ANTHROPIC_API_KEY")
                if anthropic_key:
                    model = "anthropic:claude-sonnet-4-5-20250929"
                    api_key = anthropic_key
                else:
                    # OpenAI 확인
                    openai_key = os.getenv("OPENAI_API_KEY")
                    if openai_key:
                        model = "openai:gpt-4o"
                        api_key = openai_key
                    else:
                        raise ValueError(
                            "API 키가 설정되지 않았습니다. "
                            ".env 파일에 OLLAMA_API_KEY, ANTHROPIC_API_KEY, 또는 OPENAI_API_KEY를 설정하세요."
                        )
        else:
            # 지정된 모델 사용 시 API 키 자동 결정
            if not model.startswith(("ollama:", "anthropic:", "openai:", "google:")):
                # 프로바이더가 없으면 Ollama로 가정
                model = f"ollama:{model}"
            
            # 모델 타입에 따라 API 키 자동 결정
            if model.startswith("ollama:"):
                api_key = os.getenv("OLLAMA_API_KEY")
            elif model.startswith("anthropic:"):
                api_key = os.getenv("ANTHROPIC_API_KEY")
            elif model.startswith("openai:"):
                api_key = os.getenv("OPENAI_API_KEY")
            elif model.startswith("google:"):
                api_key = os.getenv("GOOGLE_API_KEY")
            else:
                api_key = None
            
            if not api_key:
                raise ValueError(
                    f"모델 '{model}'에 대한 API 키가 환경변수에 설정되지 않았습니다."
                )
        
        # 모델 초기화
        try:
            self.model = init_chat_model(model, api_key=api_key, temperature=0.7)
            if self.model is None:
                raise ValueError(f"모델 초기화 실패: {model}")
        except Exception as e:
            raise ValueError(
                f"모델 초기화 중 오류 발생: {str(e)}\n"
                f"모델: {model}\n"
                f"API 키가 올바르게 설정되었는지 확인하세요."
            ) from e
        
        # 현재 날짜 동적 생성 (서브에이전트와 동일한 형식)
        from datetime import datetime
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        current_year = datetime.now().strftime("%Y")
        
        # 기본 시스템 프롬프트
        default_system_prompt = f"""당신은 병렬 검색 결과를 취합하고 보고서를 작성하는 전문 에이전트입니다.

**현재 날짜 정보:**
- 오늘 날짜: {current_date}
- 현재 연도: {current_year}

**⚠️ 매우 중요 - 언어 규칙:**
- 모든 응답, 보고서, 분석 결과는 반드시 한글로 작성하세요.
- 영어로 응답하지 마세요. 모든 출력은 한국어로 작성되어야 합니다.

**🚨 필수 규칙 - 병렬 검색 (절대 위반 금지):**

**방법 1: 병렬 검색 도구 사용 (권장 - 진정한 병렬 실행)**
- `parallel_search` 도구를 사용하세요
- 이 도구는 내부에서 Tavily와 Brave Search를 동시에 실행합니다
- 하나의 도구 호출로 두 검색 엔진이 병렬로 실행됩니다
- 예: parallel_search(query="검색할 내용")

**방법 2: 서브에이전트 사용 (대안)**
- 병렬 검색 도구를 사용할 수 없는 경우에만 사용
- tavily-searcher와 brave-searcher를 각각 별도의 task 호출로 실행하세요
- 두 task를 연속적으로 호출하세요
- 예: 
  - task(name="tavily-searcher", task="[검색 쿼리]")
  - task(name="brave-searcher", task="[검색 쿼리]")

**검색 쿼리 최적화:**
- 검색 쿼리에 "{current_year}" 또는 "최신" 키워드를 포함하세요
- 사용자 쿼리에 날짜가 없으면 자동으로 "{current_year}"를 추가하세요
- 예: "AI 트렌드" → "AI 트렌드 {current_year}" 또는 "최신 AI 트렌드"

**핵심 기능:**
1. **병렬 검색 (필수)**: 
   - **우선순위 1**: `parallel_search` 도구를 사용하세요 (진정한 병렬 실행)
   - **우선순위 2**: parallel_search 도구를 사용할 수 없으면 두 서브에이전트를 모두 호출하세요
   - 검색 작업이 필요하면 반드시 두 검색 엔진의 결과를 모두 수집해야 합니다

2. **결과 취합**: 
   - 두 서브에이전트의 검색 결과를 모두 받아서 종합 분석하세요
   - 중복 정보를 제거하고 핵심 정보를 추출하세요
   - 두 검색 엔진의 결과를 비교하여 더 정확한 정보를 선별하세요

3. **보고서 작성**: 
   - 종합 분석 결과를 바탕으로 구조화된 보고서를 작성하세요
   - 보고서는 한글로 작성하세요
   - 출처를 명시하세요

**보고서 구조:**
1. 요약 (Executive Summary) - 2-3 문단
2. 주요 발견사항 - 불릿 포인트
3. 상세 분석 - 각 검색 엔진의 결과 비교 및 종합
4. 결론 및 권장사항
5. 출처 (Tavily와 Brave Search 결과의 URL)

**작업 절차 (필수 순서):**
1. 사용자의 검색 요청을 받으면, 검색 쿼리에 "{current_year}" 또는 "최신" 키워드를 추가하세요
2. **병렬 검색 실행:**
   - **방법 1 (권장)**: parallel_search(query="[최적화된 검색 쿼리]") 도구 사용
   - **방법 2 (대안)**: 두 개의 task 호출
     - task(name="tavily-searcher", task="[최적화된 검색 쿼리]")
     - task(name="brave-searcher", task="[최적화된 검색 쿼리]")
3. 검색 결과를 받아서 취합하세요
4. 결과를 종합 분석하여 보고서를 작성하세요

**예시 (권장 방법):**
사용자 쿼리: "삼성전자 주가 상승 이유"
→ parallel_search(query="삼성전자 주가 상승 이유 {current_year} 최신")
→ 두 검색 엔진이 병렬로 실행되어 결과 취합
→ 결과를 종합 분석하여 보고서 작성

**예시 (대안 방법):**
사용자 쿼리: "삼성전자 주가 상승 이유"
→ Step 1: task(name="tavily-searcher", task="삼성전자 주가 상승 이유 {current_year} 최신")
→ Step 2: task(name="brave-searcher", task="삼성전자 주가 상승 이유 {current_year} 최신")
→ Step 3: 두 결과를 취합하여 보고서 작성

**중요:**
- ⚠️ 절대 하나의 서브에이전트만 호출하지 마세요
- ⚠️ 항상 두 검색 엔진을 모두 사용하여 더 풍부한 정보를 수집하세요
- 검색 결과를 그대로 나열하지 말고 분석과 인사이트를 제공하세요
- 모든 내용은 한글로 작성하세요"""

        # 최종 시스템 프롬프트
        final_system_prompt = system_prompt or default_system_prompt
        
        # 서브에이전트 생성 (상대 import 사용)
        from .subagents import create_tavily_search_subagent, create_brave_search_subagent
        
        subagents = []
        
        # 모델 문자열 저장 (서브에이전트에 전달용)
        # create_deep_agent는 모델 객체를 받지만, 서브에이전트 딕셔너리에는 모델 문자열을 전달해야 함
        model_string = model  # 원본 모델 문자열 저장
        
        # Tavily 검색 서브에이전트
        # model=None이면 메인 모델 사용 (딕셔너리에서 model 필드 제거)
        tavily_subagent = create_tavily_search_subagent(model=None)
        if tavily_subagent:
            # model 필드가 None이면 제거 (메인 모델 사용)
            if tavily_subagent.get("model") is None:
                tavily_subagent.pop("model", None)
            subagents.append(tavily_subagent)
            print(f"   ✅ Tavily 검색 서브에이전트 생성됨")
        else:
            print(f"   ⚠️ Tavily 검색 서브에이전트 생성 실패 (TAVILY_API_KEY 확인 필요)")
        
        # Brave Search 서브에이전트
        # model=None이면 메인 모델 사용 (딕셔너리에서 model 필드 제거)
        brave_subagent = create_brave_search_subagent(model=None)
        if brave_subagent:
            # model 필드가 None이면 제거 (메인 모델 사용)
            if brave_subagent.get("model") is None:
                brave_subagent.pop("model", None)
            subagents.append(brave_subagent)
            print(f"   ✅ Brave Search 서브에이전트 생성됨")
        else:
            print(f"   ⚠️ Brave Search 서브에이전트 생성 실패 (BRAVE_API_KEY 확인 필요)")
        
        if not subagents:
            raise ValueError(
                "검색 서브에이전트를 생성할 수 없습니다. "
                "TAVILY_API_KEY와 BRAVE_API_KEY 중 최소 하나는 설정되어 있어야 합니다."
            )
        
        # 병렬 검색 도구 생성 (선택사항 - 메인 에이전트가 직접 사용 가능)
        parallel_search_tool = None
        try:
            from .tools import create_parallel_search_tool
            parallel_search_tool = create_parallel_search_tool()
            if parallel_search_tool:
                print(f"   ✅ 병렬 검색 도구 생성됨 (메인 에이전트에서 직접 사용 가능)")
        except Exception as e:
            print(f"   ⚠️ 병렬 검색 도구 생성 실패: {str(e)}")
        
        # 메인 에이전트 도구 설정
        # 병렬 검색 도구를 메인 에이전트에 추가하여 진정한 병렬 실행 보장
        main_tools = []
        if parallel_search_tool:
            main_tools.append(parallel_search_tool)
            print(f"   ✅ 병렬 검색 도구가 메인 에이전트에 추가됨 (병렬 실행 보장)")
        
        # create_deep_agent 사용
        self.agent = create_deep_agent(
            model=self.model,
            tools=main_tools,  # 메인 에이전트는 직접 도구를 사용하지 않고 서브에이전트에 위임
            system_prompt=final_system_prompt,
            subagents=subagents,
            checkpointer=checkpointer,
            interrupt_on=interrupt_on
        )
        
        print("✅ 병렬 검색 에이전트가 성공적으로 생성되었습니다.")
        print(f"   모델: {model}")
        print(f"   서브에이전트: {len(subagents)}개")
        for subagent in subagents:
            if isinstance(subagent, dict):
                print(f"      - {subagent.get('name', 'unknown')}")
    
    def invoke(self, query: str) -> Dict[str, Any]:
        """쿼리 실행
        
        Args:
            query: 사용자 쿼리
            
        Returns:
            에이전트 실행 결과
        """
        try:
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": query}]
            })
            return result
        except Exception as e:
            return {
                "error": str(e),
                "messages": []
            }
    
    def chat(self, query: Optional[str] = None):
        """대화형 인터페이스
        
        Args:
            query: 초기 쿼리 (None이면 대화형 루프 시작)
        """
        print("\n🤖 병렬 검색 에이전트 응답:")
        print("=" * 50)
        
        if query:
            result = self.invoke(query)
            if "error" in result:
                print(f"❌ 오류: {result['error']}")
            else:
                print(result["messages"][-1].content if result.get("messages") else "응답 없음")
        else:
            # 대화형 루프
            print("💡 병렬 검색 에이전트는 Tavily와 Brave Search를 병렬로 사용하여 검색합니다.")
            print("💡 '/exit' 또는 '/quit' 입력 시 종료됩니다.")
            print("-" * 50)
            
            while True:
                try:
                    user_input = input("\n👤 사용자: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                        print("\n👋 병렬 검색 에이전트 대화를 종료합니다.")
                        break
                    
                    # 응답 생성
                    result = self.invoke(user_input)
                    if "error" in result:
                        print(f"\n❌ 오류: {result['error']}")
                    else:
                        response = result["messages"][-1].content if result.get("messages") else "응답 없음"
                        print(f"\n🤖 병렬 검색 에이전트: {response}")
                    
                except KeyboardInterrupt:
                    print("\n\n👋 Ctrl+C로 대화를 종료합니다.")
                    break
                except Exception as e:
                    print(f"\n❌ 오류 발생: {str(e)}")
        
        print("=" * 50)
    
    def get_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "type": "ParallelSearchAgent",
            "model": str(self.model),
            "library": "deepagents",
            "features": [
                "병렬 검색 (Tavily + Brave Search)",
                "검색 결과 취합 및 분석",
                "구조화된 보고서 작성",
                "컨텍스트 격리 (Subagents)"
            ]
        }


# ============================================
# LangGraph dev 환경용 export 함수
# ============================================

def create_parallel_search_agent_graph(
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    checkpointer: Optional[Any] = None,
    interrupt_on: Optional[Dict[str, Any]] = None
):
    """LangGraph dev 환경에서 사용할 병렬 검색 에이전트 그래프 생성
    
    Args:
        model: 사용할 모델명 (None이면 환경변수에서 자동 결정)
        system_prompt: 커스텀 시스템 프롬프트
        checkpointer: Checkpointer 인스턴스 (휴먼 루프 사용 시)
        interrupt_on: 인터럽트 설정 딕셔너리
        
    Returns:
        LangGraph CompiledStateGraph
    
    Note:
        - TAVILY_API_KEY와 BRAVE_API_KEY가 환경변수에 설정되어 있어야 합니다
        - API 키는 환경변수에서 자동으로 가져옵니다
    """
    agent_lib = ParallelSearchAgent(
        model=model,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        interrupt_on=interrupt_on
    )
    return agent_lib.agent


# LangGraph dev용 기본 그래프 (langgraph.json에서 참조)
# 환경변수에서 자동으로 설정을 읽어옴
# 주의: 모듈 import 시점에 실행되므로 환경변수가 설정되어 있어야 함

def _get_default_parallel_search_agent():
    """기본 병렬 검색 에이전트 그래프 생성 (lazy initialization)
    
    TAVILY_API_KEY와 BRAVE_API_KEY가 환경변수에 설정되어 있어야 합니다.
    """
    return create_parallel_search_agent_graph()

# LangGraph dev에서 참조할 agent 변수
agent = _get_default_parallel_search_agent()

