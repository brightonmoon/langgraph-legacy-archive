"""
Factory helpers that expose the compiled LangGraph agent.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from .graph import create_rag_agent_graph as _create_graph


def create_rag_agent_graph(
    *,
    llm: Optional[BaseChatModel] = None,
    embedding_model: Optional[Embeddings] = None,
    vectorstore_dir: Optional[str] = None,
):
    """Public factory that mirrors the internal graph builder."""

    return _create_graph(
        llm=llm,
        embedding_model=embedding_model,
        vectorstore_dir=vectorstore_dir,
    )


try:
    agent = create_rag_agent_graph()
except Exception:
    # LangGraph Studio import path should not fail during discovery
    agent = None




