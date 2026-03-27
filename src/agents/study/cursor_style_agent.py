"""
Cursor 스타일 실시간 코드 생성 및 실행 에이전트

Cursor처럼 코드를 생성하고 터미널에서 권한을 요청한 후 즉시 실행하는 메커니즘을 구현합니다.
HITL과 달리 로우레벨에서 실시간으로 코드 생성 및 실행을 제어합니다.
"""

# 표준 라이브러리
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal

# 서드파티
from langchain.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, interrupt
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.tools.code_execution import execute_python_code_tool
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


# State 정의
class CursorStyleAgentState(TypedDict):
    """Cursor 스타일 에이전트 상태"""
    # 입력
    user_query: str  # 사용자 요청
    
    # 코드 생성 및 실행
    generated_code: str  # 생성된 코드
    execution_approved: bool  # 실행 승인 여부
    execution_result: str  # 실행 결과
    code_modified: str  # 수정된 코드 (사용자가 수정한 경우)
    
    # 제어 변수
    errors: list[str]  # 에러 목록
    iteration_count: int  # 반복 횟수
    llm_calls: int  # LLM 호출 횟수
    status: str  # 현재 상태
    
    # 메시지 히스토리
    messages: Annotated[list, add_messages]


class CursorStyleAgent(BaseAgent):
    """Cursor 스타일 에이전트 - 실시간 코드 생성 및 실행
    
    워크플로우:
    1. 코드 생성 (LLM)
    2. 터미널 권한 요청 (interrupt)
    3. 사용자 승인/거부/수정
    4. 코드 실행 (승인 시)
    5. 결과 반환
    
    특징:
    - 실시간 코드 생성 및 실행
    - 터미널과 직접 상호작용
    - 각 코드 블록마다 독립적으로 실행
    - 로우레벨 제어
    """
    
    def __init__(self, model_name: str = None, enable_permission_request: bool = True):
        """Agent 초기화
        
        Args:
            model_name: 사용할 모델명 (예: "gpt-oss:120b-cloud", "qwen2.5-coder:latest")
            enable_permission_request: 권한 요청 활성화 여부 (기본값: True)
        """
        setup_langsmith_disabled()
        
        # 모델 초기화
        model_str = model_name or os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
        if model_str and not model_str.startswith("ollama:"):
            model_str = f"ollama:{model_str}"
        
        self.model = init_chat_model_helper(
            model_name=model_str,
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        self.model_name = model_name or "gpt-oss:120b-cloud"
        self.enable_permission_request = enable_permission_request
        
        # Checkpointer 생성 (interrupt 사용 시 필수)
        self.checkpointer = MemorySaver()
        
        self.graph = None
        self.build_graph()
    
    def generate_code_node(self, state: CursorStyleAgentState) -> CursorStyleAgentState:
        """노드 1: 코드 생성"""
        print("💻 [Node 1] 코드 생성 중...")
        
        user_query = state['user_query']
        previous_code = state.get('generated_code', '')
        errors = state.get('errors', [])
        
        # 에러가 있으면 수정 요청, 없으면 생성 요청
        if errors and previous_code:
            print(f"   🔧 에러 수정 중: {len(errors)}개")
            prompt = f"""
다음 코드에 에러가 있습니다. 코드를 수정해주세요:

요청: {user_query}

기존 코드:
{previous_code}

에러:
{chr(10).join(errors)}

수정된 코드만 출력하세요 (설명 없이 코드만).
"""
        else:
            print("   ✨ 새로운 코드 생성")
            prompt = f"""
다음 요청을 수행하는 Python 코드를 작성하세요:

{user_query}

요구사항:
- 실행 가능한 완전한 코드
- 함수 이름과 docstring 포함
- 주석 추가
- Python best practices 준수
- 코드만 출력 (설명 없이)
"""
        
        # LLM으로 코드 생성
        system_message = SystemMessage(
            content="당신은 Python 코드를 작성하는 전문가입니다. 실행 가능한 완전한 코드만 출력하세요."
        )
        human_message = HumanMessage(content=prompt)
        
        response = self.model.invoke([system_message, human_message])
        generated_code = response.content
        
        # 코드 블록 추출 (마크다운 코드 블록 제거)
        if "```python" in generated_code:
            code_start = generated_code.find("```python") + len("```python")
            code_end = generated_code.find("```", code_start)
            if code_end != -1:
                generated_code = generated_code[code_start:code_end].strip()
        elif "```" in generated_code:
            code_start = generated_code.find("```") + 3
            code_end = generated_code.find("```", code_start)
            if code_end != -1:
                generated_code = generated_code[code_start:code_end].strip()
        
        print(f"✅ 코드 생성 완료 ({len(generated_code)} 문자)")
        
        return {
            "generated_code": generated_code,
            "status": "code_generated",
            "llm_calls": state.get("llm_calls", 0) + 1,
            "messages": [response]
        }
    
    def request_permission_node(self, state: CursorStyleAgentState) -> CursorStyleAgentState:
        """노드 2: 권한 요청 (interrupt 사용)"""
        if not self.enable_permission_request:
            # 권한 요청 비활성화 시 자동 승인
            print("✅ 권한 요청 비활성화 - 자동 승인")
            return {
                "execution_approved": True,
                "status": "auto_approved"
            }
        
        print("⏸️  [Node 2] 실행 권한 요청 중...")
        
        generated_code = state['generated_code']
        
        # 터미널에 코드 표시
        print("\n" + "=" * 60)
        print("📝 생성된 코드:")
        print("=" * 60)
        print(generated_code)
        print("=" * 60)
        print("\n⚠️  이 코드를 실행하시겠습니까?")
        print("   - 실행 (y/approve)")
        print("   - 거부 (n/reject)")
        print("   - 수정 (e/edit)")
        print("=" * 60)
        
        # interrupt로 권한 요청
        try:
            approval = interrupt({
                "type": "code_execution_permission",
                "code": generated_code,
                "message": "코드 실행 권한 요청",
                "options": ["approve", "reject", "edit"]
            })
        except Exception as e:
            # interrupts가 비활성화되어 있으면 자동 승인
            print(f"⚠️  interrupt 오류: {str(e)} - 자동 승인")
            return {
                "execution_approved": True,
                "status": "auto_approved"
            }
        
        # Command로 재개된 경우 처리
        if isinstance(approval, dict):
            action = approval.get("action", "approve")
            
            if action == "reject":
                print("❌ 코드 실행 거부됨")
                return {
                    "execution_approved": False,
                    "status": "rejected",
                    "errors": ["코드 실행이 사용자에 의해 거부되었습니다."]
                }
            elif action == "edit":
                modified_code = approval.get("modified_code", generated_code)
                print("✏️  코드 수정됨")
                return {
                    "execution_approved": True,
                    "generated_code": modified_code,
                    "code_modified": modified_code,
                    "status": "modified"
                }
            else:
                # approve
                print("✅ 코드 실행 승인됨")
                return {
                    "execution_approved": True,
                    "status": "approved"
                }
        elif approval == "reject":
            print("❌ 코드 실행 거부됨")
            return {
                "execution_approved": False,
                "status": "rejected",
                "errors": ["코드 실행이 사용자에 의해 거부되었습니다."]
            }
        else:
            # approve (기본값)
            print("✅ 코드 실행 승인됨")
            return {
                "execution_approved": True,
                "status": "approved"
            }
    
    def execute_code_node(self, state: CursorStyleAgentState) -> CursorStyleAgentState:
        """노드 3: 코드 실행"""
        if not state.get('execution_approved', False):
            print("⏭️  [Node 3] 실행 승인 없음 - 건너뜀")
            return {
                "execution_result": "코드 실행이 승인되지 않았습니다.",
                "status": "skipped"
            }
        
        print("🚀 [Node 3] 코드 실행 중...")
        
        # 수정된 코드가 있으면 사용
        code_to_execute = state.get('code_modified') or state.get('generated_code', '')
        
        if not code_to_execute:
            return {
                "execution_result": "실행할 코드가 없습니다.",
                "errors": ["코드 없음"],
                "status": "error"
            }
        
        # 코드 실행
        try:
            result = execute_python_code_tool.invoke({
                "code": code_to_execute,
                "timeout": 30
            })
            
            print("✅ 코드 실행 완료")
            
            # 에러 확인
            errors = []
            if "❌" in result or "에러" in result:
                errors.append(result)
            
            return {
                "execution_result": result,
                "errors": errors,
                "status": "executed"
            }
            
        except Exception as e:
            error_msg = f"코드 실행 중 오류 발생: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "execution_result": error_msg,
                "errors": [error_msg],
                "status": "error"
            }
    
    def should_retry(self, state: CursorStyleAgentState) -> Literal["retry", "done"]:
        """Gate 함수: 재시도 여부 결정"""
        errors = state.get('errors', [])
        iteration_count = state.get('iteration_count', 0)
        
        # 최대 3회까지 재시도
        if iteration_count >= 3:
            print("⚠️  최대 반복 횟수(3회) 도달, 완료 처리")
            return "done"
        
        # 에러가 있고 실행 승인된 경우 재시도
        if errors and state.get('execution_approved', False):
            print(f"❌ {len(errors)}개의 에러 발견, 재시도 진행")
            return "retry"
        
        # 완료
        return "done"
    
    def format_output_node(self, state: CursorStyleAgentState) -> CursorStyleAgentState:
        """노드 4: 출력 포맷팅"""
        print("📝 [Node 4] 출력 포맷팅 중...")
        
        final_status = "완료"
        if state.get('errors'):
            final_status = "부분 완료 (에러 발생)"
        elif not state.get('execution_approved', False):
            final_status = "실행 거부됨"
        
        return {
            "status": final_status
        }
    
    def build_graph(self):
        """LangGraph 구성"""
        print("🏗️  LangGraph 구성 중...")
        
        builder = StateGraph(CursorStyleAgentState)
        
        # 노드 추가
        builder.add_node("generate_code", self.generate_code_node)
        builder.add_node("request_permission", self.request_permission_node)
        builder.add_node("execute_code", self.execute_code_node)
        builder.add_node("format_output", self.format_output_node)
        
        # 엣지 추가
        builder.add_edge(START, "generate_code")
        builder.add_edge("generate_code", "request_permission")
        builder.add_edge("request_permission", "execute_code")
        
        # 조건부 분기: 재시도 또는 완료
        builder.add_conditional_edges(
            "execute_code",
            self.should_retry,
            {
                "retry": "generate_code",  # 재시도: 다시 코드 생성
                "done": "format_output"  # 완료: 출력 포맷팅
            }
        )
        
        builder.add_edge("format_output", END)
        
        # 그래프 컴파일 (checkpointer 필수)
        self.graph = builder.compile(checkpointer=self.checkpointer)
        
        print("✅ LangGraph 구성 완료")
    
    def generate_response(self, query: str, thread_id: str = None) -> str:
        """쿼리에 대한 응답 생성
        
        Args:
            query: 사용자 쿼리
            thread_id: 스레드 ID (None이면 자동 생성)
        
        Returns:
            응답 문자열
        """
        if not self.graph:
            return "❌ 그래프가 초기화되지 않았습니다."
        
        # Thread ID 생성
        if thread_id is None:
            thread_id = f"cursor_style_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        config = {"configurable": {"thread_id": thread_id}}
        
        print(f"\n{'=' * 60}")
        print(f"🚀 Cursor 스타일 에이전트 시작")
        print(f"📋 Thread ID: {thread_id}")
        print(f"{'=' * 60}")
        
        # 초기 State 설정
        initial_state = {
            "user_query": query,
            "generated_code": "",
            "execution_approved": False,
            "execution_result": "",
            "code_modified": "",
            "errors": [],
            "iteration_count": 0,
            "llm_calls": 0,
            "status": "start",
            "messages": []
        }
        
        # 그래프 실행
        try:
            result = self.graph.invoke(initial_state, config=config)
            return self._format_response(result)
        except Exception as e:
            return f"❌ 그래프 실행 중 오류 발생: {str(e)}"
    
    def stream_with_permission(self, query: str, thread_id: str = None):
        """스트리밍 모드로 실행 (실시간 피드백 및 권한 요청)
        
        Args:
            query: 사용자 쿼리
            thread_id: 스레드 ID (None이면 자동 생성)
        """
        if not self.graph:
            print("❌ 그래프가 초기화되지 않았습니다.")
            return
        
        # Thread ID 생성
        if thread_id is None:
            thread_id = f"cursor_style_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        config = {"configurable": {"thread_id": thread_id}}
        
        print(f"\n{'=' * 60}")
        print(f"🚀 Cursor 스타일 에이전트 시작 (스트리밍 모드)")
        print(f"📋 Thread ID: {thread_id}")
        print(f"{'=' * 60}")
        
        # 초기 State 설정
        initial_state = {
            "user_query": query,
            "generated_code": "",
            "execution_approved": False,
            "execution_result": "",
            "code_modified": "",
            "errors": [],
            "iteration_count": 0,
            "llm_calls": 0,
            "status": "start",
            "messages": []
        }
        
        # 스트리밍 실행
        try:
            for step in self.graph.stream(initial_state, config=config, stream_mode="values"):
                # 상태 업데이트 표시
                if "status" in step:
                    status = step["status"]
                    if status == "code_generated":
                        print(f"\n✅ 코드 생성 완료")
                    elif status == "executed":
                        print(f"\n✅ 코드 실행 완료")
                
                # interrupt 발생 시 처리
                if "__interrupt__" in step:
                    interrupt_data = step["__interrupt__"][0]
                    interrupt_value = interrupt_data.value if hasattr(interrupt_data, 'value') else interrupt_data
                    
                    code = interrupt_value.get("code", "")
                    
                    print("\n" + "=" * 60)
                    print("📝 실행할 코드:")
                    print("=" * 60)
                    print(code)
                    print("=" * 60)
                    print("\n⚠️  이 코드를 실행하시겠습니까?")
                    
                    # 사용자 입력 받기
                    user_input = input("(y/approve/n/reject/e/edit): ").strip().lower()
                    
                    # Command로 재개
                    if user_input in ["y", "approve", ""]:
                        # 승인
                        self.graph.invoke(
                            Command(resume={"action": "approve"}),
                            config=config
                        )
                        print("✅ 코드 실행 승인됨")
                    elif user_input in ["e", "edit"]:
                        # 수정
                        print("\n수정된 코드를 입력하세요 (여러 줄 입력 후 빈 줄 입력):")
                        modified_lines = []
                        while True:
                            line = input()
                            if line.strip() == "":
                                break
                            modified_lines.append(line)
                        modified_code = "\n".join(modified_lines)
                        
                        self.graph.invoke(
                            Command(resume={"action": "edit", "modified_code": modified_code}),
                            config=config
                        )
                        print("✅ 코드 수정됨")
                    else:
                        # 거부
                        self.graph.invoke(
                            Command(resume={"action": "reject"}),
                            config=config
                        )
                        print("❌ 코드 실행 거부됨")
                        return
                
                # 실행 결과 표시
                if "execution_result" in step:
                    result = step["execution_result"]
                    if result:
                        print(f"\n📊 실행 결과:")
                        print(result)
            
            print(f"\n{'=' * 60}")
            print("✅ 완료")
            print(f"{'=' * 60}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
    
    def _format_response(self, result: CursorStyleAgentState) -> str:
        """응답 포맷팅"""
        output = f"""
{'=' * 60}
📝 Cursor 스타일 에이전트 결과
{'=' * 60}

💻 생성된 코드:
{'-' * 60}
{result.get('generated_code', '')}

📊 실행 결과:
{'-' * 60}
{result.get('execution_result', '실행되지 않음')}

📈 통계:
{'-' * 60}
- 사용자 요청: {result.get('user_query', '')}
- LLM 호출: {result.get('llm_calls', 0)}회
- 반복 횟수: {result.get('iteration_count', 0)}회
- 상태: {result.get('status', '')}
- 실행 승인: {'✅' if result.get('execution_approved', False) else '❌'}
- 에러 수: {len(result.get('errors', []))}

{'=' * 60}
"""
        return output
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return (self.model is not None and 
                self.graph is not None and 
                self.checkpointer is not None)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "Cursor Style Agent",
                "model": self.model_name,
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "Cursor Style Agent",
            "model": self.model_name,
            "architecture": "LangGraph + Interrupt 기반 실시간 코드 실행",
            "ready": self.is_ready(),
            "permission_request_enabled": self.enable_permission_request,
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> generate_code -> request_permission (interrupt) -> execute_code -> [retry | done] -> format_output -> END",
            "features": [
                "실시간 코드 생성",
                "터미널 권한 요청 (interrupt)",
                "즉시 코드 실행",
                "코드 수정 지원",
                "에러 기반 자동 재시도",
                "스트리밍 모드 지원"
            ]
        }


