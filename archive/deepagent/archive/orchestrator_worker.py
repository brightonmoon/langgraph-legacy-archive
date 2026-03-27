"""
DeepAgent 기반 Orchestrator-Worker 패턴 구현

아키텍처:
┌─────────────────────────────────────────┐
│  LangGraph Orchestrator (상위 워크플로우) │
│  - analyze_task: 작업 분해               │
│  - delegate_to_worker: Worker 위임       │
│  - synthesize_results: 결과 통합         │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  DeepAgent Worker (CompiledSubAgent)    │
│  - Planning, File System, Subagents      │
│  - 실제 작업 수행                         │
└─────────────────────────────────────────┘

구조 설명:
1. 상위: LangGraph로 Orchestrator 워크플로우 구현
2. 하위: DeepAgent를 CompiledSubAgent로 래핑하여 Worker로 사용
3. 통합: LangGraph 노드에서 DeepAgent Worker를 subgraph로 호출
"""

import os
from typing import TypedDict, Annotated, Literal, Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from deepagents import create_deep_agent, CompiledSubAgent
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper


def setup_langsmith_disabled():
    """LangSmith 완전 비활성화"""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGSMITH_API_KEY"] = ""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


# Orchestrator-Worker State 정의
class OrchestratorWorkerState(TypedDict):
    """Orchestrator-Worker 패턴의 상태"""
    messages: Annotated[list, add_messages]
    user_query: str  # 사용자 쿼리
    task_description: str  # 분석된 작업 설명
    subtasks: List[Dict[str, Any]]  # 분해된 하위 작업들
    worker_results: Dict[str, Any]  # Worker별 결과 {worker_name: result}
    final_result: str  # 최종 통합 결과
    current_task_index: int  # 현재 처리 중인 작업 인덱스
    llm_calls: int  # LLM 호출 횟수
    status: str  # 현재 상태 (analyzing, delegating, synthesizing, completed)


