# Docling RAG 적용 검토서

## 📋 개요

본 문서는 Docling을 RAG(Retrieval-Augmented Generation) 시스템에 적용하기 위한 검토서입니다. 특히 문서 청킹(chunking) 관련 기능과 옵션에 대해 중점적으로 다룹니다.

**작성일**: 2025-01-XX  
**검토 대상**: Docling v2.65.0 이상  
**검토 목적**: RAG 시스템 구축을 위한 Docling의 chunking 지원 현황 및 적용 방안 검토

---

## 1. Docling의 RAG 지원 현황

### 1.1 기본 기능

Docling은 다양한 문서 형식을 파싱하고 구조화된 형식으로 변환하는 도구입니다. RAG 시스템 구축을 위한 핵심 기능은 다음과 같습니다:

- ✅ **문서 파싱**: PDF, DOCX, PPTX, XLSX, HTML, 이미지 등 다양한 형식 지원
- ✅ **구조 보존**: 페이지 레이아웃, 읽기 순서, 테이블 구조, 코드, 수식 등 보존
- ✅ **출력 형식**: Markdown, HTML, JSON 등 다양한 형식으로 export 가능
- ✅ **AI 프레임워크 통합**: LangChain, LlamaIndex, Crew AI, Haystack 등과 통합 지원

### 1.2 Chunking 기능 지원 현황

**✅ Docling은 네이티브 chunking 기능을 제공합니다!**

Docling은 `DoclingDocument`를 직접 처리하는 네이티브 chunker를 제공합니다. [공식 문서](https://docling-project.github.io/docling/concepts/chunking/)에 따르면 두 가지 접근 방식이 있습니다:

1. **네이티브 Docling Chunker 사용** (권장)
   - `BaseChunker`, `HybridChunker`, `HierarchicalChunker` 제공
   - 문서 구조 정보를 직접 활용
   - 토큰화 인식 개선 기능 포함

2. **Markdown Export 후 외부 Chunker 사용**
   - Markdown으로 export한 후 LangChain의 `TextSplitter` 사용
   - 기존 RAG 인프라와의 호환성 우수

---

## 2. RAG를 위한 Chunking 워크플로우

### 2.1 워크플로우 옵션

Docling을 사용한 RAG 구축에는 두 가지 주요 워크플로우가 있습니다:

#### 옵션 A: 네이티브 Docling Chunker 사용 (권장)

```
문서 (PDF/DOCX 등)
    ↓
Docling DocumentConverter
    ↓
DoclingDocument (구조화된 문서)
    ↓
Docling Native Chunker (HybridChunker / HierarchicalChunker)
    ↓
BaseChunk 객체들 (메타데이터 포함)
    ↓
contextualize() → 텍스트 문자열
    ↓
LangChain Document 객체로 변환
    ↓
Embedding & Vector Store
```

#### 옵션 B: Markdown Export 후 외부 Chunker 사용

```
문서 (PDF/DOCX 등)
    ↓
Docling DocumentConverter
    ↓
DoclingDocument (구조화된 문서)
    ↓
export_to_markdown() / export_to_html() / export_to_dict()
    ↓
텍스트 문자열
    ↓
LangChain Document 객체로 변환
    ↓
LangChain TextSplitter (RecursiveCharacterTextSplitter 등)
    ↓
Chunked Documents
    ↓
Embedding & Vector Store
```

### 2.2 구현 예시

#### 방법 1: 네이티브 HybridChunker 사용 (권장)

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document

# 1. Docling으로 문서 변환
converter = DocumentConverter()
result = converter.convert("document.pdf")

# 2. HybridChunker 생성 및 사용
# 토큰화 인식 개선 + 계층적 chunking
chunker = HybridChunker(
    tokenizer="bert-base-uncased",  # 또는 다른 토크나이저
    chunk_size=1000,  # 토큰 단위
    chunk_overlap=200,
    merge_peers=True,  # 작은 청크 병합 (기본값: True)
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
            "source": "document.pdf",
            **chunk.metadata,  # Docling chunk의 메타데이터 포함
        }
    )
    documents.append(doc)
