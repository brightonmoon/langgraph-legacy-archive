"""
맥락 기반 Chunking 전략 테스트 및 예제

논문과 같은 구조화된 문서를 섹션 단위로 chunking하는 다양한 전략을 테스트합니다.

사용법:
    uv run python tests/test_contextual_chunking.py [--file <파일경로>] [--strategy <전략>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    print("⚠️  Docling이 설치되지 않았습니다. 다음 명령으로 설치하세요:")
    print("   uv pip install docling")
    sys.exit(1)

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        RecursiveCharacterTextSplitter,
    )
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    print("⚠️  LangChain이 설치되지 않았습니다.")
    print("   uv pip install langchain langchain-core langchain-text-splitters")

try:
    from docling.chunking import HierarchicalChunker
    HAS_DOCLING_CHUNKING = True
except ImportError:
    HAS_DOCLING_CHUNKING = False
    print("⚠️  Docling chunking이 설치되지 않았습니다.")
    print("   uv pip install 'docling-core[chunking]'")

from src.utils.paths import get_project_root


# 논문 표준 섹션 패턴
PAPER_SECTION_PATTERNS = [
    r'^#+\s*(?:1\.?\s*)?(?:Introduction|Abstract|Background|A B S T R A C T|I N T R O D U C T I O N)',
    r'^#+\s*(?:2\.?\s*)?(?:Method|Methodology|Methods|Experimental|M E T H O D S)',
    r'^#+\s*(?:3\.?\s*)?(?:Result|Results|Findings)',
    r'^#+\s*(?:4\.?\s*)?(?:Discussion|Analysis)',
    r'^#+\s*(?:5\.?\s*)?(?:Conclusion|Conclusions|Summary)',
    r'^#+\s*(?:6\.?\s*)?(?:Reference|References|Bibliography)',
]


def chunk_by_sections_markdown(
    file_path: str | Path,
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
) -> List[Document]:
    """
    Markdown 헤더를 기준으로 문서를 섹션 단위로 chunking.
    
    Args:
        file_path: 문서 파일 경로
        headers_to_split_on: 분할할 헤더 레벨 리스트
    
    Returns:
        Document 객체 리스트
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN:
        return []
    
    # 1. Docling으로 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    # 2. Markdown으로 export
    markdown = result.document.export_to_markdown()
    
    # 3. 헤더 레벨 설정
    if headers_to_split_on is None:
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
    
    # 4. MarkdownHeaderTextSplitter로 분할
    # strip_headers=False로 설정하여 헤더 정보 유지
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # 헤더 유지하여 섹션 정보 보존
    )
    chunks = markdown_splitter.split_text(markdown)
    
    # 5. LangChain Document로 변환
    documents = []
    for chunk in chunks:
        # 섹션 이름 추출 (Header 2 또는 Header 1에서)
        section_name = chunk.metadata.get("Header 2") or chunk.metadata.get("Header 1") or "Unknown"
        
        doc = Document(
            page_content=chunk.page_content,
            metadata={
                "source": str(file_path),
                "section_name": section_name,  # 명확한 섹션 이름 추가
                **chunk.metadata,
            }
        )
        documents.append(doc)
    
    return documents


