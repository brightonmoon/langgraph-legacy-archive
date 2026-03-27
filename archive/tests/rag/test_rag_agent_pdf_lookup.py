"""
PDF 문서에 대한 RAG 에이전트 테스트.

사용법:
    uv run pytest tests/test_rag_agent_pdf_lookup.py -v
    또는
    uv run tests/test_rag_agent_pdf_lookup.py --vectorstore-id ml_small_molecule
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableLambda

from src.agents.sub_agents.rag_agent import create_rag_agent_graph
from src.agents.sub_agents.rag_agent.data_utils import load_pdf_as_documents
from src.agents.sub_agents.rag_agent.vectorstore import VectorStoreManager
from src.utils.paths import get_project_root


@pytest.fixture(scope="module")
def pdf_documents():
    """PDF 문서를 로드하여 Document 객체로 변환"""
    pdf_path = (
        get_project_root()
        / "data"
        / "MACHINE LEARNING FOR SMALL molecule lead optimization.pdf"
    )
    if not pdf_path.exists():
        pytest.skip(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    return load_pdf_as_documents(
        pdf_path,
        chunk_size=1000,
        chunk_overlap=200,
    )


@pytest.fixture(scope="module")
def mock_llm():
    """테스트용 Mock LLM"""

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


def test_pdf_rag_basic_retrieval(pdf_documents, mock_llm, tmp_path):
    """PDF 문서의 기본 검색 테스트"""
    # 벡터스토어 생성
    manager = VectorStoreManager(vectorstore_dir=str(tmp_path))
    vectorstore_id = manager.index_documents(pdf_documents[:50])  # 처음 50개만 테스트

    # RAG 그래프 생성
    graph = create_rag_agent_graph(
        llm=mock_llm,
        vectorstore_dir=str(tmp_path),
    )

    # 질문 실행
    result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is machine learning for small molecule lead optimization?",
                }
            ],
            "vectorstore_id": vectorstore_id,
        }
    )

    # 검색 결과 확인
    retrieved = result.get("retrieved_documents", [])
    assert retrieved, "RAG 검색 결과가 비어 있습니다."
    assert len(retrieved) > 0, "검색된 문서가 없습니다."

    # 검색된 문서에 PDF 관련 내용이 있는지 확인
    concatenated = "\n".join(
        doc.get("content", "") or doc.get("page_content", "") for doc in retrieved
    )
    assert len(concatenated) > 0, "검색된 문서의 내용이 비어 있습니다."


def test_pdf_rag_specific_query(pdf_documents, mock_llm, tmp_path):
    """PDF 문서의 특정 질문에 대한 검색 테스트"""
    # 벡터스토어 생성
    manager = VectorStoreManager(vectorstore_dir=str(tmp_path))
    vectorstore_id = manager.index_documents(pdf_documents[:100])  # 처음 100개만 테스트

    # RAG 그래프 생성
    graph = create_rag_agent_graph(
        llm=mock_llm,
        vectorstore_dir=str(tmp_path),
    )

    # 구체적인 질문 실행
    queries = [
        "What are the key challenges in small molecule lead optimization?",
        "How is machine learning applied to drug discovery?",
        "What methods are used for molecular property prediction?",
    ]

    for query in queries:
        result = graph.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query,
                    }
                ],
                "vectorstore_id": vectorstore_id,
            }
        )

        retrieved = result.get("retrieved_documents", [])
        assert retrieved, f"질문 '{query}'에 대한 검색 결과가 비어 있습니다."


def test_pdf_metadata_preservation(pdf_documents, mock_llm, tmp_path):
    """PDF 문서의 메타데이터 보존 테스트"""
    # 벡터스토어 생성
    manager = VectorStoreManager(vectorstore_dir=str(tmp_path))
    vectorstore_id = manager.index_documents(pdf_documents[:20])

    # 검색 테스트
    retrieved = manager.retrieve_documents(
        vectorstore_id,
        "machine learning",
        search_kwargs={"k": 5},
    )

    assert retrieved, "검색 결과가 비어 있습니다."

    # 메타데이터 확인
    for doc in retrieved:
        assert hasattr(doc, "metadata"), "문서에 메타데이터가 없습니다."
        metadata = doc.metadata
        assert "source" in metadata or "file_type" in metadata, "소스 정보가 없습니다."


def main():
    """CLI로 직접 실행할 때 사용"""
    parser = argparse.ArgumentParser(description="PDF RAG 테스트")
    parser.add_argument(
        "--vectorstore-id",
        type=str,
        default="ml_small_molecule",
        help="벡터스토어 ID",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is machine learning for small molecule lead optimization?",
        help="테스트할 질문",
    )

    args = parser.parse_args()

    # 벡터스토어 매니저 초기화
    manager = VectorStoreManager()

    # 검색 테스트
    print(f"🔍 벡터스토어 ID: {args.vectorstore_id}")
    print(f"📝 질문: {args.query}\n")

    try:
        retrieved = manager.retrieve_documents(
            args.vectorstore_id,
            args.query,
            search_kwargs={"k": 5},
        )

        if not retrieved:
            print("❌ 검색 결과가 없습니다.")
            print(f"   벡터스토어가 존재하는지 확인하세요: {manager.base_dir / args.vectorstore_id}")
            return 1

        print(f"✅ {len(retrieved)}개의 문서를 검색했습니다.\n")

        for i, doc in enumerate(retrieved, 1):
            content = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            print(f"[{i}] {doc.metadata.get('source', 'Unknown source')}")
            print(f"    페이지: {doc.metadata.get('page', 'N/A')}")
            print(f"    내용: {content}\n")

        return 0

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())




