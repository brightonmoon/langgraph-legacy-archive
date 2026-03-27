"""
State definition for the LangGraph-based RAG sub-agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class RAGAgentState(TypedDict, total=False):
    """Shared state that flows through the LangGraph graph."""

    messages: List[Union[BaseMessage, Dict[str, Any]]]
    query: str
    ingest_inputs: Dict[str, Any]
    vectorstore_id: str
    retrieved_documents: List[Dict[str, Any]]
    final_answer: str
    metadata: Dict[str, Any]


def get_last_user_message(messages: Optional[List[Any]]) -> str:
    """Utility helper to fetch the latest user query from a LangChain-style message list."""
    if not messages:
        return ""

    for message in reversed(messages):
        # LangChain BaseMessage
        if isinstance(message, BaseMessage):
            if getattr(message, "type", "") in {"human", "user"} or getattr(message, "role", "") == "user":
                return str(message.content)

        # dict-style message
        if isinstance(message, dict):
            role = message.get("role") or message.get("type")
            if role in {"human", "user"}:
                content = message.get("content")
                if isinstance(content, list):
                    # LangGraph Studio sometimes passes list contents
                    text_chunks = [chunk.get("text", "") if isinstance(chunk, dict) else str(chunk) for chunk in content]
                    return "\n".join(filter(None, text_chunks)).strip()
                return str(content)

    return ""