```

#### 방법 2: HierarchicalChunker 사용

```python
from docling.chunking import HierarchicalChunker
from langchain_core.documents import Document

# 계층적 구조 기반 chunking
chunker = HierarchicalChunker(
    merge_list_items=True,  # 리스트 아이템 병합 (기본값: True)
)

chunks = list(chunker.chunk(result.document))

# LangChain Document로 변환
documents = [
    Document(
        page_content=chunker.contextualize(chunk),
        metadata={"source": "document.pdf", **chunk.metadata}
    )
    for chunk in chunks
]
```

#### 방법 3: Markdown Export 후 LangChain TextSplitter 사용

```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Docling으로 문서 변환
converter = DocumentConverter()
result = converter.convert("document.pdf")

# 2. Markdown으로 export
markdown = result.document.export_to_markdown()

# 3. LangChain Document 생성
doc = Document(
    page_content=markdown,
    metadata={
        "source": "document.pdf",
        "total_items": len(list(result.document.iterate_items())),
    }
)

# 4. Chunking 수행
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents([doc])
```

#### 방법 4: LangChain DoclingLoader 사용

```python
from langchain_community.document_loaders import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. DoclingLoader로 직접 로드
loader = DoclingLoader("document.pdf")
documents = loader.load()

# 2. Chunking 수행
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(documents)
```

---

## 3. Chunking 옵션 및 전략

### 3.1 Docling 네이티브 Chunker

#### BaseChunker (기본 인터페이스)

모든 Docling chunker의 기본 클래스입니다. 다음 메서드를 제공합니다:

- `chunk(dl_doc: DoclingDocument, **kwargs) -> Iterator[BaseChunk]`: 문서를 청크로 분할
- `contextualize(chunk: BaseChunk) -> str`: 메타데이터가 포함된 텍스트 생성 (임베딩 모델 입력용)

#### HybridChunker (권장)

**특징**:
- 토큰화 인식 개선을 통한 정밀한 chunking
- 계층적 chunking 기반
- 토큰 크기 기준으로 청크 분할/병합
- 연속된 작은 청크를 병합하여 컨텍스트 유지

**설치**:
```bash
# HuggingFace 토크나이저 사용 시
pip install 'docling-core[chunking]'

# OpenAI tiktoken 사용 시
pip install 'docling-core[chunking-openai]'
```

**사용 예시**:
```python
from docling.chunking import HybridChunker

chunker = HybridChunker(
    tokenizer="bert-base-uncased",  # 또는 "gpt-4", "cl100k_base" 등
    chunk_size=1000,  # 토큰 단위
    chunk_overlap=200,
    merge_peers=True,  # 작은 연속 청크 병합 (기본값: True)
)

chunks = list(chunker.chunk(docling_document))
```

**옵션**:
- `tokenizer`: 토크나이저 이름 (HuggingFace 모델명 또는 tiktoken 인코딩)
- `chunk_size`: 최대 청크 크기 (토큰 단위)
- `chunk_overlap`: 청크 간 겹침 (토큰 단위)
- `merge_peers`: 작은 연속 청크 병합 여부 (기본값: True)

#### HierarchicalChunker

**특징**:
- 문서 구조 정보를 활용한 계층적 chunking
- 각 문서 요소를 개별 청크로 생성
- 리스트 아이템은 기본적으로 병합 (옵션으로 비활성화 가능)
- 헤더와 캡션 정보를 메타데이터로 포함

**사용 예시**:
```python
from docling.chunking import HierarchicalChunker

chunker = HierarchicalChunker(
    merge_list_items=True,  # 리스트 아이템 병합 (기본값: True)
)

