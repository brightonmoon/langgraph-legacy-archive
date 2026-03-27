"""
Utility helpers for preparing documents from structured data sources.
"""

from __future__ import annotations

import csv
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Literal, Optional

from langchain_core.documents import Document

try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    PyPDFLoader = None

from src.utils.paths import resolve_data_file_path


class ChunkingStrategy(str, Enum):
    """CSV 데이터 청킹 전략"""

    ROW_WITH_HEADER = "row_with_header"  # 각 행에 헤더 포함 (기본값, 현재 방식)
    HEADER_SEPARATE = "header_separate"  # 헤더를 별도 문서로 저장
    BATCHED = "batched"  # 여러 행을 묶어서 하나의 문서로 생성
    METADATA_HEADER = "metadata_header"  # 헤더를 메타데이터로 저장
    HYBRID = "hybrid"  # 하이브리드 방식 (헤더 문서 + 행 문서)


def _format_row_as_text(headers: Iterable[str], row: dict) -> str:
    """각 행을 텍스트 형식으로 변환 (컬럼명: 값 형식)"""
    lines = ["Gene expression record"]
    for header in headers:
        value = row.get(header, "")
        lines.append(f"{header}: {value}")
    return "\n".join(lines)


def _format_row_values_only(headers: Iterable[str], row: dict) -> str:
    """행의 값만 텍스트로 변환 (컬럼명 없음)"""
    return "\n".join(str(row.get(header, "")) for header in headers)


def _create_header_document(
    headers: Iterable[str], csv_path: Path, description: str = "CSV Schema"
) -> Document:
    """헤더 정보를 별도 Document로 생성"""
    header_list = list(headers)
    content = f"{description}:\n"
    content += "\n".join(f"{i+1}. {header}" for i, header in enumerate(header_list))
    return Document(
        page_content=content,
        metadata={
            "type": "schema",
            "source": str(csv_path),
            "column_count": len(header_list),
            "columns": header_list,
        },
    )


