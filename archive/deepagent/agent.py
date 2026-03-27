"""
DeepAgents 라이브러리를 사용하는 Deep Agent 구현

LangChain의 deepagents 패키지를 활용하여 복잡한 멀티 스텝 작업을 처리하는
고급 에이전트를 구현합니다.
"""

import os
import warnings
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# Pydantic serializer 경고 억제 (deepagents 내부 경고)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


def setup_langsmith_disabled():
    """LangSmith 완전 비활성화"""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGSMITH_API_KEY"] = ""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


class DeepAgentLibrary:
    """DeepAgents 라이브러리를 사용하는 Deep Agent 클래스
    
    deepagents 패키지의 create_deep_agent 함수를 사용하여
    간단하게 고급 에이전트를 생성합니다.
    
    특징:
    - Planning (작업 분해): write_todos 도구 자동 제공
    - File System: ls, read_file, write_file, edit_file 자동 제공
    - Subagents: task 도구로 서브에이전트 생성 가능
    - CSV 분석: CSV 분석 subagent (pandas 설치 시 자동 생성)
    - MCP 도구: mcp_config.json이 있으면 자동 로드
    - Middleware: 자동으로 컨텍스트 관리 및 최적화
    - 자동 감지: 모델, API 키, 도구 등을 환경변수에서 자동으로 감지
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
        subagents: Optional[List[Dict[str, Any]]] = None,
        checkpointer: Optional[Any] = None,
        interrupt_on: Optional[Dict[str, Any]] = None
    ):
        """DeepAgent 초기화
        
        Args:
            model: 사용할 모델명 (예: "claude-sonnet-4-5-20250929", "gpt-4o")
                  None이면 환경변수에서 자동 결정 (Ollama 우선, 없으면 Claude/OpenAI)
            tools: 추가할 커스텀 도구 리스트 (메인 에이전트용)
                  None이면 기본 도구 자동 로드 (Brave Search, MCP 도구 자동 감지)
            system_prompt: 커스텀 시스템 프롬프트
            subagents: 서브에이전트 리스트 (딕셔너리 또는 CompiledSubAgent 객체)
                      각 subagent는 name, description, system_prompt, tools, model 등을 포함
            checkpointer: Checkpointer 인스턴스 (휴먼 루프 사용 시 필수)
            interrupt_on: 인터럽트 설정 딕셔너리 (휴먼 루프 사용 시)
        
        Note:
            - MCP 도구: mcp_config.json이 있고 사용 가능하면 자동 로드
            - CSV Subagent: pandas가 설치되어 있으면 자동 생성
            - API 키: 환경변수에서 자동으로 가져옴 (.env 파일 사용)
            - Subagents: 컨텍스트 격리 및 전문 작업 위임에 유용
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
        
        self.model = init_chat_model(model, api_key=api_key, temperature=0.7)
        
        # 기본 시스템 프롬프트
        csv_instructions = """
4. **CSV 파일 분석 - 매우 중요**: 
   
   ⚠️🚨 절대 규칙: 파일명이 .csv로 끝나거나 CSV 파일이라고 언급된 경우, 반드시 CSV 전용 도구만 사용하세요!
   
   ❌ 절대 사용 금지:
   - read_file, mcp_read_file, mcp_read_text_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
   - ls, write_file, edit_file 등의 파일 시스템 도구로 CSV 파일 접근 금지!
   - CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생하고 작업이 실패합니다!
   
   ✅ 반드시 사용해야 할 CSV 전용 도구:
   - read_csv_metadata: CSV 파일의 메타데이터 조회 (파일 크기, 컬럼 정보, 샘플 데이터)
   - read_csv_chunk: CSV 파일의 일부만 읽기 (메모리 효율적, 대용량 파일 지원)
   - filter_csv: pandas query 문자열로 CSV 파일 필터링
   - csv_summary_stats: CSV 파일의 요약 통계 계산
   
   📋 CSV 파일 분석 절차:
   1. 파일명이 .csv로 끝나거나 CSV 파일이라고 언급되면, 즉시 read_csv_metadata 도구를 사용하세요
   2. read_csv_metadata 도구로 파일 구조를 먼저 확인하세요
   3. 필요한 경우 read_csv_chunk 도구로 데이터를 읽으세요
   4. 필터링이 필요하면 filter_csv 도구를 사용하세요
   5. 통계가 필요하면 csv_summary_stats 도구를 사용하세요
   
   ⚠️ 기억하세요: CSV 파일은 read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats 중 하나만 사용하세요!
"""
        
        default_system_prompt = f"""당신은 고급 Deep Agent입니다. 복잡한 멀티 스텝 작업을 처리할 수 있습니다.

**⚠️ 매우 중요 - 언어 규칙:**
- 모든 응답, 보고서, 분석 결과는 반드시 한글로 작성하세요.
- 영어로 응답하지 마세요. 모든 출력은 한국어로 작성되어야 합니다.
- 데이터를 읽고 분석한 결과를 보고서로 작성할 때도 반드시 한글로 작성하세요.
- 컬럼명이나 데이터 값은 원본 그대로 유지하되, 설명과 분석은 모두 한글로 작성하세요.

**핵심 기능:**
1. **작업 분해**: write_todos 도구를 사용하여 복잡한 작업을 하위 작업으로 분해하세요.
2. **Plan 관리 (Offload Context)**: 
   - 복잡한 멀티 스텝 작업의 경우, write_todos로 작업을 분해한 후 format_plan 도구로 마크다운 형식으로 변환하세요.
   - save_plan 도구를 사용하여 plan.md 파일로 저장하세요. 이렇게 하면 세션 간 plan을 공유하거나 컨텍스트를 오프로드할 수 있습니다.
   - 이전 세션의 plan을 계속하려면 load_plan 도구를 사용하여 plan.md 파일을 불러오세요.
   - 작업 진행 상황에 따라 plan을 업데이트하고 save_plan으로 다시 저장하세요.
3. **컨텍스트 관리**: 파일 시스템 도구(ls, read_file, write_file, edit_file)를 사용하여 컨텍스트를 관리하세요.
4. **CSV 파일 분석**: CSV 파일 분석 전용 도구를 사용하여 데이터를 분석하세요.{csv_instructions}

**도구 선택 규칙 (매우 중요):**
- 파일명이 .csv로 끝나거나 "CSV 파일"이라고 언급되면 → CSV 전용 도구 사용 (read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats)
- 일반 텍스트 파일(.txt, .md, .py 등) → read_file, write_file, edit_file 사용
- 디렉토리 탐색 → ls 도구 사용

**도구 선택 우선순위:**
1. 파일명이나 확장자를 먼저 확인하세요
2. .csv 확장자가 있으면 반드시 read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats 중 하나를 선택하세요
3. .csv가 아닌 파일에만 read_file, mcp_read_file을 사용하세요

**보고서 작성 규칙:**
- 데이터를 분석한 후 보고서를 작성할 때는 반드시 한글로 작성하세요.
- 분석 결과, 통계, 요약, 결론 등 모든 내용을 한글로 작성하세요.
- 영어로 작성하지 마세요. 모든 설명과 분석은 한국어로 작성되어야 합니다.

복잡한 작업의 경우:
1. 먼저 write_todos로 작업을 분해하세요.
2. format_plan 도구를 사용하여 plan을 마크다운 형식으로 변환하세요.
3. save_plan 도구를 사용하여 plan.md 파일로 저장하세요 (세션 간 공유 및 컨텍스트 오프로드).
4. 필요시 파일 시스템 도구로 컨텍스트를 관리하세요.
5. CSV 파일 분석이 필요하면 반드시 CSV 전용 도구를 사용하세요.
6. 작업 진행 상황에 따라 plan을 업데이트하고 save_plan으로 다시 저장하세요.
7. 분석 결과를 보고서로 작성할 때는 반드시 한글로 작성하세요.

**이전 세션 계속하기:**
- load_plan 도구를 사용하여 plan.md 파일을 불러오세요.
- 읽은 plan을 바탕으로 작업을 계속하세요.

필요한 경우 적절한 도구를 사용하여 작업을 수행하세요."""
        
        # 최종 시스템 프롬프트
        final_system_prompt = system_prompt or default_system_prompt
        
        # 도구 자동 로드 (MCP 도구 자동 감지)
        if tools is None:
            try:
                # 절대 import 시도 (패키지로 설치된 경우)
                from deepagent.tools import get_all_tools, load_mcp_tools_sync
            except ImportError:
                try:
                    # 상대 import 시도 (패키지로 import될 때)
                    from .tools import get_all_tools, load_mcp_tools_sync
                except ImportError:
                    # 직접 파일 import (같은 디렉토리)
                    import sys
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    if current_dir not in sys.path:
                        sys.path.insert(0, current_dir)
                    from tools import get_all_tools, load_mcp_tools_sync
            
            # 기본 도구 가져오기 (Brave Search + CSV 도구 포함)
            final_tools = get_all_tools(include_mcp=False, include_csv=True)
            if final_tools:
                print(f"   기본 도구: {len(final_tools)}개 자동 로드됨")
            
            # MCP 도구 자동 로드 시도
            # 기본적으로 활성화 (LOAD_MCP_TOOLS 환경변수가 false로 설정되어 있지 않으면 활성화)
            _load_mcp_tools = os.getenv("LOAD_MCP_TOOLS", "true").lower() != "false"
            if _load_mcp_tools:
                try:
                    mcp_tools = load_mcp_tools_sync()
                    if mcp_tools:
                        # Filesystem MCP 도구 필터링 (CSV 도구와 충돌 방지)
                        filesystem_tool_names = {
                            "mcp_read_file", "mcp_read_text_file", "mcp_read_media_file",
                            "mcp_read_multiple_files", "mcp_write_file", "mcp_edit_file",
                            "mcp_create_directory", "mcp_list_directory", "mcp_list_directory_with_sizes",
                            "mcp_directory_tree", "mcp_move_file", "mcp_search_files",
                            "mcp_get_file_info", "mcp_list_allowed_directories"
                        }
                        filtered_mcp_tools = [
                            t for t in mcp_tools 
                            if not (hasattr(t, 'name') and t.name in filesystem_tool_names)
                        ]
                        if filtered_mcp_tools:
                            final_tools.extend(filtered_mcp_tools)
                            print(f"   MCP 도구: {len(filtered_mcp_tools)}개 자동 로드됨 (Filesystem 제외)")
                except Exception as e:
                    # MCP 도구가 없으면 무시
                    print(f"   ⚠️ MCP 도구 로드 실패: {str(e)}")
            else:
                print("   ⚠️ MCP 도구 로드 비활성화됨 (LOAD_MCP_TOOLS=false)")
        else:
            final_tools = tools if tools else []
        
        # create_deep_agent 사용 (DeepAgents 공식 방법)
        # CSV 도구는 이미 final_tools에 포함되어 있음
        # create_deep_agent는 자동으로 다음 middleware를 추가함:
        # - FilesystemMiddleware: 파일 시스템 도구 제공 (ls, read_file, write_file, edit_file)
        #   → 그래프 노드: "FilesystemMiddleware.before_agent"로 표시됨
        # - TodoListMiddleware: write_todos 도구 제공 (작업 분해)
        #   → 별도 그래프 노드 없이 도구만 제공됨 (tools 노드에서 실행)
        # - SubAgentMiddleware: task 도구 제공 (서브에이전트 생성)
        #   → 별도 그래프 노드 없이 도구만 제공됨
        # - PatchToolCallsMiddleware: 도구 호출 패치
        #   → 그래프 노드: "PatchToolCallsMiddleware.before_agent"로 표시됨
        
        # create_deep_agent를 사용하여 에이전트 생성
        # checkpointer와 interrupt_on은 create_deep_agent에 직접 전달됨
        self.agent = create_deep_agent(
            model=self.model,
            tools=final_tools,
            system_prompt=final_system_prompt,
            subagents=subagents,
            checkpointer=checkpointer,
            interrupt_on=interrupt_on
        )
        
        # Subagents 정보 출력
        if subagents:
            print(f"   Subagents: {len(subagents)}개 설정됨")
            for subagent in subagents:
                if isinstance(subagent, dict):
                    print(f"      - {subagent.get('name', 'unknown')}: {subagent.get('description', '')[:50]}")
                else:
                    print(f"      - {getattr(subagent, 'name', 'unknown')}: {getattr(subagent, 'description', '')[:50]}")
        
        print("✅ DeepAgent 라이브러리 에이전트가 성공적으로 생성되었습니다.")
        print(f"   모델: {model}")
        print(f"   커스텀 도구: {len(tools) if tools else 0}개")
        print(f"   총 도구: {len(final_tools)}개")
    
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
        print("\n🤖 DeepAgent 라이브러리 응답:")
        print("=" * 50)
        
        if query:
            result = self.invoke(query)
            if "error" in result:
                print(f"❌ 오류: {result['error']}")
            else:
                print(result["messages"][-1].content if result.get("messages") else "응답 없음")
        else:
            # 대화형 루프
            print("💡 DeepAgent는 복잡한 멀티 스텝 작업을 처리할 수 있습니다.")
            print("💡 '/exit' 또는 '/quit' 입력 시 종료됩니다.")
            print("-" * 50)
            
            while True:
                try:
                    user_input = input("\n👤 사용자: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                        print("\n👋 DeepAgent 대화를 종료합니다.")
                        break
                    
                    # 응답 생성
                    result = self.invoke(user_input)
                    if "error" in result:
                        print(f"\n❌ 오류: {result['error']}")
                    else:
                        response = result["messages"][-1].content if result.get("messages") else "응답 없음"
                        print(f"\n🤖 DeepAgent: {response}")
                    
                except KeyboardInterrupt:
                    print("\n\n👋 Ctrl+C로 대화를 종료합니다.")
                    break
                except Exception as e:
                    print(f"\n❌ 오류 발생: {str(e)}")
        
        print("=" * 50)
    
    def create_csv_query(self, csv_filepath: str, analysis_type: str = "full") -> Dict[str, Any]:
        """CSV 분석을 위한 쿼리 생성
        
        CSV 분석은 CSV 전용 도구를 직접 사용합니다.
        
        Args:
            csv_filepath: 분석할 CSV 파일 경로
            analysis_type: 분석 유형 ("full", "metadata", "filter", "stats")
            
        Returns:
            CSV 분석을 위한 쿼리 딕셔너리
        """
        if analysis_type == "metadata":
            query = f"{csv_filepath} 파일의 구조와 메타데이터를 조회하세요. read_csv_metadata 도구를 사용하여 파일 정보를 확인하세요."
        elif analysis_type == "filter":
            query = f"{csv_filepath} 파일의 데이터를 필터링하고 결과를 요약하세요. filter_csv 도구를 사용하여 데이터를 필터링하세요."
        elif analysis_type == "stats":
            query = f"{csv_filepath} 파일의 수치형 컬럼에 대한 통계 정보를 계산하세요. csv_summary_stats 도구를 사용하여 통계를 계산하세요."
        else:  # full
            query = f"{csv_filepath} 파일을 전체적으로 분석하세요. 먼저 read_csv_metadata 도구로 파일 구조를 확인하고, 필요한 경우 read_csv_chunk, filter_csv, csv_summary_stats 도구를 사용하세요."
        
        return {
            "query": query,
            "filepath": csv_filepath,
            "analysis_type": analysis_type,
            "instructions": "CSV 전용 도구(read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats)를 사용하세요."
        }
    
    def get_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "type": "DeepAgentLibrary",
            "model": str(self.model),
            "library": "deepagents",
            "features": [
                "Planning and Task Decomposition",
                "Context Management (File System)",
                "CSV Analysis Tools (read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats)",
                "Middleware Architecture"
            ]
        }


