# 맥락 기반 RAG Chunking 전략 가이드

## 📋 개요

본 문서는 RAG(Retrieval-Augmented Generation) 시스템에서 **글자수 단위가 아닌 맥락별로 chunk를 자르는 전략**에 대한 기술 자료입니다. 특히 논문과 같은 구조화된 문서에서 **Introduction, Method, Result 등 소제목 단위로 chunk를 분할**하는 방법을 다룹니다.

**작성일**: 2025-01-XX  
**대상 프로젝트**: agentic_ai  
**기술 스택**: Docling, LangChain, FAISS

---

## 1. 맥락 기반 Chunking의 필요성

### 1.1 기존 방식의 한계

기존의 글자수 기반 chunking 방식은 다음과 같은 문제점이 있습니다:

- ❌ **의미 단위 무시**: 문장이나 문단 중간에서 잘려 의미가 손실됨
- ❌ **컨텍스트 단절**: 관련된 내용이 서로 다른 chunk로 분리됨
- ❌ **검색 정확도 저하**: 불완전한 컨텍스트로 인한 검색 품질 저하
- ❌ **논문 구조 무시**: Introduction, Method, Result 등 논리적 구조를 반영하지 못함

### 1.2 맥락 기반 Chunking의 장점

- ✅ **의미 단위 보존**: 논리적 단위(섹션, 소제목)로 chunk 분할
- ✅ **컨텍스트 유지**: 관련 내용을 하나의 chunk에 포함
- ✅ **검색 정확도 향상**: 완전한 컨텍스트로 인한 더 나은 검색 결과
- ✅ **메타데이터 풍부**: 섹션 정보를 메타데이터로 활용 가능
- ✅ **사용자 경험 개선**: 더 정확하고 관련성 높은 답변 생성

---

## 2. 프로젝트에서 구축한 기술 스택

### 2.1 핵심 기술

프로젝트에서 테스트 및 구축한 주요 기술들:

1. **Docling**: 문서 파싱 및 구조 추출
   - PDF, DOCX 등 다양한 형식 지원
   - 문서 구조 정보 보존 (헤더, 섹션, 테이블 등)
   - Markdown export로 구조화된 텍스트 생성

2. **LangChain TextSplitters**: 다양한 chunking 전략 제공
   - `MarkdownHeaderTextSplitter`: Markdown 헤더 기반 분할
   - `RecursiveCharacterTextSplitter`: 재귀적 문자 분할
   - `TokenTextSplitter`: 토큰 단위 분할

3. **Docling Native Chunkers**: 구조 인식 chunking
   - `HierarchicalChunker`: 계층적 구조 기반 chunking
   - `HybridChunker`: 토큰화 인식 + 구조 기반 chunking

### 2.2 현재 프로젝트 구조

```
agentic_ai/
├── src/agents/sub_agents/rag_agent/
│   ├── vectorstore.py          # VectorStoreManager (FAISS 기반)
│   └── data_utils.py            # 문서 로딩 유틸리티
├── tests/
│   ├── test_docling_basic.py    # Docling 기본 사용법
│   ├── test_docling_advanced.py # Docling 고급 기능
│   ├── test_docling_comparison.py # 파서 비교
│   └── DOCLING_RAG_APPLICATION_REVIEW.md # Docling RAG 검토서
└── data/                        # 테스트 문서들
```

---

## 3. 맥락 기반 Chunking 전략

### 3.1 전략 1: MarkdownHeaderTextSplitter 활용 (권장)

**개요**: Docling이 Markdown으로 export한 문서를 헤더 구조에 따라 분할

**장점**:
- ✅ 구현이 간단하고 직관적
- ✅ LangChain과 완벽 통합
- ✅ 섹션 정보가 메타데이터로 자동 포함
- ✅ 논문의 표준 구조(Introduction, Method, Result 등) 자동 인식

**구현 예시**:

```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

def chunk_by_sections_markdown(
    file_path: str | Path,
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
) -> List[Document]:
    """
    Markdown 헤더를 기준으로 문서를 섹션 단위로 chunking.
    
    Args:
        file_path: 문서 파일 경로
        headers_to_split_on: 분할할 헤더 레벨 리스트
                          기본값: [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    
    Returns:
        Document 객체 리스트 (각 섹션이 하나의 Document)
    """
    # 1. Docling으로 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    # 2. Markdown으로 export
    markdown = result.document.export_to_markdown()
    
    # 3. 헤더 레벨 설정 (기본값: H1, H2, H3)
    if headers_to_split_on is None:
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
    
    # 4. MarkdownHeaderTextSplitter로 분할
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    chunks = markdown_splitter.split_text(markdown)
    
    # 5. LangChain Document로 변환
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk.page_content,
            metadata={
                "source": str(file_path),
                **chunk.metadata,  # 헤더 정보가 메타데이터로 포함됨
            }
        )
        documents.append(doc)
    
    return documents
```

