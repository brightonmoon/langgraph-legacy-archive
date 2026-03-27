import pytest
from langchain_core.messages import AIMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableLambda

from src.agents.sub_agents.rag_agent import create_rag_agent_graph


@pytest.fixture
def mock_llm():
    def _invoke(messages):
        # 마지막 Human 메시지를 그대로 에코하여 예측 가능하게 유지
        if isinstance(messages, ChatPromptValue):
            serialized = messages.to_messages()
        elif isinstance(messages, list):
            serialized = messages
        else:
            serialized = [messages]

        last_content = serialized[-1].content if serialized else ""
        return AIMessage(content=f"mock-response::{last_content}")

    return RunnableLambda(_invoke)


def test_rag_agent_ingests_and_answers(tmp_path, mock_llm):
    graph = create_rag_agent_graph(llm=mock_llm, vectorstore_dir=str(tmp_path))

    ingest_inputs = {
        "texts": [
            "LangGraph는 LangChain 워크플로우를 위한 상태 기반 오케스트레이션 프레임워크입니다.",
            "Traditional RAG는 벡터 스토어에서 문서를 검색한 뒤 답변을 생성합니다.",
        ]
    }
    user_messages = [{"role": "user", "content": "LangGraph는 무엇인가요?"}]

    result = graph.invoke({"messages": user_messages, "ingest_inputs": ingest_inputs})

    assert result["vectorstore_id"]
    assert result["metadata"]["ingest_status"] == "completed"
    assert result["metadata"]["retrieval_status"] == "completed"
    assert "final_answer" in result
    assert "LangGraph" in result["final_answer"]


def test_rag_agent_handles_missing_index(tmp_path, mock_llm):
    graph = create_rag_agent_graph(llm=mock_llm, vectorstore_dir=str(tmp_path))
    user_messages = [{"role": "user", "content": "컨텍스트가 없으면 어떻게 되나요?"}]

    result = graph.invoke({"messages": user_messages})

    assert result["metadata"]["retrieval_status"] == "vectorstore_missing"
    assert "관련 컨텍스트" in result["final_answer"]

