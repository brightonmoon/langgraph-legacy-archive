import pytest
from langchain_core.messages import AIMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableLambda

from src.agents.sub_agents.rag_agent import create_rag_agent_graph
from src.agents.sub_agents.rag_agent.data_utils import load_csv_rows_as_documents


@pytest.fixture(scope="module")
def csv_documents():
    return load_csv_rows_as_documents(
        "DESeq2_counts.csv",
        limit=200,
    )


@pytest.fixture(scope="module")
def mock_llm():
    def _invoke(messages):
        if isinstance(messages, ChatPromptValue):
            serialized = messages.to_messages()
        elif isinstance(messages, list):
            serialized = messages
        else:
            serialized = [messages]

        last_content = serialized[-1].content if serialized else ""
        return AIMessage(content=f"[mock-response] {last_content}")

    return RunnableLambda(_invoke)


def test_spock2_row_roundtrip(csv_documents, mock_llm, tmp_path):
    graph = create_rag_agent_graph(llm=mock_llm, vectorstore_dir=str(tmp_path))

    result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "SPOCK2 유전자 행을 그대로 보여줘.",
                }
            ],
            "ingest_inputs": {
                "documents": csv_documents,
                "chunk_size": 2000,
                "chunk_overlap": 100,
            },
        }
    )

    retrieved = result.get("retrieved_documents", [])
    assert retrieved, "RAG 검색 결과가 비어 있습니다."
    concatenated = "\n".join(doc["content"] for doc in retrieved)

    assert "GeneID: SPOCK2" in concatenated
    assert "Norm_PI_T_CTRL_1: 21.474198886245" in concatenated
    assert "Norm_PI_U_CTRL_1: 48927.506114235" in concatenated