**사용 예시**:

```python
# 논문을 섹션 단위로 chunking
documents = chunk_by_sections_markdown("paper.pdf")

# 결과 예시:
# - Document 1: page_content="Introduction 내용...", metadata={"Header 1": "Introduction", ...}
# - Document 2: page_content="Method 내용...", metadata={"Header 1": "Method", ...}
# - Document 3: page_content="Results 내용...", metadata={"Header 1": "Results", ...}
```

### 3.2 전략 2: Docling HierarchicalChunker 활용

**개요**: Docling의 네이티브 HierarchicalChunker를 사용하여 문서 구조 기반 chunking

**장점**:
- ✅ 문서 구조 정보를 직접 활용
- ✅ 테이블, 수식 등 구조 요소 자동 처리
- ✅ 토큰화 인식 없이 순수 구조 기반

**구현 예시**:

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker
from langchain_core.documents import Document

def chunk_by_structure_hierarchical(
    file_path: str | Path,
    merge_list_items: bool = True,
) -> List[Document]:
    """
    Docling HierarchicalChunker를 사용하여 구조 기반 chunking.
    
    Args:
        file_path: 문서 파일 경로
        merge_list_items: 리스트 아이템 병합 여부
    
    Returns:
        Document 객체 리스트
    """
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
        # contextualize()로 메타데이터가 포함된 텍스트 생성
        text = chunker.contextualize(chunk)
        doc = Document(
            page_content=text,
            metadata={
                "source": str(file_path),
                **chunk.metadata,  # 구조 정보가 메타데이터로 포함됨
            }
        )
        documents.append(doc)
    
    return documents
```

### 3.3 전략 3: 커스텀 섹션 인식 Chunking

**개요**: 논문의 표준 섹션(Introduction, Method, Result 등)을 명시적으로 인식하여 분할

**장점**:
- ✅ 논문 구조에 특화된 정확한 분할
- ✅ 섹션 이름을 메타데이터로 명확히 저장
- ✅ 섹션별 검색 및 필터링 가능

**구현 예시**:

```python
import re
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from typing import List, Tuple, Optional

# 논문 표준 섹션 패턴
PAPER_SECTION_PATTERNS = [
    r'^#+\s*(?:1\.?\s*)?(?:Introduction|Abstract|Background)',
    r'^#+\s*(?:2\.?\s*)?(?:Method|Methodology|Methods|Experimental)',
    r'^#+\s*(?:3\.?\s*)?(?:Result|Results|Findings)',
    r'^#+\s*(?:4\.?\s*)?(?:Discussion|Analysis)',
    r'^#+\s*(?:5\.?\s*)?(?:Conclusion|Conclusions|Summary)',
    r'^#+\s*(?:6\.?\s*)?(?:Reference|References|Bibliography)',
]

def chunk_by_paper_sections(
    file_path: str | Path,
    section_patterns: Optional[List[str]] = None,
) -> List[Document]:
    """
    논문의 표준 섹션을 인식하여 chunking.
    
    Args:
        file_path: 문서 파일 경로
        section_patterns: 섹션 패턴 리스트 (기본값: 표준 논문 섹션)
    
    Returns:
        Document 객체 리스트
    """
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
```

### 3.4 전략 4: 하이브리드 접근 (섹션 + 크기 제한)

**개요**: 섹션 단위로 먼저 분할하되, 너무 긴 섹션은 추가로 분할

**장점**:
- ✅ 섹션 구조 보존
- ✅ 긴 섹션도 적절한 크기로 분할
- ✅ 임베딩 모델의 토큰 제한 고려

**구현 예시**:

```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