chunks = list(chunker.chunk(docling_document))
```

**옵션**:
- `merge_list_items`: 리스트 아이템 병합 여부 (기본값: True)

### 3.2 LangChain TextSplitter 옵션 (대안)

Markdown export 후 사용할 수 있는 주요 TextSplitter:

#### RecursiveCharacterTextSplitter (권장)
- **특징**: 재귀적으로 텍스트를 분할하여 의미 단위 유지
- **옵션**:
  - `chunk_size`: 청크 크기 (기본값: 1000)
  - `chunk_overlap`: 청크 간 겹침 (기본값: 200)
  - `length_function`: 길이 측정 함수
  - `separators`: 분할 구분자 우선순위

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""],
)
```

#### CharacterTextSplitter
- **특징**: 단순 문자 단위 분할
- **옵션**: `chunk_size`, `chunk_overlap`, `separator`

#### TokenTextSplitter
- **특징**: 토큰 수 기준 분할 (LLM 컨텍스트 윈도우 고려)
- **옵션**: `chunk_size`, `chunk_overlap`, `encoding_name`

#### MarkdownHeaderTextSplitter
- **특징**: Markdown 헤더 구조를 고려한 분할
- **장점**: Docling이 Markdown으로 export하므로 구조 보존에 유리

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on
)
chunks = markdown_splitter.split_text(markdown)
```

### 3.3 Docling 구조 정보 활용 전략

네이티브 chunker가 구조 정보를 자동으로 활용하지만, 커스텀 전략도 가능합니다:

#### 전략 1: 아이템 단위 Chunking
```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document

converter = DocumentConverter()
result = converter.convert("document.pdf")

# iterate_items()를 사용하여 구조 단위로 분할
documents = []
for item_tuple in result.document.iterate_items():
    item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
    depth = item_tuple[1] if isinstance(item_tuple, tuple) else 0
    
    # 각 아이템을 별도 Document로 생성
    if hasattr(item, 'text') and item.text:
        doc = Document(
            page_content=item.text,
            metadata={
                "source": "document.pdf",
                "item_type": type(item).__name__,
                "depth": depth,
            }
        )
        documents.append(doc)
```

#### 전략 2: 테이블 단위 Chunking
```python
# 테이블을 별도로 추출하여 하나의 청크로 처리
tables = result.document.tables
for table in tables:
    if hasattr(table, 'data'):
        table_text = table.data.to_markdown()  # 또는 다른 형식
        doc = Document(
            page_content=table_text,
            metadata={
                "source": "document.pdf",
                "type": "table",
            }
        )
        documents.append(doc)
```

#### 전략 3: 섹션 단위 Chunking
```python
# Markdown 헤더를 기준으로 섹션 단위 분할
markdown = result.document.export_to_markdown()
# MarkdownHeaderTextSplitter 사용
```

---

## 4. 기존 파서와의 비교

### 4.1 Chunking 관점에서의 비교

| 파서 | 네이티브 Chunking | 구조 보존 | 테이블 처리 | 복잡한 레이아웃 | 토큰화 인식 |
|------|-----------------|----------|------------|----------------|------------|
| **Docling** | ✅ **네이티브 지원** (HybridChunker, HierarchicalChunker) | ✅ 우수 | ✅ 우수 | ✅ 우수 | ✅ 지원 |
| **PyPDFLoader** | ❌ (외부 라이브러리 필요) | ⚠️ 제한적 | ⚠️ 제한적 | ⚠️ 제한적 | ❌ |
| **PyMuPDF** | ❌ (외부 라이브러리 필요) | ⚠️ 보통 | ⚠️ 보통 | ⚠️ 보통 | ❌ |
| **UnstructuredPDFLoader** | ❌ (외부 라이브러리 필요) | ✅ 우수 | ✅ 우수 | ✅ 우수 | ❌ |

### 4.2 RAG 적용 시 고려사항

#### Docling의 장점
1. **네이티브 Chunking 지원**: HybridChunker, HierarchicalChunker 등 제공
2. **토큰화 인식**: 임베딩 모델 토크나이저와 정렬된 정밀한 chunking
3. **구조 정보 보존**: 테이블, 수식, 이미지 등 구조 정보를 메타데이터로 활용
4. **읽기 순서 인식**: 논리적 읽기 순서를 고려한 chunking
5. **다양한 형식 지원**: PDF뿐만 아니라 Office 문서, HTML 등 통합 처리
6. **LangChain 통합**: `DoclingLoader`로 간편한 통합
7. **유연성**: 네이티브 chunker 또는 Markdown export 후 외부 chunker 선택 가능

#### Docling의 단점
1. **처리 속도**: 고급 기능 사용 시 상대적으로 느림
2. **의존성**: 많은 의존성 필요 (특히 chunking 기능 사용 시)
3. **토크나이저 설정**: HybridChunker 사용 시 적절한 토크나이저 선택 필요

---

## 5. 프로젝트 적용 방안

### 5.1 현재 프로젝트 구조

프로젝트에서는 이미 다음과 같은 RAG 인프라를 구축하고 있습니다:

- **VectorStoreManager**: FAISS 기반 벡터 스토어 관리
- **RecursiveCharacterTextSplitter**: 기본 chunking 전략
- **Ollama Embeddings**: bge-m3 모델 사용

### 5.2 Docling 통합 제안

#### 옵션 1: 네이티브 HybridChunker 사용 (최고 권장)

```python
# src/agents/sub_agents/rag_agent/data_utils.py에 추가
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document

