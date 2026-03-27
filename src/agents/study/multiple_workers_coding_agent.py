"""
Multiple Workers Coding Agent - 여러 Worker를 병렬로 사용하여 코드 품질 향상

Architecture:
- Orchestrator: gpt-oss:120b-cloud (작업 분석 및 품질 평가)
- Workers: qwen2.5-coder:latest, codegemma:latest (병렬 코드 생성)
"""

# 표준 라이브러리
import json
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal

# 서드파티
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 로컬 (다른 패키지 - 절대 import)
from src.agents.base import BaseAgent
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


# State 정의
class MultipleWorkersCodingAgentState(TypedDict):
    """Multiple Workers 코딩 에이전트의 상태"""
    # 입력
    user_query: str  # 사용자 요청
    task_description: str  # 분석된 작업 설명
    
    # 다중 Worker 결과
    code_candidates: dict[str, str]  # {model_name: code}
    code_scores: dict[str, float]  # {model_name: score}
    selected_model: str  # 선택된 모델
    selected_code: str  # 선택된 코드
    
    # 작업 데이터
    test_code: str  # 테스트 코드
    test_result: str  # 테스트 실행 결과
    errors: list[str]  # 발생한 에러 목록
    
    # 제어 변수
    iteration_count: int  # 반복 횟수 (무한 루프 방지)
    llm_calls: int  # LLM 호출 횟수
    status: str  # 현재 상태
    
    # 메시지 히스토리
    messages: Annotated[list, add_messages]