def chunk_by_sections_with_size_limit(
    file_path: str | Path,
    max_chunk_size: int = 2000,
    chunk_overlap: int = 200,
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
) -> List[Document]:
    """
    섹션 단위로 먼저 분할하고, 긴 섹션은 크기 제한으로 추가 분할.
    
    Args:
        file_path: 문서 파일 경로
        max_chunk_size: 최대 청크 크기 (문자 단위)
        chunk_overlap: 청크 간 겹침
        headers_to_split_on: 분할할 헤더 레벨
    
    Returns:
        Document 객체 리스트
    """
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
            # 작은 섹션은 그대로 사용
            final_documents.append(section_doc)
        else:
            # 긴 섹션은 추가 분할
            sub_chunks = text_splitter.split_documents([section_doc])
            # 원본 섹션 메타데이터 유지
            for sub_chunk in sub_chunks:
                sub_chunk.metadata.update(section_doc.metadata)
                sub_chunk.metadata['is_subsection'] = True
            final_documents.extend(sub_chunks)
    
    return final_documents
```

---

## 4. 프로젝트 통합 방안

### 4.1 VectorStoreManager 확장

현재 프로젝트의 `VectorStoreManager`에 맥락 기반 chunking 옵션 추가:

```python
# src/agents/sub_agents/rag_agent/vectorstore.py

class VectorStoreManager:
    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        vectorstore_dir: Optional[str | Path] = None,
        # 맥락 기반 chunking 옵션 추가
        chunking_strategy: str = "contextual",  # "contextual", "size_based", "hybrid"
        contextual_headers: Optional[List[Tuple[str, str]]] = None,
        max_section_size: Optional[int] = None,  # 섹션 최대 크기 제한
    ) -> None:
        # ... 기존 코드 ...
        self.chunking_strategy = chunking_strategy
        self.contextual_headers = contextual_headers or [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.max_section_size = max_section_size
    
    def load_document_with_contextual_chunking(
        self,
        file_path: str | Path,
    ) -> List[Document]:
        """
        맥락 기반 chunking으로 문서 로드.
        """
        from docling.document_converter import DocumentConverter
        from langchain_text_splitters import MarkdownHeaderTextSplitter
        
        # Docling으로 변환
        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        markdown = result.document.export_to_markdown()
        
        if self.chunking_strategy == "contextual":
            # 섹션 단위 chunking
            splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=self.contextual_headers
            )
            chunks = splitter.split_text(markdown)
            documents = [
                Document(
                    page_content=chunk.page_content,
                    metadata={**chunk.metadata, "source": str(file_path)}
                )
                for chunk in chunks
            ]
            
            # 크기 제한이 있으면 추가 분할
            if self.max_section_size:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.max_section_size,
                    chunk_overlap=self.default_chunk_overlap,
                )
                final_documents = []
                for doc in documents:
                    if len(doc.page_content) <= self.max_section_size:
                        final_documents.append(doc)
                    else:
                        sub_chunks = text_splitter.split_documents([doc])
                        for sub_chunk in sub_chunks:
                            sub_chunk.metadata.update(doc.metadata)
                        final_documents.extend(sub_chunks)
                documents = final_documents
            
            return documents
        else:
            # 기존 방식 (크기 기반)
            return self.split_documents([Document(
                page_content=markdown,
                metadata={"source": str(file_path)}
            )])
```

### 4.2 data_utils.py에 헬퍼 함수 추가

```python
# src/agents/sub_agents/rag_agent/data_utils.py

def load_document_contextual(
    file_path: str | Path,
    strategy: str = "markdown_header",
    **kwargs
) -> List[Document]:
    """
    맥락 기반 chunking으로 문서 로드.
    
    Args:
        file_path: 문서 파일 경로
        strategy: chunking 전략
            - "markdown_header": MarkdownHeaderTextSplitter 사용
            - "hierarchical": Docling HierarchicalChunker 사용
            - "paper_sections": 논문 섹션 인식 사용
            - "hybrid": 섹션 + 크기 제한
        **kwargs: 전략별 추가 옵션
    
    Returns:
        Document 객체 리스트
    """
    if strategy == "markdown_header":
        return chunk_by_sections_markdown(file_path, **kwargs)
    elif strategy == "hierarchical":
        return chunk_by_structure_hierarchical(file_path, **kwargs)
    elif strategy == "paper_sections":
        return chunk_by_paper_sections(file_path, **kwargs)
    elif strategy == "hybrid":
        return chunk_by_sections_with_size_limit(file_path, **kwargs)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
```

---

## 5. 실제 사용 예시

### 5.1 논문 문서 처리

```python
from src.agents.sub_agents.rag_agent.data_utils import load_document_contextual