def chunk_by_structure_hierarchical(
    file_path: str | Path,
    merge_list_items: bool = True,
) -> List[Document]:
    """
    Docling HierarchicalChunker를 사용하여 구조 기반 chunking.
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN or not HAS_DOCLING_CHUNKING:
        return []
    
    # 1. 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    # 2. HierarchicalChunker 생성
    chunker = HierarchicalChunker(
        merge_list_items=merge_list_items,
    )
    
    # 3. Chunking 수행
    chunks = list(chunker.chunk(result.document))
    
    # 4. LangChain Document로 변환
    documents = []
    for chunk in chunks:
        text = chunker.contextualize(chunk)
        
        # chunk.meta에서 메타데이터 추출
        metadata = {
            "source": str(file_path),
        }
        
        # headings 정보 추가
        if hasattr(chunk, 'meta') and chunk.meta:
            if hasattr(chunk.meta, 'headings') and chunk.meta.headings:
                metadata['headings'] = chunk.meta.headings
                metadata['section_name'] = chunk.meta.headings[0] if chunk.meta.headings else "Unknown"
            
            # captions 정보 추가
            if hasattr(chunk.meta, 'captions') and chunk.meta.captions:
                metadata['captions'] = chunk.meta.captions
        
        doc = Document(
            page_content=text,
            metadata=metadata,
        )
        documents.append(doc)
    
    return documents


def chunk_by_paper_sections(
    file_path: str | Path,
    section_patterns: Optional[List[str]] = None,
) -> List[Document]:
    """
    논문의 표준 섹션을 인식하여 chunking.
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN:
        return []
    
    # 1. 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    markdown = result.document.export_to_markdown()
    
    # 2. 섹션 패턴 설정
    if section_patterns is None:
        section_patterns = PAPER_SECTION_PATTERNS
    
    # 3. 섹션 경계 찾기
    lines = markdown.split('\n')
    section_boundaries = []
    current_section = None
    
    for i, line in enumerate(lines):
        for pattern in section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                # 섹션 이름 추출
                section_name = re.sub(r'^#+\s*\d+\.?\s*', '', line).strip()
                section_name = re.sub(r'^#+\s*', '', section_name).strip()
                
                if current_section is not None:
                    section_boundaries.append({
                        'name': current_section['name'],
                        'start': current_section['start'],
                        'end': i,
                    })
                
                current_section = {
                    'name': section_name,
                    'start': i,
                }
                break
    
    # 마지막 섹션 추가
    if current_section is not None:
        section_boundaries.append({
            'name': current_section['name'],
            'start': current_section['start'],
            'end': len(lines),
        })
    
    # 4. 섹션별로 Document 생성
    documents = []
    for boundary in section_boundaries:
        section_lines = lines[boundary['start']:boundary['end']]
        section_text = '\n'.join(section_lines)
        
        doc = Document(
            page_content=section_text,
            metadata={
                "source": str(file_path),
                "section_name": boundary['name'],
                "section_type": "paper_section",
            }
        )
        documents.append(doc)
    
    return documents


def chunk_by_sections_with_size_limit(
    file_path: str | Path,
    max_chunk_size: int = 2000,
    chunk_overlap: int = 200,
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
) -> List[Document]:
    """
    섹션 단위로 먼저 분할하고, 긴 섹션은 크기 제한으로 추가 분할.
    """
    if not HAS_LANGCHAIN:
        return []
    
    # 1. 섹션 단위로 먼저 분할
    section_docs = chunk_by_sections_markdown(file_path, headers_to_split_on)
    
    # 2. 긴 섹션은 추가로 분할
    final_documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    for section_doc in section_docs:
        if len(section_doc.page_content) <= max_chunk_size:
            final_documents.append(section_doc)
        else:
            sub_chunks = text_splitter.split_documents([section_doc])
            for sub_chunk in sub_chunks:
                sub_chunk.metadata.update(section_doc.metadata)
                sub_chunk.metadata['is_subsection'] = True
            final_documents.extend(sub_chunks)
    
    return final_documents