def load_docling_with_native_chunker(
    file_path: str | Path,
    *,
    tokenizer: str = "bert-base-uncased",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    merge_peers: bool = True,
) -> List[Document]:
    """
    Docling 네이티브 HybridChunker를 사용하여 문서 로드 및 chunking.
    
    Args:
        file_path: 문서 파일 경로
        tokenizer: 토크나이저 이름 (HuggingFace 모델명 또는 tiktoken 인코딩)
        chunk_size: 최대 청크 크기 (토큰 단위)
        chunk_overlap: 청크 간 겹침 (토큰 단위)
        merge_peers: 작은 연속 청크 병합 여부
        
    Returns:
        Document 객체 리스트
    """
    # 1. 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    # 2. HybridChunker 생성
    chunker = HybridChunker(
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        merge_peers=merge_peers,
    )
    
    # 3. Chunking 수행
    chunks = list(chunker.chunk(result.document))
    
    # 4. LangChain Document로 변환
    documents = []
    for chunk in chunks:
        text = chunker.contextualize(chunk)
        doc = Document(
            page_content=text,
            metadata={
                "source": str(file_path),
                "file_type": "docling",
                **chunk.metadata,  # Docling chunk의 메타데이터 포함
            }
        )
        documents.append(doc)
    
    return documents
```

#### 옵션 2: LangChain DoclingLoader 사용

```python
# src/agents/sub_agents/rag_agent/data_utils.py에 추가
from langchain_community.document_loaders import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_docling_documents(
    file_path: str | Path,
    *,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """
    DoclingLoader를 사용하여 문서를 로드하고 chunking 수행.
    
    Args:
        file_path: 문서 파일 경로
        chunk_size: 청크 크기
        chunk_overlap: 청크 간 겹침
        
    Returns:
        Document 객체 리스트
    """
    loader = DoclingLoader(str(file_path))
    documents = loader.load()
    
    # 메타데이터 추가
    for doc in documents:
        doc.metadata["file_type"] = "docling"
        doc.metadata["source"] = str(file_path)
    
    # Chunking 수행
    if chunk_size is not None:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap or 0,
        )
        documents = splitter.split_documents(documents)
    
    return documents