# 논문을 섹션 단위로 chunking
documents = load_document_contextual(
    "data/paper.pdf",
    strategy="markdown_header",
)

# 결과:
# - Introduction 섹션 → Document 1
# - Method 섹션 → Document 2
# - Results 섹션 → Document 3
# - Discussion 섹션 → Document 4
# - Conclusion 섹션 → Document 5
```

### 5.2 VectorStore에 저장

```python
from src.agents.sub_agents.rag_agent.vectorstore import VectorStoreManager

# 맥락 기반 chunking 설정
manager = VectorStoreManager(
    chunking_strategy="contextual",
    contextual_headers=[
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ],
    max_section_size=2000,  # 긴 섹션은 추가 분할
)

# 문서 로드 및 저장
documents = manager.load_document_with_contextual_chunking("paper.pdf")
manager.add_documents(documents, collection_name="papers")
```

### 5.3 검색 시 섹션 정보 활용

```python
# 검색 결과에서 섹션 정보 활용
results = manager.similarity_search(
    query="What methods were used?",
    collection_name="papers",
    k=5,
)

for doc in results:
    print(f"Section: {doc.metadata.get('Header 1', 'Unknown')}")
    print(f"Content: {doc.page_content[:200]}...")
    print()
```

---

## 6. 전략 비교 및 선택 가이드

### 6.1 전략 비교표

| 전략 | 구현 난이도 | 구조 보존 | 성능 | 메타데이터 | 권장 사용 사례 |
|------|------------|----------|------|-----------|--------------|
| **MarkdownHeaderTextSplitter** | ⭐ 쉬움 | ⭐⭐⭐ 우수 | ⭐⭐⭐ 빠름 | ⭐⭐⭐ 풍부 | 논문, 보고서 (권장) |
| **HierarchicalChunker** | ⭐⭐ 보통 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ 풍부 | 복잡한 구조 문서 |
| **커스텀 섹션 인식** | ⭐⭐⭐ 어려움 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ 매우 풍부 | 논문 특화 |
| **하이브리드 접근** | ⭐⭐ 보통 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ 풍부 | 긴 문서 |

### 6.2 선택 가이드

**MarkdownHeaderTextSplitter 사용 권장**:
- ✅ 구현이 간단하고 직관적
- ✅ LangChain과 완벽 통합
- ✅ 대부분의 논문/보고서에 적용 가능
- ✅ 섹션 정보가 메타데이터로 자동 포함

**HierarchicalChunker 사용 권장**:
- ✅ 테이블, 수식 등 복잡한 구조 요소가 많은 문서
- ✅ Docling의 구조 정보를 최대한 활용하고 싶을 때

**커스텀 섹션 인식 사용 권장**:
- ✅ 논문의 표준 섹션을 명확히 인식해야 할 때
- ✅ 섹션 이름을 정확한 메타데이터로 저장하고 싶을 때

**하이브리드 접근 사용 권장**:
- ✅ 섹션 구조를 보존하면서도 크기 제한이 필요할 때
- ✅ 임베딩 모델의 토큰 제한을 고려해야 할 때

---

## 7. 성능 최적화 및 고려사항

### 7.1 메타데이터 관리

맥락 기반 chunking에서는 메타데이터가 매우 중요합니다:

```python
# 좋은 메타데이터 예시
metadata = {
    "source": "paper.pdf",
    "Header 1": "Introduction",  # 최상위 섹션
    "Header 2": "Background",     # 하위 섹션
    "section_name": "Introduction",
    "section_type": "paper_section",
    "page_number": 1,  # Docling에서 제공 가능
}
```

### 7.2 검색 품질 향상

섹션 정보를 활용한 검색 개선:

```python
def search_with_section_filter(
    manager: VectorStoreManager,
    query: str,
    section_filter: Optional[str] = None,
    k: int = 5,
) -> List[Document]:
    """
    섹션 필터를 적용한 검색.
    """
    results = manager.similarity_search(query, k=k*2)  # 더 많이 가져오기
    
    if section_filter:
        # 특정 섹션만 필터링
        filtered = [
            doc for doc in results
            if section_filter.lower() in doc.metadata.get('Header 1', '').lower()
        ]
        return filtered[:k]
    
    return results[:k]
