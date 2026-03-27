"""
LangGraph workflow definition for the RAG sub-agent.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langchain_ollama import ChatOllama

from src.utils.config import setup_langsmith_disabled

from .prompts import format_context, get_rag_system_prompt
from .state import RAGAgentState, get_last_user_message
from .vectorstore import VectorStoreManager


def _extract_content(response: Any) -> str:
    if isinstance(response, BaseMessage):
        return str(response.content)
    if isinstance(response, dict):
        return str(response.get("content", ""))
    return str(response)


def create_rag_agent_graph(
    *,
    llm: Optional[BaseChatModel] = None,
    embedding_model: Optional[Embeddings] = None,
    vectorstore_dir: Optional[str] = None,
):
    """Build and compile the LangGraph workflow."""

    load_dotenv()
    setup_langsmith_disabled()

    if llm is not None:
        chat_model = llm
    else:
        model_name = os.getenv("RAG_AGENT_MODEL", "gpt-oss:120b-cloud")
        temperature = float(os.getenv("RAG_AGENT_TEMPERATURE", "0.2"))
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        chat_model = ChatOllama(model=model_name, temperature=temperature, base_url=base_url)

    default_vectorstore_id = os.getenv("RAG_AGENT_DEFAULT_VECTORSTORE_ID")

    vector_manager = VectorStoreManager(
        embedding_model=embedding_model,
        vectorstore_dir=vectorstore_dir,
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", get_rag_system_prompt()),
            ("human", "질문: {question}\n\n검색 컨텍스트:\n{context}\n\n응답:"),
        ]
    )

    def bootstrap_node(state: RAGAgentState) -> RAGAgentState:
        if state.get("vectorstore_id") or not default_vectorstore_id:
            return {}

        metadata = {
            **(state.get("metadata", {}) or {}),
            "bootstrap_vectorstore_id": default_vectorstore_id,
        }
        return {"vectorstore_id": default_vectorstore_id, "metadata": metadata}

    def ingest_node(state: RAGAgentState) -> RAGAgentState:
        ingest_inputs = state.get("ingest_inputs")
        if not ingest_inputs:
            return {}

        documents = vector_manager.prepare_documents(ingest_inputs)
        chunked = vector_manager.split_documents(
            documents,
            chunk_size=ingest_inputs.get("chunk_size"),
            chunk_overlap=ingest_inputs.get("chunk_overlap"),
        )
        if not chunked:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "ingest_status": "skipped",
                    "reason": "문서를 찾을 수 없음",
                }
            }

        vector_id = vector_manager.index_documents(chunked, vectorstore_id=state.get("vectorstore_id"))
        return {
            "vectorstore_id": vector_id,
            "metadata": {
                **state.get("metadata", {}),
                "ingest_status": "completed",
                "ingested_docs": len(documents),
                "chunks": len(chunked),
            },
        }

    def retrieval_node(state: RAGAgentState) -> RAGAgentState:
        query = state.get("query") or get_last_user_message(state.get("messages"))
        vector_id = state.get("vectorstore_id")
        if not vector_id:
            return {
                "query": query,
                "retrieved_documents": [],
                "metadata": {
                    **state.get("metadata", {}),
                    "retrieval_status": "vectorstore_missing",
                },
            }

        retrieved = vector_manager.retrieve_documents(vector_id, query)
        serialized_docs = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in retrieved
        ]

        retrieval_status = "completed"
        if not serialized_docs:
            retrieval_status = (
                "vectorstore_missing" if not state.get("vectorstore_id") else "empty"
            )

        return {
            "query": query,
            "retrieved_documents": serialized_docs,
            "metadata": {
                **state.get("metadata", {}),
                "retrieval_status": retrieval_status,
                "retrieved_chunks": len(serialized_docs),
            },
        }

    qa_chain = qa_prompt | chat_model

    def answer_node(state: RAGAgentState) -> RAGAgentState:
        question = state.get("query") or get_last_user_message(state.get("messages"))
        context_block = format_context(state.get("retrieved_documents", []))

        response = qa_chain.invoke(
            {
                "question": question or "질문이 제공되지 않았습니다.",
                "context": context_block or "관련 컨텍스트를 찾지 못했습니다.",
            }
        )
        answer_text = _extract_content(response)
        return {
            "final_answer": answer_text.strip(),
            "messages": (state.get("messages") or []) + [AIMessage(content=answer_text)],
            "metadata": state.get("metadata", {}),
        }

    graph = StateGraph(RAGAgentState)
    graph.add_node("bootstrap", bootstrap_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("answer", answer_node)

    def start_router(state: RAGAgentState) -> str:
        return "ingest" if state.get("ingest_inputs") else "retrieve"

    graph.add_edge(START, "bootstrap")
    graph.add_conditional_edges(
        "bootstrap",
        start_router,
        {"ingest": "ingest", "retrieve": "retrieve"},
    )
    graph.add_edge("ingest", "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()