def chunk_markdown_hierarchical(
    file_path: str | Path,
    top_level_headers: Optional[List[Tuple[str, str]]] = None,
    sub_level_headers: Optional[List[Tuple[str, str]]] = None,
    max_chunk_size: int = 2000,
) -> List[Document]:
    """
    계층적 마크다운 chunking:
    - 상위 헤더(##)로 주요 섹션 분할
    - 하위 헤더(###)로 세부 섹션 분할
    - 크기 제한으로 최종 분할
    
    이 함수는 상위 헤더가 하위 헤더를 포함하도록 처리합니다.
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN:
        return []
    
    # 1. 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    markdown = result.document.export_to_markdown()
    
    # 2. 상위 헤더 설정
    if top_level_headers is None:
        top_level_headers = [("##", "Header 2")]
    
    if sub_level_headers is None:
        sub_level_headers = [("###", "Header 3")]
    
    # 3. 상위 헤더로 분할
    top_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=top_level_headers,
        strip_headers=False,  # 헤더 유지
    )
    top_chunks = top_splitter.split_text(markdown)
    
    # 4. 각 상위 섹션 처리
    final_documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=200,
    )
    
    for top_chunk in top_chunks:
        section_name = top_chunk.metadata.get("Header 2", "Unknown")
        content = top_chunk.page_content
        
        # 큰 섹션은 하위 헤더로 추가 분할
        if len(content) > max_chunk_size * 2:
            sub_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=sub_level_headers,
                strip_headers=False,
            )
            sub_chunks = sub_splitter.split_text(content)
            
            for sub_chunk in sub_chunks:
                sub_section = sub_chunk.metadata.get("Header 3", "")
                
                if len(sub_chunk.page_content) > max_chunk_size:
                    # 크기 제한으로 분할
                    size_chunks = text_splitter.split_documents([sub_chunk])
                    for size_chunk in size_chunks:
                        size_chunk.metadata.update({
                            "section_name": section_name,
                            "sub_section": sub_section,
                            "is_subsection": True,
                        })
                    final_documents.extend(size_chunks)
                else:
                    sub_chunk.metadata.update({
                        "section_name": section_name,
                        "sub_section": sub_section,
                    })
                    final_documents.append(sub_chunk)
        elif len(content) > max_chunk_size:
            # 크기 제한으로 분할
            size_chunks = text_splitter.split_documents([top_chunk])
            for size_chunk in size_chunks:
                size_chunk.metadata["section_name"] = section_name
            final_documents.extend(size_chunks)
        else:
            top_chunk.metadata["section_name"] = section_name
            final_documents.append(top_chunk)
    
    # 5. LangChain Document로 변환
    documents = []
    for chunk in final_documents:
        doc = Document(
            page_content=chunk.page_content,
            metadata={
                "source": str(file_path),
                **chunk.metadata,
            }
        )
        documents.append(doc)
    
    return documents


def chunk_paper_with_section_awareness(
    file_path: str | Path,
    max_chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    논문 섹션 인식 + 크기 제한 하이브리드 chunking (권장 전략).
    
    Paper Sections의 섹션 인식 능력과 Hybrid의 크기 제한을 결합한 전략입니다.
    
    Args:
        file_path: 문서 파일 경로
        max_chunk_size: 최대 청크 크기 (문자 단위)
        chunk_overlap: 청크 간 겹침
    
    Returns:
        Document 객체 리스트 (섹션 정보 포함)
    """
    if not HAS_LANGCHAIN:
        return []
    
    # 1단계: Paper Sections로 주요 섹션 분할
    section_docs = chunk_by_paper_sections(file_path)
    
    # 2단계: 큰 섹션은 추가 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    final_documents = []
    for section_doc in section_docs:
        section_name = section_doc.metadata.get('section_name', 'Unknown')
        
        if len(section_doc.page_content) <= max_chunk_size:
            # 작은 섹션은 그대로 사용
            final_documents.append(section_doc)
        else:
            # 큰 섹션은 추가 분할하되 섹션 정보 유지
            sub_chunks = text_splitter.split_documents([section_doc])
            for i, sub_chunk in enumerate(sub_chunks, 1):
                sub_chunk.metadata.update({
                    'section_name': section_name,
                    'section_type': 'paper_section',
                    'is_subsection': True,
                    'subsection_index': i,
                    'total_subsections': len(sub_chunks),
                })
            final_documents.extend(sub_chunks)
    
    return final_documents