class OrchestratorWorkerAgent:
    """Orchestrator-Worker 패턴 구현
    
    구조:
    - Orchestrator (LangGraph): 작업 분해 및 Worker 관리
    - Workers (DeepAgent as CompiledSubAgent): 실제 작업 수행
    """
    
    def __init__(
        self,
        orchestrator_model: Optional[str] = None,
        worker_model: Optional[str] = None,
        use_ollama: bool = True
    ):
        """Orchestrator-Worker 에이전트 초기화
        
        Args:
            orchestrator_model: Orchestrator에 사용할 모델명 (기본값: "gpt-oss:120b-cloud")
            worker_model: Worker(DeepAgent)에 사용할 로컬 Ollama 모델명 
                         (예: "qwen2.5-coder:latest", "codegemma:latest", "gemma3:4b", "deepseek-r1:latest")
            use_ollama: Ollama 모델 사용 여부
        """
        load_dotenv()
        setup_langsmith_disabled()
        
        # Orchestrator 모델 설정 (gpt-oss:120b-cloud - Cloud 모델)
        if orchestrator_model is None:
            orchestrator_model = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
        
        # Orchestrator는 gpt-oss:120b-cloud 사용 (API 키 필요)
        ollama_api_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_api_key:
            raise ValueError(
                "OLLAMA_API_KEY가 설정되지 않았습니다. "
                "상위 Orchestrator(gpt-oss:120b-cloud)를 사용하려면 OLLAMA_API_KEY가 필요합니다."
            )
        
        self.orchestrator_model = init_chat_model(
            f"ollama:{orchestrator_model}",
            api_key=ollama_api_key,
            temperature=0.7
        )
        
        # Worker 모델 설정 (DeepAgent용) - 로컬 Ollama 모델 사용
        if worker_model is None:
            worker_model = "qwen2.5-coder:latest"  # 기본값
        
        # DeepAgent를 Worker로 생성 (로컬 Ollama 모델 사용)
        # ChatOllama를 직접 전달하여 API 키 없이 사용
        worker_chat_model = ChatOllama(
            model=worker_model,
            temperature=0.7
        )
        
        self.worker_agent = create_deep_agent(
            model=worker_chat_model,
            system_prompt="""당신은 전문 Worker입니다. 
            Orchestrator로부터 받은 작업을 정확하고 효율적으로 수행하세요.
            작업이 완료되면 결과만 반환하세요."""
        )
        
        # 사용 가능한 모델 목록 저장 (참고용)
        self.available_models = {
            "gemma3:4b": "gemma3:4b",
            "deepseek-r1:latest": "deepseek-r1:latest",
            "codegemma:latest": "codegemma:latest",
            "qwen2.5-coder:latest": "qwen2.5-coder:latest"
        }
        
        print("✅ Orchestrator-Worker 에이전트 초기화 완료")
        print(f"   Orchestrator 모델: {orchestrator_model} (Cloud - API 키 필요)")
        print(f"   Worker (DeepAgent) 모델: {worker_model} (로컬 Ollama)")
        print(f"   구조: LangGraph Orchestrator → DeepAgent Worker (subgraph)")
        print(f"   사용 가능한 Worker 모델: {', '.join(self.available_models.keys())}")
        
        # LangGraph 그래프 구성
        self.graph = None
        self.build_graph()
    
    def analyze_task(self, state: OrchestratorWorkerState) -> OrchestratorWorkerState:
        """Orchestrator 노드 1: 작업 분석 및 분해"""
        print("🔍 [Orchestrator] 작업 분석 및 분해 중...")
        
        query = state['user_query']
        
        system_message = SystemMessage(
            content="""당신은 Orchestrator입니다. 복잡한 작업을 분석하고 
            효율적으로 수행할 수 있는 하위 작업으로 분해하세요."""
        )
        
        human_message = HumanMessage(
            content=f"""다음 작업을 분석하고 하위 작업으로 분해하세요:

{query}

분해된 작업을 JSON 형식으로 반환하세요:
{{
    "subtasks": [
        {{"id": 1, "task": "작업1", "description": "설명1"}},
        {{"id": 2, "task": "작업2", "description": "설명2"}}
    ]
}}"""
        )
        
        response = self.orchestrator_model.invoke([system_message, human_message])
        
        # JSON 파싱 (간단한 예시)
        import json
        try:
            subtasks_data = json.loads(response.content)
            subtasks = subtasks_data.get("subtasks", [])
        except:
            # JSON 파싱 실패 시 기본 구조
            subtasks = [
                {"id": 1, "task": "작업1", "description": response.content}
            ]
        
        return {
            "task_description": response.content,
            "subtasks": subtasks,
            "status": "analyzing",
            "llm_calls": state.get("llm_calls", 0) + 1
        }
    
    def delegate_to_worker(self, state: OrchestratorWorkerState) -> OrchestratorWorkerState:
        """Orchestrator 노드 2: Worker에게 작업 위임
        
        DeepAgent Worker를 subgraph로 호출하는 방식:
        - DeepAgent는 이미 compiled LangGraph이므로 직접 invoke 가능
        - 향후 LangGraph의 add_node로 subgraph로 추가 가능
        """
        print("👥 [Orchestrator] Worker에게 작업 위임 중...")
        print("   📌 DeepAgent Worker를 subgraph로 호출")
        
        subtasks = state.get("subtasks", [])
        worker_results = {}
        
        # 각 하위 작업을 Worker(DeepAgent)에게 위임
        for i, subtask in enumerate(subtasks):
            task_desc = subtask.get("description", subtask.get("task", ""))
            worker_name = f"worker_{i+1}"
            
            print(f"   → {worker_name}에게 작업 위임: {task_desc[:50]}...")
            
            # Worker (DeepAgent - 이미 compiled LangGraph) 호출
            # DeepAgent는 내부적으로 Planning, File System, Subagents 기능 제공
            worker_result = self.worker_agent.invoke({
                "messages": [{"role": "user", "content": task_desc}]
            })
            
            # 결과 추출 (DeepAgent의 messages 형식)
            if worker_result.get("messages"):
                result_content = worker_result["messages"][-1].content
            else:
                result_content = "작업 수행 완료"
            
            # DeepAgent 내부 LLM 호출 횟수 추정
            # AIMessage가 있으면 LLM 호출이 있었던 것
            messages = worker_result.get("messages", [])
            
            # 실제 LLM 호출 횟수 추정 (AIMessage 개수로)
            estimated_worker_llm_calls = 0
            for msg in messages:
                # AIMessage 또는 assistant role 메시지가 있으면 LLM 호출
                if hasattr(msg, 'role'):
                    if msg.role == 'assistant':
                        estimated_worker_llm_calls += 1
                elif isinstance(msg, dict):
                    if msg.get('role') == 'assistant':
                        estimated_worker_llm_calls += 1
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    estimated_worker_llm_calls += 1
            
            # 최소 1회는 보장 (Worker가 호출되었으므로)
            if estimated_worker_llm_calls == 0:
                estimated_worker_llm_calls = 1
            
            worker_results[worker_name] = {
                "subtask": subtask,
                "result": result_content,
                "worker_type": "DeepAgent",
                # DeepAgent 내부 상태 추적을 위한 추가 정보
                "message_count": len(worker_result.get("messages", [])),
                "estimated_llm_calls": estimated_worker_llm_calls,  # 실제 LLM 호출 추정 횟수
                "messages": [
                    {
                        "role": getattr(msg, "role", type(msg).__name__),
                        "content": getattr(msg, "content", str(msg))[:500]  # 처음 500자만
                    }
                    for msg in worker_result.get("messages", [])[:5]  # 최대 5개만
                ] if worker_result.get("messages") else []
            }
            
            print(f"   ✅ {worker_name} 완료 (예상 LLM 호출: {estimated_worker_llm_calls}회)")
        
        # 전체 Worker LLM 호출 횟수 합산
        total_worker_llm_calls = sum(
            result.get("estimated_llm_calls", 1) 
            for result in worker_results.values()
        )
        
        return {
            "worker_results": worker_results,
            "status": "delegating",
            "llm_calls": state.get("llm_calls", 0) + total_worker_llm_calls
        }
    
    def synthesize_results(self, state: OrchestratorWorkerState) -> OrchestratorWorkerState:
        """Orchestrator 노드 3: Worker 결과 통합"""
        print("📦 [Orchestrator] 결과 통합 중...")
        
        worker_results = state.get("worker_results", {})
        task_description = state.get("task_description", "")
        
        # 결과 통합 프롬프트
        system_message = SystemMessage(
            content="""당신은 Orchestrator입니다. 여러 Worker의 결과를 
            통합하여 최종 결과를 생성하세요."""
        )
        
        results_summary = "\n\n".join([
            f"**{name}**:\n{result['result']}"
            for name, result in worker_results.items()
        ])
        
        human_message = HumanMessage(
            content=f"""다음 작업의 결과를 통합하세요:

**원본 작업**: {task_description}

**Worker 결과들**:
{results_summary}

통합된 최종 결과를 생성하세요."""
        )
        
        response = self.orchestrator_model.invoke([system_message, human_message])
        
        return {
            "final_result": response.content,
            "status": "completed",
            "llm_calls": state.get("llm_calls", 0) + 1
        }
    
    def build_graph(self):
        """LangGraph 그래프 구성: Orchestrator-Worker 패턴"""
        try:
            graph = StateGraph(OrchestratorWorkerState)
            
            # Orchestrator 노드들
            graph.add_node("analyze_task", self.analyze_task)
            graph.add_node("delegate_to_worker", self.delegate_to_worker)
            graph.add_node("synthesize_results", self.synthesize_results)
            
            # 엣지 구성
            graph.add_edge(START, "analyze_task")
            graph.add_edge("analyze_task", "delegate_to_worker")
            graph.add_edge("delegate_to_worker", "synthesize_results")
            graph.add_edge("synthesize_results", END)
            
            # 그래프 컴파일
            self.graph = graph.compile()
            
            print("✅ Orchestrator-Worker 그래프 구성 완료")
            print("   구조: START → analyze_task → delegate_to_worker → synthesize_results → END")
            
        except Exception as e:
            print(f"❌ 그래프 구성 중 오류 발생: {str(e)}")
            self.graph = None
    
    def invoke(self, query: str) -> Dict[str, Any]:
        """쿼리 실행"""
        if not self.graph:
            return {"error": "그래프가 초기화되지 않았습니다."}
        
        try:
            initial_state = {
                "messages": [],
                "user_query": query,
                "task_description": "",
                "subtasks": [],
                "worker_results": {},
                "final_result": "",
                "current_task_index": 0,
                "llm_calls": 0,
                "status": "pending"
            }
            
            result = self.graph.invoke(initial_state)
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        return {
            "type": "OrchestratorWorkerAgent",
            "architecture": "LangGraph Orchestrator + DeepAgent Workers",
            "orchestrator_model": str(self.orchestrator_model),
            "worker_type": "DeepAgent (CompiledSubAgent)",
            "graph_ready": self.graph is not None,
            "pattern": "Orchestrator-Worker",
            "features": [
                "작업 분석 및 분해 (Orchestrator)",
                "Worker에게 작업 위임",
                "결과 통합 및 최종 생성",
                "DeepAgent를 Worker로 활용"
            ]
        }