class MultipleWorkersCodingAgent(BaseAgent):
    """Multiple Workers 코딩 에이전트
    
    Orchestrator (gpt-oss:120b-cloud): 작업 분석 및 코드 품질 평가
    Workers (qwen2.5-coder:latest, codegemma:latest): 병렬 코드 생성
    
    워크플로우:
    1. 요구사항 분석 (Orchestrator)
    2. 병렬 코드 생성 (Worker 1: qwen2.5-coder, Worker 2: codegemma)
    3. 코드 품질 평가 (Orchestrator)
    4. 최적 코드 선택
    5. 테스트 코드 생성 (선택된 Worker)
    6. 코드 검증 (Orchestrator)
    7. 에러 수정 (필요시)
    8. 결과 반환
    """
    
    def __init__(self, model_name: str = None):
        """Agent 초기화
        
        Args:
            model_name: 사용할 모델명 (예: "gpt-oss:120b-cloud", "kimi-k2:1t-cloud")
        """
        setup_langsmith_disabled()
        
        # Orchestrator 모델 (Cloud) - 전체 흐름 제어 및 품질 평가
        model_str = model_name or os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
        if model_str and not model_str.startswith("ollama:"):
            model_str = f"ollama:{model_str}"
        
        self.orchestrator = init_chat_model_helper(
            model_name=model_str,
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        self.model_name = model_name or "gpt-oss:120b-cloud"
        
        # Worker 모델들 (Local) - 병렬 코드 생성
        self.worker_qwen = ChatOllama(model="qwen2.5-coder:latest", temperature=0.7)
        self.worker_codegemma = ChatOllama(model="codegemma:latest", temperature=0.7)
        
        print(f"✅ Worker 모델 로드 완료:")
        print(f"   - qwen2.5-coder:latest")
        print(f"   - codegemma:latest")
        
        self.graph = None
        self.build_graph()
    
    def analyze_requirements(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 1: 요구사항 분석 (Orchestrator 사용)"""
        print("🔍 [Node 1] 요구사항 분석 중... (Orchestrator: gpt-oss:120b-cloud)")
        
        user_query = state['user_query']
        
        # Orchestrator로 요구사항 분석
        system_message = SystemMessage(
            content="당신은 코딩 요청을 분석하는 전문가입니다. 명확하고 구체적인 작업 설명을 작성하세요."
        )
        
        human_message = HumanMessage(
            content=f"""
다음 코딩 요청을 분석하고 명확한 작업 설명을 작성하세요:

요청: {user_query}

다음 정보를 포함하세요:
- 작업 목표
- 필요한 입력/출력
- 제약 조건
- 예상 함수 구조
"""
        )
        
        response = self.orchestrator.invoke([system_message, human_message])
        
        print(f"✅ 분석 완료")
        
        return {
            "task_description": response.content,
            "status": "analyzing",
            "llm_calls": state.get("llm_calls", 0) + 1,
            "messages": [response]
        }
    
    def generate_code_parallel(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 2: 병렬 코드 생성 (두 Worker 동시 실행)"""
        print("💻 [Node 2] 병렬 코드 생성 중...")
        print("   - Worker 1: qwen2.5-coder:latest")
        print("   - Worker 2: codegemma:latest")
        
        task_description = state['task_description']
        errors = state.get('errors', [])
        
        # 에러가 있으면 수정 요청, 없으면 생성 요청
        if errors:
            print(f"   🔧 에러 수정 중: {len(errors)}개")
            prompt = f"""
다음 코드에 에러가 있습니다. 코드를 수정해주세요:

작업: {task_description}

코드:
{state.get('selected_code', '')}

에러:
{chr(10).join(errors)}

수정된 코드만 출력하세요 (설명 없이 코드만).
"""
        else:
            print("   ✨ 새로운 코드 생성")
            prompt = f"""
다음 작업을 수행하는 Python 코드를 작성하세요:

{task_description}

요구사항:
- 함수 이름과 docstring 포함
- 주석 추가
- Python best practices 준수
- 코드만 출력 (설명 없이)
"""
        
        # 두 Worker 모델로 병렬 코드 생성
        human_message = HumanMessage(content=prompt)
        
        # Worker 1: qwen2.5-coder
        print("   🤖 qwen2.5-coder 실행 중...")
        response_qwen = self.worker_qwen.invoke([human_message])
        code_qwen = response_qwen.content
        
        # Worker 2: codegemma
        print("   🤖 codegemma 실행 중...")
        response_codegemma = self.worker_codegemma.invoke([human_message])
        code_codegemma = response_codegemma.content
        
        # 결과 저장
        code_candidates = {
            "qwen2.5-coder": code_qwen,
            "codegemma": code_codegemma
        }
        
        print(f"✅ 병렬 코드 생성 완료")
        
        return {
            "code_candidates": code_candidates,
            "status": "generating_parallel",
            "llm_calls": state.get("llm_calls", 0) + 2,  # 두 모델 호출
            "iteration_count": state.get("iteration_count", 0) + 1,
            "messages": [response_qwen, response_codegemma]
        }
    
    def evaluate_code_quality(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 3: 코드 품질 평가 (Orchestrator 사용)"""
        print("📊 [Node 3] 코드 품질 평가 중... (Orchestrator: gpt-oss:120b-cloud)")
        
        code_candidates = state['code_candidates']
        task_description = state['task_description']
        
        # Orchestrator로 코드 품질 평가
        evaluation_prompt = f"""
다음 2개의 코드를 평가하고 각각에 점수를 매기세요 (0-100):

작업 설명:
{task_description}

코드 1 (qwen2.5-coder):
{code_candidates['qwen2.5-coder']}

코드 2 (codegemma):
{code_candidates['codegemma']}

평가 기준:
- 정확성 (40점): 요구사항을 정확히 충족하는가?
- 가독성 (30점): 코드가 읽기 쉽고 이해하기 쉬운가?
- 최적화 (30점): 효율적이고 Python best practices를 따르는가?

JSON 형식으로 응답하세요:
{{
    "qwen2.5-coder": 85,
    "codegemma": 90,
    "reason": "선택 이유 설명"
}}
"""
        
        print("   🔍 Orchestrator 평가 중...")
        human_message = HumanMessage(content=evaluation_prompt)
        response = self.orchestrator.invoke([human_message])
        
        # JSON 파싱
        try:
            # JSON 추출 (코드 블록 제거)
            content = response.content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            scores_data = json.loads(content)
            
            # 점수 추출
            scores = {
                "qwen2.5-coder": float(scores_data.get("qwen2.5-coder", 0)),
                "codegemma": float(scores_data.get("codegemma", 0))
            }
            
            # 최고 점수 모델 선택
            selected_model = max(scores, key=scores.get)
            selected_code = code_candidates[selected_model]
            
            print(f"   ✅ 평가 완료:")
            print(f"      - qwen2.5-coder: {scores['qwen2.5-coder']:.1f}점")
            print(f"      - codegemma: {scores['codegemma']:.1f}점")
            print(f"      - 선택된 모델: {selected_model}")
            
        except Exception as e:
            print(f"   ⚠️ JSON 파싱 실패, 기본값 사용: {str(e)}")
            # 기본값: 첫 번째 모델 선택
            selected_model = "qwen2.5-coder"
            selected_code = code_candidates[selected_model]
            scores = {
                "qwen2.5-coder": 50,
                "codegemma": 50
            }
        
        return {
            "code_scores": scores,
            "selected_model": selected_model,
            "selected_code": selected_code,
            "status": "evaluating",
            "llm_calls": state.get("llm_calls", 0) + 1,
            "messages": [response]
        }
    
    def generate_tests(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 4: 테스트 코드 생성 (선택된 Worker 사용)"""
        print(f"🧪 [Node 4] 테스트 코드 생성 중... (Worker: {state['selected_model']})")
        
        task_description = state['task_description']
        code = state['selected_code']
        selected_model = state['selected_model']
        
        prompt = f"""
다음 코드에 대한 테스트 코드를 작성하세요:

작업: {task_description}

코드:
{code}

요구사항:
- 다양한 케이스 포함 (정상 케이스, edge case)
- 간단한 assert 문 사용
- 코드만 출력 (설명 없이)
"""
        
        # 선택된 Worker 모델로 테스트 생성
        worker = self.worker_qwen if selected_model == "qwen2.5-coder" else self.worker_codegemma
        
        human_message = HumanMessage(content=prompt)
        response = worker.invoke([human_message])
        
        print(f"✅ 테스트 코드 생성 완료")
        
        return {
            "test_code": response.content,
            "llm_calls": state.get("llm_calls", 0) + 1,
            "messages": [response]
        }
    
    def validate_code(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 5: 코드 검증 (Orchestrator 사용)"""
        print("🔎 [Node 5] 코드 검증 중... (Orchestrator: gpt-oss:120b-cloud)")
        
        code = state['selected_code']
        test_code = state['test_code']
        
        # Orchestrator로 코드 검증
        prompt = f"""
다음 코드와 테스트를 검증하고 테스트 결과를 예측하세요:

코드:
{code}

테스트:
{test_code}

테스트를 실행하면 어떤 결과가 나올지 예측하세요.
에러가 있으면 에러 메시지를, 통과하면 "✅ 모든 테스트 통과"라고 답하세요.
"""
        
        human_message = HumanMessage(content=prompt)
        response = self.orchestrator.invoke([human_message])
        
        # 에러 추출 (간단한 방법)
        result_text = response.content
        errors = []
        
        if "에러" in result_text or "Error" in result_text or "error" in result_text.lower():
            # Orchestrator에게 에러 내용 추출 요청
            extract_prompt = f"""
다음 텍스트에서 에러 메시지를 추출하세요:

{result_text}

에러가 있다면 에러 메시지를, 없다면 "없음"이라고 답하세요.
"""
            error_response = self.orchestrator.invoke([HumanMessage(content=extract_prompt)])
            if "없음" not in error_response.content:
                errors.append(error_response.content)
        
        print(f"✅ 검증 완료: {'에러 있음' if errors else '통과'}")
        
        return {
            "test_result": result_text,
            "errors": errors,
            "status": "testing",
            "llm_calls": state.get("llm_calls", 0) + 1,
            "messages": [response]
        }
    
    def should_fix_errors(self, state: MultipleWorkersCodingAgentState) -> Literal["fix", "done"]:
        """Gate 함수: 에러 수정 여부 결정"""
        errors = state.get('errors', [])
        iteration_count = state.get('iteration_count', 0)
        
        # 최대 3회까지 수정 시도
        if iteration_count >= 3:
            print("⚠️ 최대 반복 횟수(3회) 도달, 완료 처리")
            return "done"
        
        # 에러가 있으면 수정
        if errors:
            print(f"❌ {len(errors)}개의 에러 발견, 수정 진행")
            return "fix"
        
        # 에러가 없으면 완료
        print("✅ 테스트 통과")
        return "done"
    
    def format_output(self, state: MultipleWorkersCodingAgentState) -> MultipleWorkersCodingAgentState:
        """노드 6: 출력 포맷팅"""
        print("📝 [Node 6] 출력 포맷팅 중...")
        
        final_status = "완료"
        if state.get('errors'):
            final_status = "부분 완료 (에러 발생)"
        
        return {
            "status": final_status
        }
    
    def build_graph(self):
        """LangGraph 구성"""
        print("🏗️ LangGraph 구성 중...")
        
        builder = StateGraph(MultipleWorkersCodingAgentState)
        
        # 노드 추가
        builder.add_node("analyze_requirements", self.analyze_requirements)
        builder.add_node("generate_code_parallel", self.generate_code_parallel)
        builder.add_node("evaluate_code_quality", self.evaluate_code_quality)
        builder.add_node("generate_tests", self.generate_tests)
        builder.add_node("validate_code", self.validate_code)
        builder.add_node("format_output", self.format_output)
        
        # 순차 실행
        builder.add_edge(START, "analyze_requirements")
        builder.add_edge("analyze_requirements", "generate_code_parallel")
        builder.add_edge("generate_code_parallel", "evaluate_code_quality")
        builder.add_edge("evaluate_code_quality", "generate_tests")
        builder.add_edge("generate_tests", "validate_code")
        
        # 조건부 분기: 에러 수정 또는 완료
        builder.add_conditional_edges(
            "validate_code",
            self.should_fix_errors,
            {
                "fix": "generate_code_parallel",  # 에러 수정: 다시 코드 생성
                "done": "format_output"  # 완료: 출력 포맷팅
            }
        )
        
        builder.add_edge("format_output", END)
        
        # 그래프 컴파일
        self.graph = builder.compile()
        
        print("✅ LangGraph 구성 완료")
    
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        if not self.graph:
            return "❌ 그래프가 초기화되지 않았습니다."
        
        print(f"\n{'=' * 60}")
        print(f"🚀 Multiple Workers 코딩 에이전트 시작")
        print(f"{'=' * 60}")
        
        # 초기 State 설정
        initial_state = {
            "user_query": query,
            "task_description": "",
            "code_candidates": {},
            "code_scores": {},
            "selected_model": "",
            "selected_code": "",
            "test_code": "",
            "test_result": "",
            "errors": [],
            "iteration_count": 0,
            "llm_calls": 0,
            "status": "start",
            "messages": []
        }
        
        # 그래프 실행
        result = self.graph.invoke(initial_state)
        
        # 결과 포맷팅
        return self._format_response(result)
    
    def _format_response(self, result: MultipleWorkersCodingAgentState) -> str:
        """응답 포맷팅"""
        output = f"""
{'=' * 60}
📝 Multiple Workers 코딩 에이전트 결과
{'=' * 60}

🏆 선택된 모델: {result['selected_model']}
📊 모델별 점수:
{'-' * 60}
"""
        
        # 모델별 점수 출력
        for model, score in result.get('code_scores', {}).items():
            marker = "👑" if model == result['selected_model'] else "  "
            output += f"{marker} {model}: {score:.1f}점\n"
        
        output += f"""
💻 생성된 코드 (선택된 모델: {result['selected_model']}):
{'-' * 60}
{result['selected_code']}

🧪 테스트 코드:
{'-' * 60}
{result['test_code']}

🔎 테스트 결과:
{'-' * 60}
{result['test_result']}

📊 통계:
{'-' * 60}
- 사용자 요청: {result['user_query']}
- LLM 호출: {result['llm_calls']}회
- 반복 횟수: {result['iteration_count']}회
- 상태: {result['status']}
- 에러 수: {len(result.get('errors', []))}

{'=' * 60}
"""
        return output
    
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        return (self.orchestrator is not None and 
                self.worker_qwen is not None and 
                self.worker_codegemma is not None and 
                self.graph is not None)
    
    def get_info(self) -> dict:
        """Agent 정보 반환"""
        if not self.graph:
            return {
                "type": "Multiple Workers Coding Agent",
                "model": self.model_name,
                "ready": False,
                "error": "그래프가 초기화되지 않았습니다."
            }
        
        return {
            "type": "Multiple Workers Coding Agent",
            "orchestrator": self.model_name,
            "workers": ["qwen2.5-coder:latest", "codegemma:latest"],
            "architecture": "Multiple Workers 패턴 + Orchestrator 품질 평가",
            "ready": self.is_ready(),
            "nodes": list(self.graph.nodes.keys()),
            "flow": "START -> analyze (Orchestrator) -> generate_parallel (2 Workers) -> evaluate (Orchestrator) -> generate_tests (Selected Worker) -> validate (Orchestrator) -> [fix | done] -> format -> END",
            "features": [
                "Multiple Workers 병렬 코드 생성",
                "Orchestrator 품질 평가",
                "자동 모델 선택",
                "요구사항 분석 (Orchestrator)",
                "테스트 생성 (선택된 Worker)",
                "코드 검증 (Orchestrator)",
                "자동 에러 수정",
                "반복 횟수 제한",
                "로컬 Workers로 비용 절감"
            ]
        }
    
    def chat(self, query: str = None) -> None:
        """대화형 인터페이스"""
        if not self.is_ready():
            print("❌ Agent가 준비되지 않았습니다.")
            return
        
        print(f"\n🤖 Multiple Workers 코딩 에이전트 시작")
        print("=" * 60)
        print("💡 코딩 작업을 요청하세요 (예: Python으로 리스트 정렬 함수 작성)")
        print("💡 두 Worker 모델이 병렬로 코드를 생성하고 품질을 비교합니다.")
        print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
        print("=" * 60)
        
        while True:
            try:
                # 사용자 입력 받기
                if query:
                    user_input = query
                    query = None  # 한 번만 사용
                else:
                    user_input = input("\n👤 코딩 작업을 요청하세요: ").strip()
                
                # 종료 조건 확인
                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
                
                if not user_input:
                    print("❌ 요청을 입력해주세요.")
                    continue
                
                print(f"\n🎯 요청: {user_input}")
                print("-" * 30)
                
                # 응답 생성
                response = self.generate_response(user_input)
                print(response)
                print("-" * 30)
                
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+C로 대화를 종료합니다. 안녕히 가세요!")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {str(e)}")
                print("계속하려면 Enter를 누르세요...")
                try:
                    input()
                except KeyboardInterrupt:
                    print("\n\n👋 대화를 종료합니다. 안녕히 가세요!")
                    break
