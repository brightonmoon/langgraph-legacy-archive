"""
Prompt helpers for the RAG sub-agent.
"""

from __future__ import annotations

from datetime import datetime, timezone


def get_rag_system_prompt() -> str:
    """Return a system prompt with dynamic date metadata."""
    now = datetime.now(timezone.utc)
    readable = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    iso = now.isoformat()
    return (
        "당신은 LangChain 기반의 RAG 어시스턴트입니다.\n"
        f"- 현재 UTC 시각: {readable}\n"
        f"- ISO 타임스탬프: {iso}\n\n"
        "규칙:\n"
        "1. 사용자 질문에 답변하기 전에 검색된 컨텍스트를 반드시 검토하세요.\n"
        "2. 컨텍스트에 없는 내용은 가정하지 말고 '정보 없음'이라고 말하세요.\n"
        "3. 응답은 한국어로 제공하되, 기술 용어는 원문 표기를 병기할 수 있습니다.\n"
    )


def format_context(docs: list[dict]) -> str:
    """Render retrieved documents into a single context string."""
    if not docs:
        return ""

    formatted_chunks = []
    for idx, doc in enumerate(docs, start=1):
        content = doc.get("content") or doc.get("page_content") or ""
        metadata = doc.get("metadata") or {}
        source = metadata.get("source") or metadata.get("path") or metadata.get("id") or f"chunk-{idx}"
        formatted_chunks.append(f"[출처: {source}] {content.strip()}")

    return "\n\n".join(formatted_chunks)