def _create_row_documents_row_with_header(
    headers: List[str], rows: List[dict], csv_path: Path, limit: Optional[int] = None
) -> List[Document]:
    """전략 1: 각 행에 헤더 포함 (현재 방식)"""
    documents: List[Document] = []
    for idx, row in enumerate(rows):
        if limit is not None and len(documents) >= limit:
            break
        content = _format_row_as_text(headers, row)
        metadata = {
            "source": str(csv_path),
            "row_index": idx,
            "type": "row",
            "GeneID": row.get("GeneID"),
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _create_row_documents_header_separate(
    headers: List[str], rows: List[dict], csv_path: Path, limit: Optional[int] = None
) -> List[Document]:
    """전략 2: 헤더를 별도 문서로 저장"""
    documents: List[Document] = []
    # 헤더 문서 추가
    documents.append(_create_header_document(headers, csv_path))

    # 행 문서 생성 (값만 포함)
    for idx, row in enumerate(rows):
        if limit is not None and len(documents) - 1 >= limit:  # 헤더 문서 제외
            break
        content = _format_row_values_only(headers, row)
        metadata = {
            "source": str(csv_path),
            "row_index": idx,
            "type": "row",
            "headers": headers,  # 헤더는 메타데이터에 저장
            "GeneID": row.get("GeneID"),
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _create_row_documents_batched(
    headers: List[str],
    rows: List[dict],
    csv_path: Path,
    batch_size: int = 10,
    limit: Optional[int] = None,
) -> List[Document]:
    """전략 3: 여러 행을 묶어서 하나의 문서로 생성"""
    documents: List[Document] = []
    header_text = "Columns: " + ", ".join(headers) + "\n\n"

    total_rows = len(rows) if limit is None else min(len(rows), limit)
    for i in range(0, total_rows, batch_size):
        batch = rows[i : i + batch_size]
        content = header_text
        content += "\n".join(
            f"Row {i+j}: " + ", ".join(str(row.get(h, "")) for h in headers)
            for j, row in enumerate(batch)
        )

        metadata = {
            "source": str(csv_path),
            "type": "batch",
            "batch_start": i,
            "batch_size": len(batch),
            "batch_end": i + len(batch) - 1,
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _create_row_documents_metadata_header(
    headers: List[str], rows: List[dict], csv_path: Path, limit: Optional[int] = None
) -> List[Document]:
    """전략 4: 헤더를 메타데이터로 저장"""
    documents: List[Document] = []
    for idx, row in enumerate(rows):
        if limit is not None and len(documents) >= limit:
            break
        # 값만 텍스트로 변환
        content = _format_row_values_only(headers, row)
        metadata = {
            "source": str(csv_path),
            "row_index": idx,
            "type": "row",
            "headers": headers,  # 헤더를 메타데이터로 저장
            "GeneID": row.get("GeneID"),
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def _create_row_documents_hybrid(
    headers: List[str],
    rows: List[dict],
    csv_path: Path,
    include_header_doc: bool = True,
    limit: Optional[int] = None,
) -> List[Document]:
    """전략 5: 하이브리드 방식 (헤더 문서 + 행 문서)"""
    documents: List[Document] = []

    # 1. 헤더 문서 생성 (선택적)
    if include_header_doc:
        documents.append(_create_header_document(headers, csv_path))

    # 2. 각 행 문서 생성 (컬럼명 포함, 간결한 형식)
    for idx, row in enumerate(rows):
        if limit is not None and len(documents) - (1 if include_header_doc else 0) >= limit:
            break
        # 주요 컬럼만 포함 (처음 15개)
        max_cols = min(15, len(headers))
        content = "\n".join(
            f"{h}: {row.get(h, '')}" for h in headers[:max_cols]
        )
        if len(headers) > max_cols:
            content += f"\n... and {len(headers) - max_cols} more columns"

        metadata = {
            "source": str(csv_path),
            "row_index": idx,
            "type": "row",
            "all_headers": headers,  # 전체 헤더는 메타데이터에
            "GeneID": row.get("GeneID"),
        }
        documents.append(Document(page_content=content, metadata=metadata))
    return documents


def load_csv_rows_as_documents(
    csv_path: str | Path,
    *,
    limit: Optional[int] = None,
    strategy: ChunkingStrategy | Literal[
        "row_with_header",
        "header_separate",
        "batched",
        "metadata_header",
        "hybrid",
    ] = ChunkingStrategy.ROW_WITH_HEADER,
    batch_size: int = 10,
    include_header_doc: bool = True,
) -> List[Document]:
    """
    CSV 파일을 LangChain Document 객체로 변환 (다양한 청킹 전략 지원).

    Args:
        csv_path: CSV 파일 경로
        limit: 처리할 최대 행 수 (None이면 전체)
        strategy: 청킹 전략
            - "row_with_header": 각 행에 헤더 포함 (기본값)
            - "header_separate": 헤더를 별도 문서로 저장
            - "batched": 여러 행을 묶어서 하나의 문서로 생성
            - "metadata_header": 헤더를 메타데이터로 저장
            - "hybrid": 하이브리드 방식 (헤더 문서 + 행 문서)
        batch_size: BATCHED 전략 사용 시 배치 크기
        include_header_doc: HYBRID 전략 사용 시 헤더 문서 포함 여부

    Returns:
        Document 객체 리스트
    """
    resolved_path = resolve_data_file_path(str(csv_path))

    # CSV 파일 읽기
    with resolved_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    # 전략에 따라 문서 생성
    if isinstance(strategy, str):
        strategy = ChunkingStrategy(strategy)

    if strategy == ChunkingStrategy.ROW_WITH_HEADER:
        return _create_row_documents_row_with_header(headers, rows, resolved_path, limit)
    elif strategy == ChunkingStrategy.HEADER_SEPARATE:
        return _create_row_documents_header_separate(headers, rows, resolved_path, limit)
    elif strategy == ChunkingStrategy.BATCHED:
        return _create_row_documents_batched(headers, rows, resolved_path, batch_size, limit)
    elif strategy == ChunkingStrategy.METADATA_HEADER:
        return _create_row_documents_metadata_header(headers, rows, resolved_path, limit)
    elif strategy == ChunkingStrategy.HYBRID:
        return _create_row_documents_hybrid(headers, rows, resolved_path, include_header_doc, limit)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def load_pdf_as_documents(
    pdf_path: str | Path,
    *,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """
    PDF 파일을 LangChain Document 객체로 변환.

    Args:
        pdf_path: PDF 파일 경로
        chunk_size: 청크 크기 (None이면 페이지 단위로 유지)
        chunk_overlap: 청크 간 겹침 크기

    Returns:
        Document 객체 리스트 (각 페이지 또는 청크가 하나의 Document)

    Raises:
        ImportError: PyPDFLoader가 설치되지 않은 경우
        FileNotFoundError: PDF 파일이 존재하지 않는 경우
    """
    if PyPDFLoader is None:
        raise ImportError(
            "langchain-community 패키지가 필요합니다. "
            "pip install langchain-community 로 설치 후 다시 시도하세요."
        )

    resolved_path = resolve_data_file_path(str(pdf_path))
    if not resolved_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {resolved_path}")

    # PDF 로드
    loader = PyPDFLoader(str(resolved_path))
    documents = loader.load()

    # 메타데이터에 소스 경로 추가
    for doc in documents:
        if "source" not in doc.metadata:
            doc.metadata["source"] = str(resolved_path)
        doc.metadata["file_type"] = "pdf"

    # 청킹이 필요한 경우
    if chunk_size is not None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap or 0,
        )
        documents = splitter.split_documents(documents)

    return documents

