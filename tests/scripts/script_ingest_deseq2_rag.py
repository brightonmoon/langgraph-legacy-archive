"""
CLI helper to ingest the DESeq2_counts.csv dataset into the RAG vector store.

Usage:
    uv run tests/scripts/script_ingest_deseq2_rag.py \
        --csv data/DESeq2_counts.csv \
        --vectorstore-id deseq2_counts
"""

from __future__ import annotations

import argparse
from datetime import datetime

from dotenv import load_dotenv

from src.agents.sub_agents.rag_agent.data_utils import (
    ChunkingStrategy,
    load_csv_rows_as_documents,
)
from src.agents.sub_agents.rag_agent.vectorstore import VectorStoreManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest DESeq2 CSV into RAG vector store.")
    parser.add_argument(
        "--csv",
        default="data/DESeq2_counts.csv",
        help="Path to the DESeq2_counts.csv file (relative or absolute).",
    )
    parser.add_argument(
        "--vectorstore-id",
        default="deseq2_counts",
        help="Identifier for the persisted vector store.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        help="Chunk size for splitting rows.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="Chunk overlap for splitting rows.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on the number of CSV rows to ingest.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="row_with_header",
        choices=["row_with_header", "header_separate", "batched", "metadata_header", "hybrid"],
        help="CSV 청킹 전략 (기본값: row_with_header)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="BATCHED 전략 사용 시 배치 크기 (기본값: 10)",
    )
    parser.add_argument(
        "--include-header-doc",
        action="store_true",
        default=True,
        help="HYBRID 전략 사용 시 헤더 문서 포함 (기본값: True)",
    )
    parser.add_argument(
        "--no-include-header-doc",
        dest="include_header_doc",
        action="store_false",
        help="HYBRID 전략 사용 시 헤더 문서 제외",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()

    strategy = ChunkingStrategy(args.strategy)
    print(
        f"[{datetime.now().isoformat()}] Loading CSV rows from {args.csv} "
        f"(strategy: {strategy.value}) ..."
    )
    documents = load_csv_rows_as_documents(
        args.csv,
        limit=args.limit,
        strategy=strategy,
        batch_size=args.batch_size,
        include_header_doc=args.include_header_doc,
    )
    if not documents:
        raise SystemExit("CSV 파일에서 로드된 문서가 없습니다.")

    manager = VectorStoreManager()
    print(
        f"[{datetime.now().isoformat()}] Chunking {len(documents)} documents "
        f"(chunk_size={args.chunk_size}, overlap={args.chunk_overlap}) ..."
    )
    chunks = manager.split_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    if not chunks:
        raise SystemExit("문서 청크 생성에 실패했습니다.")

    print(
        f"[{datetime.now().isoformat()}] Indexing {len(chunks)} chunks "
        f"into vectorstore '{args.vectorstore_id}' ..."
    )
    vector_id = manager.index_documents(chunks, vectorstore_id=args.vectorstore_id)

    print("\n✅ Ingestion complete!")
    print(f"   Vectorstore ID : {vector_id}")
    print(f"   Storage Path   : {manager.base_dir / vector_id}")
    print(
        "   Next step      : export RAG_AGENT_DEFAULT_VECTORSTORE_ID "
        "environment variable before running LangGraph:"
    )
    print(f"\n   export RAG_AGENT_DEFAULT_VECTORSTORE_ID={vector_id}\n")


if __name__ == "__main__":
    main()