```

### 7.3 청크 크기 관리

섹션 단위 chunking에서도 크기 관리가 필요할 수 있습니다:

- **너무 작은 섹션**: 여러 섹션을 하나로 병합
- **너무 큰 섹션**: 하위 섹션으로 추가 분할 또는 크기 제한 적용

---

## 8. 테스트 및 검증

### 8.1 Chunking 품질 검증

```python
def validate_contextual_chunking(
    documents: List[Document],
    min_chunk_size: int = 100,
    max_chunk_size: int = 5000,
) -> Dict[str, Any]:
    """
    맥락 기반 chunking 결과 검증.
    """
    stats = {
        "total_chunks": len(documents),
        "chunks_with_metadata": sum(1 for d in documents if d.metadata),
        "avg_chunk_size": sum(len(d.page_content) for d in documents) / len(documents),
        "sections_found": set(),
    }
    
    for doc in documents:
        # 섹션 정보 확인
        if "Header 1" in doc.metadata:
            stats["sections_found"].add(doc.metadata["Header 1"])
        
        # 크기 검증
        size = len(doc.page_content)
        if size < min_chunk_size:
            stats.setdefault("too_small", []).append(doc.metadata.get("Header 1", "Unknown"))
        if size > max_chunk_size:
            stats.setdefault("too_large", []).append(doc.metadata.get("Header 1", "Unknown"))
    
    stats["sections_found"] = list(stats["sections_found"])
    return stats
```

### 8.2 검색 성능 비교

기존 방식과 맥락 기반 방식 비교:

```python
def compare_chunking_strategies(
    file_path: str | Path,
    test_queries: List[str],
) -> Dict[str, Any]:
    """
    다양한 chunking 전략 비교.
    """
    # 1. 크기 기반 chunking
    manager_size = VectorStoreManager(chunking_strategy="size_based")
    docs_size = manager_size.load_document_with_contextual_chunking(file_path)
    manager_size.add_documents(docs_size, collection_name="size_based")
    
    # 2. 맥락 기반 chunking
    manager_context = VectorStoreManager(chunking_strategy="contextual")
    docs_context = manager_context.load_document_with_contextual_chunking(file_path)
    manager_context.add_documents(docs_context, collection_name="contextual")
    
    # 3. 검색 성능 비교
    results = {}
    for query in test_queries:
        results_size = manager_size.similarity_search(query, collection_name="size_based", k=5)
        results_context = manager_context.similarity_search(query, collection_name="contextual", k=5)
        
        results[query] = {
            "size_based": [d.page_content[:200] for d in results_size],
            "contextual": [d.page_content[:200] for d in results_context],
        }
    
    return results
```

---

## 9. 결론 및 권장사항

### 9.1 핵심 요약

1. **맥락 기반 chunking은 RAG 시스템의 검색 품질을 크게 향상시킵니다**
   - 의미 단위 보존
   - 컨텍스트 유지
   - 메타데이터 활용

2. **MarkdownHeaderTextSplitter가 가장 실용적인 선택입니다**
   - 구현 간단
   - LangChain 통합 용이
   - 대부분의 문서에 적용 가능

3. **프로젝트에 통합 시 고려사항**
   - VectorStoreManager 확장
   - 메타데이터 관리
   - 검색 시 섹션 정보 활용

### 9.2 다음 단계

1. ✅ **MarkdownHeaderTextSplitter 기반 구현** (1단계)
2. ⏳ **VectorStoreManager에 통합** (2단계)
3. ⏳ **성능 테스트 및 최적화** (3단계)
4. ⏳ **하이브리드 접근 추가** (4단계)

---

## 10. 참고 자료

### 10.1 프로젝트 내 관련 파일

- `tests/DOCLING_RAG_APPLICATION_REVIEW.md`: Docling RAG 적용 검토서
- `tests/test_docling_basic.py`: Docling 기본 사용법
- `tests/test_docling_advanced.py`: Docling 고급 기능
- `src/agents/sub_agents/rag_agent/vectorstore.py`: VectorStoreManager
- `src/agents/sub_agents/rag_agent/data_utils.py`: 문서 로딩 유틸리티

### 10.2 외부 참고 자료

- [Docling 공식 문서](https://docling-project.github.io/docling)
- [Docling Chunking 개념](https://docling-project.github.io/docling/concepts/chunking/)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [LangChain MarkdownHeaderTextSplitter](https://python.langchain.com/docs/modules/data_connection/document_transformers/text_splitters/markdown_header_metadata)

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX  
**작성자**: agentic_ai 프로젝트 팀