```

#### 옵션 3: HierarchicalChunker 사용

```python
def load_docling_with_structure(
    file_path: str | Path,
    *,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    use_structure: bool = True,
) -> List[Document]:
    """
    Docling의 구조 정보를 활용한 고급 chunking.
    """
    from docling.document_converter import DocumentConverter
    from langchain_core.documents import Document
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        MarkdownHeaderTextSplitter,
    )
    
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    if use_structure:
        # Markdown 헤더 기반 분할
        markdown = result.document.export_to_markdown()
        
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        chunks = markdown_splitter.split_text(markdown)
        
        documents = [
            Document(
                page_content=chunk.page_content,
                metadata={**chunk.metadata, "source": str(file_path)}
            )
            for chunk in chunks
        ]
    else:
        # 기본 Markdown → Chunking
        markdown = result.document.export_to_markdown()
        doc = Document(
            page_content=markdown,
            metadata={"source": str(file_path)}
        )
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or 1000,
            chunk_overlap=chunk_overlap or 200,
        )
        documents = splitter.split_documents([doc])
    
    return documents
```

### 5.3 Chunking 옵션 설정

프로젝트의 `VectorStoreManager`에 Docling 전용 옵션 추가:

```python
# src/agents/sub_agents/rag_agent/vectorstore.py

class VectorStoreManager:
    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        vectorstore_dir: Optional[str | Path] = None,
        # Docling 전용 옵션 추가
        docling_chunk_strategy: str = "hybrid",  # "hybrid", "hierarchical", "langchain"
        docling_tokenizer: str = "bert-base-uncased",  # HybridChunker용
        docling_chunk_size: int = 1000,  # 토큰 단위
        docling_chunk_overlap: int = 200,  # 토큰 단위
        docling_merge_peers: bool = True,  # HybridChunker용
    ):
        # ... 기존 코드 ...
        self.docling_chunk_strategy = docling_chunk_strategy
        self.docling_tokenizer = docling_tokenizer
        self.docling_chunk_size = docling_chunk_size
        self.docling_chunk_overlap = docling_chunk_overlap
        self.docling_merge_peers = docling_merge_peers
```

---

## 6. 테스트 계획

### 6.1 Chunking 전략 비교 테스트

다음 전략들을 비교 테스트:

1. **HybridChunker (네이티브)** ⭐ 권장
   - `tokenizer="bert-base-uncased", chunk_size=1000, chunk_overlap=200`
   - 토큰화 인식 개선 + 계층적 chunking

2. **HierarchicalChunker (네이티브)**
   - 구조 기반 chunking
   - `merge_list_items=True`

3. **RecursiveCharacterTextSplitter (LangChain)**
   - `chunk_size=1000, chunk_overlap=200`
   - Markdown export 후 사용

4. **MarkdownHeaderTextSplitter (LangChain)**
   - Docling의 Markdown export 활용
   - 섹션 구조 보존

### 6.2 평가 지표

- **Chunk 품질**: 의미 단위 보존 정도
- **검색 정확도**: RAG 검색 성능
- **처리 속도**: 문서 변환 및 chunking 시간
- **메타데이터 풍부도**: 구조 정보 보존 정도

---

## 7. 권장 사항

### 7.1 Chunking 전략 선택 가이드

| 문서 유형 | 권장 전략 | 이유 |
|----------|----------|------|
| **일반 문서** | **HybridChunker** ⭐ | 토큰화 인식 + 구조 보존 |
| **논문/보고서** | **HybridChunker** 또는 HierarchicalChunker | 섹션 구조 보존 + 토큰 정렬 |
| **테이블 중심 문서** | HierarchicalChunker | 구조 정보 최대 활용 |
| **복잡한 레이아웃** | HybridChunker | 구조 정보 + 토큰 정밀도 |
| **기존 RAG 인프라 통합** | LangChain TextSplitter (Markdown export 후) | 호환성 우선 |

### 7.2 Chunking 파라미터 권장값

#### HybridChunker (토큰 단위)

```python
# 일반적인 문서
chunker = HybridChunker(
    tokenizer="bert-base-uncased",  # 또는 임베딩 모델과 동일한 토크나이저
    chunk_size=1000,  # 토큰 단위
    chunk_overlap=200,
    merge_peers=True,
)

# 긴 문서 (논문 등)
chunker = HybridChunker(
    tokenizer="bert-base-uncased",
    chunk_size=2000,  # 토큰 단위
    chunk_overlap=300,
    merge_peers=True,
)