def chunk_by_section_and_paragraphs(
    file_path: str | Path,
    max_chunk_size: int = 2000,
) -> List[Document]:
    """
    섹션 인식 + 단락 단위 chunking (단락 보존 전략).
    
    섹션을 인식한 후, 각 섹션을 단락 단위로 분할하여 의미 단위를 보존합니다.
    
    Args:
        file_path: 문서 파일 경로
        max_chunk_size: 최대 청크 크기 (문자 단위)
    
    Returns:
        Document 객체 리스트 (섹션 정보 + 단락 정보 포함)
    """
    if not HAS_LANGCHAIN:
        return []
    
    # 1단계: 섹션 분할
    section_docs = chunk_by_paper_sections(file_path)
    
    # 2단계: 각 섹션을 단락 단위로 분할
    final_documents = []
    
    for section_doc in section_docs:
        section_name = section_doc.metadata.get('section_name', 'Unknown')
        content = section_doc.page_content
        
        # 단락 단위로 분할 (\n\n 기준)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # 크기 제한 확인
            if current_size + para_size > max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = '\n\n'.join(current_chunk)
                final_documents.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "source": str(file_path),
                        "section_name": section_name,
                        "section_type": "paper_section",
                        "chunk_type": "section_paragraph",
                        "paragraph_count": len(current_chunk),
                    }
                ))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # 마지막 청크
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            final_documents.append(Document(
                page_content=chunk_text,
                metadata={
                    "source": str(file_path),
                    "section_name": section_name,
                    "section_type": "paper_section",
                    "chunk_type": "section_paragraph",
                    "paragraph_count": len(current_chunk),
                }
            ))
    
    return final_documents


def validate_contextual_chunking(
    documents: List[Document],
    min_chunk_size: int = 100,
    max_chunk_size: int = 5000,
) -> Dict[str, any]:
    """
    맥락 기반 chunking 결과 검증.
    """
    stats = {
        "total_chunks": len(documents),
        "chunks_with_metadata": sum(1 for d in documents if d.metadata),
        "avg_chunk_size": sum(len(d.page_content) for d in documents) / len(documents) if documents else 0,
        "sections_found": set(),
        "too_small": [],
        "too_large": [],
    }
    
    for doc in documents:
        # 섹션 정보 확인
        if "Header 1" in doc.metadata:
            stats["sections_found"].add(doc.metadata["Header 1"])
        elif "section_name" in doc.metadata:
            stats["sections_found"].add(doc.metadata["section_name"])
        
        # 크기 검증
        size = len(doc.page_content)
        if size < min_chunk_size:
            section = doc.metadata.get("Header 1") or doc.metadata.get("section_name", "Unknown")
            stats["too_small"].append(section)
        if size > max_chunk_size:
            section = doc.metadata.get("Header 1") or doc.metadata.get("section_name", "Unknown")
            stats["too_large"].append(section)
    
    stats["sections_found"] = list(stats["sections_found"])
    return stats


