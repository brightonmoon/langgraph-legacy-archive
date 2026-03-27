# Docling 사용법 가이드

> PDF(논문)을 Markdown으로 변환하고, Chunking하여 LangChain 및 VectorDB와 통합하는 방법

## 📋 목차

1. [PDF를 Markdown으로 변환](#1-pdf를-markdown으로-변환)
   - [기본 사용법](#11-기본-사용법)
   - [DocumentConverter 파라미터 및 설정](#12-documentconverter-파라미터-및-설정)
   - [CLI 사용법](#13-cli-사용법)
   - [이미지 처리 비활성화](#14-이미지-처리-비활성화)
   - [주요 Export 메서드](#15-주요-export-메서드)
2. [문서 Chunking 방법](#2-문서-chunking-방법)
3. [LangChain 및 VectorDB 통합](#3-langchain-및-vectordb-통합)

---

## 1. PDF를 Markdown으로 변환

### 1.1 기본 사용법

```python
from docling.document_converter import DocumentConverter

# 파일 경로 또는 URL 사용 가능
source = "document.pdf"  # 또는 "https://arxiv.org/pdf/2408.09869"
converter = DocumentConverter()
result = converter.convert(source)

# Markdown으로 변환
markdown = result.document.export_to_markdown()
print(markdown)
```

### 1.2 DocumentConverter 파라미터 및 설정

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

# 기본 변환기 생성
converter = DocumentConverter()

# 고급 설정 (필요시)
from docling.datamodel.base_models import ImageRefMode

converter = DocumentConverter(
    # OCR 설정
    enable_ocr=True,  # OCR 활성화 (스캔된 PDF용)
    ocr_lang="en",    # OCR 언어 설정 (예: "en", "ko", "en,fr")
    
    # 출력 형식 설정
    format_options={
        "markdown": {
            "table_format": "pipe",  # 테이블 형식: "pipe", "grid", "html"
            "image_ref_mode": ImageRefMode.PLACEHOLDER,  # 이미지 처리 비활성화
            # 또는 ImageRefMode.EMBEDDED (base64 인코딩)
            # 또는 ImageRefMode.REFERENCED (PNG 파일로 저장)
        }
    }
)

# 문서 변환
result = converter.convert("document.pdf")
doc = result.document

# 다양한 형식으로 export
markdown = doc.export_to_markdown()
html = doc.export_to_html()
json_dict = doc.export_to_dict()
```

### 1.3 CLI 사용법

```bash
# 기본 변환
docling document.pdf --output output_dir/

# URL에서 변환
docling https://arxiv.org/pdf/2408.09869 --output output_dir/

# OCR 옵션
docling document.pdf --ocr-lang en,ko --output output_dir/

# 특정 형식으로 변환
docling document.pdf --to md --output output.md

# 이미지 처리 비활성화 (placeholder 모드)
docling document.pdf --image-export-mode placeholder --output output_dir/

# 이미지 처리 옵션 설명:
# - placeholder: 이미지를 자리 표시자로 대체 (이미지 처리 비활성화)
# - embedded: 이미지를 base64로 인코딩하여 문서에 포함
# - referenced: 이미지를 PNG 파일로 저장하고 문서에서 참조
```

### 1.4 이미지 처리 비활성화

#### CLI에서 이미지 처리 비활성화

```bash
# 이미지를 placeholder로 대체 (이미지 처리 비활성화)
docling document.pdf --image-export-mode placeholder --output output_dir/

# 이미지 처리 모드 옵션:
# - placeholder: 이미지를 자리 표시자로 대체 (처리 비활성화, 가장 빠름)
# - embedded: 이미지를 base64로 인코딩하여 문서에 포함 (파일 크기 증가)
# - referenced: 이미지를 PNG 파일로 저장하고 문서에서 참조 (기본값)
```

#### Python API에서 이미지 처리 비활성화

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import ImageRefMode

# 방법 1: format_options 사용
converter = DocumentConverter(
    format_options={
        "markdown": {
            "image_ref_mode": ImageRefMode.PLACEHOLDER,  # 이미지 처리 비활성화
        }
    }
)

# 방법 2: export 시 옵션 지정
result = converter.convert("document.pdf")
markdown = result.document.export_to_markdown(
    image_ref_mode=ImageRefMode.PLACEHOLDER
)
```

**참고**: `ImageRefMode.PLACEHOLDER`를 사용하면 이미지가 텍스트로만 표시되어 처리 속도가 향상되고 메모리 사용량이 감소합니다. 이미지 내용이 필요 없는 경우에 유용합니다.

### 1.5 주요 Export 메서드

```python
# Markdown (가장 일반적)
markdown = result.document.export_to_markdown()

# HTML
html = result.document.export_to_html()

# JSON (구조화된 데이터)
json_data = result.document.export_to_dict()

# 문서 구조 정보 접근
for item in result.document.iterate_items():
    print(f"Item type: {type(item).__name__}")
    # TextItem, TableItem, PictureItem, FormulaItem 등
```

---

## 2. 문서 Chunking 방법

Docling은 두 가지 주요 Chunking 방식을 제공합니다:

### 2.1 방법 A: 네이티브 Docling Chunker 사용 (권장)

#### HybridChunker (토큰 기반 + 구조 인식)

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document

# 1. 문서 변환
converter = DocumentConverter()
result = converter.convert("document.pdf")

# 2. HybridChunker 생성
chunker = HybridChunker(
    tokenizer="bert-base-uncased",  # 또는 "gpt-4", "cl100k_base"
    chunk_size=1000,  # 토큰 단위
    chunk_overlap=200,  # 토큰 단위
    merge_peers=True,  # 작은 연속 청크 병합 (기본값: True)
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

**설치 요구사항**:
```bash
# HuggingFace 토크나이저 사용 시
pip install 'docling-core[chunking]'

# OpenAI tiktoken 사용 시
pip install 'docling-core[chunking-openai]'
```

#### HierarchicalChunker (구조 기반)

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
        metadata={
            "source": "document.pdf",
            **chunk.metadata
        }
    )
    for chunk in chunks
]
```

### 2.2 방법 B: Markdown Export 후 LangChain TextSplitter 사용

#### 기본 사용법

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
    chunk_size=1000,  # 문자 단위
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""],  # 분할 우선순위
)
chunks = text_splitter.split_documents([doc])
```

#### Markdown 헤더 기반 Chunking (섹션 인식)

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Markdown 헤더를 기준으로 분할
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False,  # 헤더 유지하여 섹션 정보 보존
)

chunks = markdown_splitter.split_text(markdown)

# LangChain Document로 변환
documents = [
    Document(
        page_content=chunk.page_content,
        metadata={
            "source": "document.pdf",
            **chunk.metadata,  # Header 1, Header 2 등 포함
        }
    )
    for chunk in chunks
]
```

### 2.3 방법 C: LangChain DoclingLoader 사용

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

### 2.4 Chunking 전략 비교

| 방법 | 장점 | 단점 | 권장 사용 사례 |
|------|------|------|---------------|
| **HybridChunker** | 토큰 정확도, 구조 인식, 작은 청크 병합 | 토크나이저 필요 | LLM 컨텍스트 윈도우 고려 시 |
| **HierarchicalChunker** | 문서 구조 완벽 보존 | 크기 제한 없음 | 구조화된 문서 (논문 등) |
| **Markdown + TextSplitter** | 기존 인프라 호환, 유연함 | 구조 정보 손실 가능 | 기존 LangChain 파이프라인 |
| **Markdown + HeaderSplitter** | 섹션 인식, 메타데이터 풍부 | 헤더 없는 문서에 부적합 | 논문, 기술 문서 |

---

## 3. LangChain 및 VectorDB 통합

### 3.1 FAISS VectorDB 통합

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document

# 1. 문서 변환 및 Chunking
converter = DocumentConverter()
result = converter.convert("document.pdf")

chunker = HybridChunker(
    tokenizer="bert-base-uncased",
    chunk_size=1000,
    chunk_overlap=200,
)

chunks = list(chunker.chunk(result.document))
documents = [
    Document(
        page_content=chunker.contextualize(chunk),
        metadata={"source": "document.pdf", **chunk.metadata}
    )
    for chunk in chunks
]

# 2. Embedding 생성 및 VectorDB 저장
embeddings = OpenAIEmbeddings()  # 또는 다른 Embedding 모델
vectorstore = FAISS.from_documents(documents, embeddings)

# 3. VectorDB 저장
vectorstore.save_local("faiss_index")

# 4. 검색 사용
query = "What is the main contribution?"
results = vectorstore.similarity_search(query, k=5)
for doc in results:
    print(f"Score: {doc.metadata}")
    print(f"Content: {doc.page_content[:200]}...")
```

### 3.2 Chroma VectorDB 통합

```python
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 1. 문서 준비 (위와 동일)
# ... (변환 및 chunking 코드)

# 2. Chroma VectorDB 생성
chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

vectorstore = Chroma.from_documents(
    documents=documents,
    embedding=OpenAIEmbeddings(),
    persist_directory="./chroma_db",
    collection_name="research_papers"
)

# 3. 검색
query = "What methods were used?"
results = vectorstore.similarity_search_with_score(query, k=5)
for doc, score in results:
    print(f"Score: {score}")
    print(f"Section: {doc.metadata.get('Header 2', 'N/A')}")
    print(f"Content: {doc.page_content[:200]}...")
```

### 3.3 RAG 체인 구성 (LangChain)

```python
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# 1. VectorDB 로드
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

# 2. LLM 초기화
llm = ChatOpenAI(model_name="gpt-4", temperature=0)

# 3. RAG 체인 생성
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # 또는 "map_reduce", "refine", "map_rerank"
    retriever=vectorstore.as_retriever(
        search_type="similarity",  # 또는 "mmr", "similarity_score_threshold"
        search_kwargs={"k": 5}  # 상위 5개 문서 검색
    ),
    return_source_documents=True,
)

# 4. 질문 답변
query = "What are the key findings of this research?"
result = qa_chain({"query": query})

print(f"Answer: {result['result']}")
print(f"\nSources:")
for doc in result['source_documents']:
    print(f"  - {doc.metadata.get('source', 'N/A')} (Section: {doc.metadata.get('Header 2', 'N/A')})")
```

### 3.4 완전한 워크플로우 예제

```python
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

def process_paper_to_vectordb(
    pdf_path: str | Path,
    output_dir: str | Path = "vectorstore",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
):
    """
    논문 PDF를 처리하여 VectorDB에 저장하는 완전한 워크플로우
    """
    # 1. 문서 변환
    print("📄 Converting PDF to structured document...")
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    
    # 2. Chunking
    print("✂️  Chunking document...")
    chunker = HybridChunker(
        tokenizer="bert-base-uncased",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    chunks = list(chunker.chunk(result.document))
    documents = [
        Document(
            page_content=chunker.contextualize(chunk),
            metadata={
                "source": str(pdf_path),
                "chunk_id": i,
                **chunk.metadata,
            }
        )
        for i, chunk in enumerate(chunks)
    ]
    
    print(f"✅ Created {len(documents)} chunks")
    
    # 3. Embedding 및 VectorDB 저장
    print("🔢 Creating embeddings and saving to VectorDB...")
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(output_path))
    
    print(f"💾 VectorDB saved to {output_path}")
    
    return vectorstore, documents


def create_rag_chain(vectorstore_path: str | Path, model_name: str = "gpt-4"):
    """
    VectorDB를 사용하여 RAG 체인 생성
    """
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local(
        str(vectorstore_path),
        embeddings,
        allow_dangerous_deserialization=True
    )
    
    llm = ChatOpenAI(model_name=model_name, temperature=0)
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
    )
    
    return qa_chain


# 사용 예제
if __name__ == "__main__":
    # 1. PDF 처리 및 VectorDB 저장
    pdf_file = "research_paper.pdf"
    vectorstore, documents = process_paper_to_vectordb(
        pdf_file,
        output_dir="vectorstore/research_paper",
        chunk_size=1000,
        chunk_overlap=200,
    )
    
    # 2. RAG 체인 생성
    qa_chain = create_rag_chain("vectorstore/research_paper")
    
    # 3. 질문 답변
    query = "What is the main contribution of this paper?"
    result = qa_chain({"query": query})
    
    print(f"\n❓ Question: {query}")
    print(f"\n💡 Answer:\n{result['result']}")
    print(f"\n📚 Sources:")
    for i, doc in enumerate(result['source_documents'], 1):
        section = doc.metadata.get('Header 2', doc.metadata.get('section_name', 'N/A'))
        print(f"  {i}. {section} (from {doc.metadata.get('source', 'N/A')})")
```

### 3.5 메타데이터 활용 팁

```python
# Chunking 시 메타데이터 추가
documents = [
    Document(
        page_content=chunker.contextualize(chunk),
        metadata={
            "source": "document.pdf",
            "page_number": chunk.metadata.get("page", 0),
            "section": chunk.metadata.get("Header 2", "Unknown"),
            "subsection": chunk.metadata.get("Header 3", ""),
            "chunk_index": i,
            "chunk_type": type(chunk).__name__,
        }
    )
    for i, chunk in enumerate(chunks)
]

# 메타데이터 필터링 검색
vectorstore = FAISS.from_documents(documents, embeddings)

# 특정 섹션만 검색
results = vectorstore.similarity_search(
    query="methodology",
    k=5,
    filter={"section": "Methods"}  # 메타데이터 필터
)
```

---

## 📚 참고 자료

- [Docling 공식 문서](https://docling-project.github.io/docling/)
- [Docling GitHub](https://github.com/docling-project/docling)
- [LangChain Docling 통합](https://python.langchain.com/docs/integrations/document_loaders/docling)
- [LangChain Vector Stores](https://python.langchain.com/docs/modules/data_connection/vectorstores/)

---

## 🔧 설치 요구사항

```bash
# 기본 Docling
pip install docling

# Chunking 기능 (HybridChunker, HierarchicalChunker)
pip install 'docling-core[chunking]'

# LangChain 통합
pip install langchain langchain-core langchain-community langchain-openai

# VectorDB
pip install faiss-cpu  # 또는 faiss-gpu
# 또는
pip install chromadb
```

---

**작성일**: 2025-01-27  
**버전**: Docling v2.65.0+