# 짧은 문서 (뉴스, 블로그 등)
chunker = HybridChunker(
    tokenizer="bert-base-uncased",
    chunk_size=500,  # 토큰 단위
    chunk_overlap=100,
    merge_peers=True,
)
```

#### LangChain TextSplitter (문자 단위)

```python
# 일반적인 문서
chunk_size=1000  # 문자 단위
chunk_overlap=200

# 긴 문서 (논문 등)
chunk_size=2000
chunk_overlap=300

# 짧은 문서 (뉴스, 블로그 등)
chunk_size=500
chunk_overlap=100
```

**중요**: HybridChunker는 토큰 단위, LangChain TextSplitter는 문자 단위입니다!

### 7.3 구현 우선순위

1. **1단계**: HybridChunker 네이티브 통합 ⭐
   - `docling-core[chunking]` 설치
   - `load_docling_with_native_chunker()` 함수 구현
   - 임베딩 모델과 동일한 토크나이저 설정

2. **2단계**: HierarchicalChunker 옵션 추가
   - 구조 기반 chunking이 필요한 문서에 적용

3. **3단계**: LangChain 통합 (대안)
   - 기존 RAG 인프라와의 호환성 유지
   - DoclingLoader + TextSplitter 조합

---

## 8. 결론

### 8.1 핵심 요약

1. **✅ Docling은 네이티브 chunking 기능을 제공합니다!**
   - `HybridChunker`: 토큰화 인식 개선 + 계층적 chunking (권장)
   - `HierarchicalChunker`: 문서 구조 기반 chunking
   - `BaseChunker`: 커스텀 chunker 구현을 위한 기본 인터페이스

2. **Docling의 강점**
   - **토큰화 인식**: 임베딩 모델 토크나이저와 정렬된 정밀한 chunking
   - **구조 정보 보존**: 테이블, 수식, 이미지 등 구조 정보를 메타데이터로 활용
   - **유연성**: 네이티브 chunker 또는 Markdown export 후 외부 chunker 선택 가능

3. **LangChain 통합**
   - `DoclingLoader`를 통해 쉽게 통합 가능
   - 네이티브 chunker 결과를 LangChain Document로 변환 가능
   - 기존 RAG 인프라와 호환성 우수

4. **다양한 chunking 전략 적용 가능**
   - **HybridChunker** (네이티브, 권장): 토큰 정렬 + 구조 보존
   - **HierarchicalChunker** (네이티브): 구조 기반
   - **LangChain TextSplitter** (대안): Markdown export 후 사용

### 8.2 다음 단계

1. ✅ Docling 기본 통합 테스트
2. ⏳ Chunking 전략 비교 테스트
3. ⏳ 프로덕션 적용 및 성능 모니터링

---

## 9. 참고 자료

### 9.1 공식 문서
- [Docling GitHub](https://github.com/docling-project/docling)
- [Docling 공식 문서](https://docling-project.github.io/docling)
- [Docling Chunking 개념](https://docling-project.github.io/docling/concepts/chunking/) ⭐
- [LangChain Docling 통합](https://python.langchain.com/docs/integrations/document_loaders/docling)

### 9.2 프로젝트 내 관련 파일
- `tests/test_docling_basic.py`: Docling 기본 사용법
- `tests/test_docling_advanced.py`: Docling 고급 기능
- `tests/test_docling_comparison.py`: 기존 파서와의 비교
- `src/agents/sub_agents/rag_agent/vectorstore.py`: RAG 벡터 스토어 관리
- `src/agents/sub_agents/rag_agent/data_utils.py`: 문서 로딩 유틸리티

### 9.3 관련 문서
- `tests/README_DOCLING_SETUP.md`: Docling 설치 및 사용 가이드
- `.cursor/docs/rag_agent_manual.mdc`: RAG 에이전트 매뉴얼

---

**문서 버전**: 2.0  
**최종 업데이트**: 2025-01-XX  
**주요 변경사항**: Docling 네이티브 chunking 기능 추가 (HybridChunker, HierarchicalChunker)