# ============================================
# LangGraph dev 환경용 export 함수
# ============================================

def create_deep_agent_graph(
    model: Optional[str] = None,
    tools: Optional[List] = None,
    system_prompt: Optional[str] = None,
    subagents: Optional[List[Dict[str, Any]]] = None,
    checkpointer: Optional[Any] = None,
    interrupt_on: Optional[Dict[str, Any]] = None
):
    """LangGraph dev 환경에서 사용할 DeepAgent 그래프 생성
    
    Args:
        model: 사용할 모델명 (None이면 환경변수에서 자동 결정)
        tools: 추가할 커스텀 도구 리스트 (None이면 자동 로드)
        system_prompt: 커스텀 시스템 프롬프트
        subagents: 서브에이전트 리스트 (딕셔너리 또는 CompiledSubAgent 객체)
        checkpointer: Checkpointer 인스턴스 (휴먼 루프 사용 시)
        interrupt_on: 인터럽트 설정 딕셔너리
        
    Returns:
        LangGraph CompiledStateGraph
    
    Note:
        - MCP 도구와 CSV subagent는 자동으로 감지되어 포함됩니다
        - API 키는 환경변수에서 자동으로 가져옵니다
    """
    agent_lib = DeepAgentLibrary(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        subagents=subagents,
        checkpointer=checkpointer,
        interrupt_on=interrupt_on
    )
    return agent_lib.agent


# LangGraph dev용 기본 그래프 (langgraph.json에서 참조)
# 환경변수에서 자동으로 설정을 읽어옴
# 주의: 모듈 import 시점에 실행되므로 환경변수가 설정되어 있어야 함

def _get_default_agent():
    """기본 DeepAgent 그래프 생성 (lazy initialization)
    
    MCP 도구와 CSV subagent는 자동으로 감지되어 포함됩니다.
    """
    return create_deep_agent_graph()

# LangGraph dev에서 참조할 agent 변수
agent = _get_default_agent()