def save_chunks_to_files(
    documents: List[Document],
    output_dir: Path,
    strategy_name: str,
    source_file: Path,
) -> None:
    """
    Chunking 결과를 개별 파일로 저장.
    
    Args:
        documents: 저장할 Document 리스트
        output_dir: 출력 디렉토리
        strategy_name: 전략 이름
        source_file: 원본 파일 경로
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 전략별 서브디렉토리 생성
    strategy_dir = output_dir / strategy_name
    strategy_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    
    for i, doc in enumerate(documents, 1):
        # 섹션 이름 가져오기
        section = doc.metadata.get('Header 1') or doc.metadata.get('section_name', 'Unknown')
        
        # 파일명 생성 (섹션 이름을 파일명에 포함)
        safe_section = re.sub(r'[^\w\s-]', '', section).strip()
        safe_section = re.sub(r'[-\s]+', '_', safe_section)
        filename = f"{i:03d}_{safe_section}.txt"
        
        # 파일 경로
        chunk_file = strategy_dir / filename
        
        # 내용 저장 (메타데이터 포함)
        content_lines = [
            f"# Chunk {i}/{len(documents)}\n",
            f"## Metadata\n",
            f"Source: {doc.metadata.get('source', 'Unknown')}\n",
            f"Section: {section}\n",
            f"Size: {len(doc.page_content)} characters\n",
            f"\n## Content\n",
            doc.page_content,
        ]
        
        chunk_file.write_text('\n'.join(content_lines), encoding='utf-8')
        saved_files.append(chunk_file)
    
    print(f"\n💾 청크 저장 완료:")
    print(f"  • 저장 위치: {strategy_dir}")
    print(f"  • 총 파일 수: {len(saved_files)}개")
    print(f"  • 첫 번째 파일: {saved_files[0].name if saved_files else 'N/A'}")


def save_chunks_summary(
    documents: List[Document],
    output_file: Path,
    strategy_name: str,
    source_file: Path,
) -> None:
    """
    Chunking 결과를 요약 파일로 저장 (JSON 형식).
    
    Args:
        documents: 저장할 Document 리스트
        output_file: 출력 파일 경로
        strategy_name: 전략 이름
        source_file: 원본 파일 경로
    """
    import json
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 통계 계산
    stats = validate_contextual_chunking(documents)
    
    # 요약 데이터 구성
    summary = {
        "strategy": strategy_name,
        "source_file": str(source_file),
        "total_chunks": len(documents),
        "statistics": {
            "total_chunks": stats['total_chunks'],
            "chunks_with_metadata": stats['chunks_with_metadata'],
            "avg_chunk_size": stats['avg_chunk_size'],
            "sections_found": stats['sections_found'],
        },
        "chunks": [
            {
                "index": i + 1,
                "section": doc.metadata.get('Header 1') or doc.metadata.get('section_name', 'Unknown'),
                "size": len(doc.page_content),
                "metadata": doc.metadata,
                "content": doc.page_content,
            }
            for i, doc in enumerate(documents)
        ],
    }
    
    # JSON으로 저장
    output_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    print(f"\n💾 요약 파일 저장 완료:")
    print(f"  • 저장 위치: {output_file}")


def print_chunking_results(
    documents: List[Document],
    strategy_name: str,
    show_content: bool = False,
) -> None:
    """
    Chunking 결과 출력.
    """
    print(f"\n{'='*60}")
    print(f"📊 {strategy_name} 결과")
    print(f"{'='*60}")
    print(f"총 청크 수: {len(documents)}\n")
    
    # 검증 통계
    stats = validate_contextual_chunking(documents)
    print("📈 통계:")
    print(f"  • 총 청크 수: {stats['total_chunks']}")
    print(f"  • 메타데이터 포함 청크: {stats['chunks_with_metadata']}")
    print(f"  • 평균 청크 크기: {stats['avg_chunk_size']:.0f} 자")
    print(f"  • 발견된 섹션: {len(stats['sections_found'])}개")
    
    if stats['sections_found']:
        print(f"\n  섹션 목록:")
        for section in sorted(stats['sections_found']):
            count = sum(1 for d in documents 
                        if d.metadata.get('Header 1') == section 
                        or d.metadata.get('section_name') == section)
            print(f"    - {section}: {count}개 청크")
    
    if stats['too_small']:
        print(f"\n  ⚠️  너무 작은 청크: {len(stats['too_small'])}개")
    if stats['too_large']:
        print(f"\n  ⚠️  너무 큰 청크: {len(stats['too_large'])}개")
    
    # 샘플 청크 출력
    if documents and show_content:
        print(f"\n📝 샘플 청크 (처음 3개):")
        print("-" * 60)
        for i, doc in enumerate(documents[:3], 1):
            section = doc.metadata.get('Header 1') or doc.metadata.get('section_name', 'Unknown')
            print(f"\n[{i}] 섹션: {section}")
            print(f"크기: {len(doc.page_content)} 자")
            print(f"메타데이터: {doc.metadata}")
            print(f"내용 미리보기:")
            print(doc.page_content[:300])
            if len(doc.page_content) > 300:
                print("...")
            print("-" * 60)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="맥락 기반 Chunking 전략 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 모든 전략 테스트
  uv run python tests/test_contextual_chunking.py --file paper.pdf
  
  # 특정 전략만 테스트
  uv run python tests/test_contextual_chunking.py --file paper.pdf --strategy markdown_header
  
  # 내용 미리보기 포함
  uv run python tests/test_contextual_chunking.py --file paper.pdf --show-content
        """
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="테스트할 문서 파일 경로"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["markdown_header", "hierarchical", "paper_sections", "hybrid", "section_aware", "hierarchical_markdown", "section_paragraph", "all"],
        default="all",
        help="사용할 chunking 전략 (기본: all). section_aware는 권장 하이브리드 전략, hierarchical_markdown은 계층적 마크다운, section_paragraph는 섹션+단락 전략입니다."
    )
    parser.add_argument(
        "--show-content",
        action="store_true",
        help="청크 내용 미리보기 표시"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=2000,
        help="하이브리드 전략의 최대 청크 크기 (기본: 2000)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="청크를 파일로 저장"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="test_output/chunks",
        help="청크 저장 디렉토리 (기본: test_output/chunks)"
    )
    parser.add_argument(
        "--save-summary",
        action="store_true",
        help="청크 요약을 JSON 파일로 저장"
    )
    
    args = parser.parse_args()
    
    if not HAS_DOCLING:
        sys.exit(1)
    
    # 파일 찾기
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            sys.exit(1)
    else:
        # 테스트 데이터 디렉토리에서 찾기
        project_root = get_project_root()
        data_dir = project_root / "data"
        
        pdf_files = list(data_dir.glob("*.pdf"))
        if pdf_files:
            file_path = pdf_files[0]
            print(f"📁 테스트 파일 사용: {file_path}")
        else:
            print(f"⚠️  {data_dir}에 PDF 파일이 없습니다.")
            print("   --file 옵션을 사용하여 파일을 지정하세요.")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🚀 맥락 기반 Chunking 전략 테스트")
    print(f"{'='*60}")
    print(f"파일: {file_path}")
    print(f"전략: {args.strategy}")
    print(f"{'='*60}")
    
    # 전략별 테스트
    strategies_to_test = []
    
    if args.strategy == "all":
        strategies_to_test = [
            ("markdown_header", chunk_by_sections_markdown),
            ("hierarchical_markdown", lambda f: chunk_markdown_hierarchical(f, max_chunk_size=args.max_size)),
            ("hybrid", lambda f: chunk_by_sections_with_size_limit(f, max_chunk_size=args.max_size)),
            ("section_aware", lambda f: chunk_paper_with_section_awareness(f, max_chunk_size=args.max_size)),
            ("section_paragraph", lambda f: chunk_by_section_and_paragraphs(f, max_chunk_size=args.max_size)),
        ]
        
        if HAS_DOCLING_CHUNKING:
            strategies_to_test.append(("hierarchical", chunk_by_structure_hierarchical))
        
        strategies_to_test.append(("paper_sections", chunk_by_paper_sections))
    else:
        strategy_map = {
            "markdown_header": chunk_by_sections_markdown,
            "hierarchical": chunk_by_structure_hierarchical,
            "hierarchical_markdown": lambda f: chunk_markdown_hierarchical(f, max_chunk_size=args.max_size),
            "paper_sections": chunk_by_paper_sections,
            "hybrid": lambda f: chunk_by_sections_with_size_limit(f, max_chunk_size=args.max_size),
            "section_aware": lambda f: chunk_paper_with_section_awareness(f, max_chunk_size=args.max_size),
            "section_paragraph": lambda f: chunk_by_section_and_paragraphs(f, max_chunk_size=args.max_size),
        }
        if args.strategy in strategy_map:
            strategies_to_test = [(args.strategy, strategy_map[args.strategy])]
    
    # 각 전략 테스트
    for strategy_name, strategy_func in strategies_to_test:
        try:
            print(f"\n🔄 {strategy_name} 전략 테스트 중...")
            documents = strategy_func(file_path)
            
            if documents:
                print_chunking_results(documents, strategy_name, args.show_content)
                
                # 청크 저장
                if args.save:
                    output_dir = Path(args.output_dir)
                    save_chunks_to_files(
                        documents,
                        output_dir,
                        strategy_name,
                        file_path,
                    )
                
                # 요약 저장
                if args.save_summary:
                    output_file = Path(args.output_dir) / f"{file_path.stem}_{strategy_name}_summary.json"
                    save_chunks_summary(
                        documents,
                        output_file,
                        strategy_name,
                        file_path,
                    )
            else:
                print(f"  ⚠️  청크를 생성하지 못했습니다.")
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"✅ 테스트 완료!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

