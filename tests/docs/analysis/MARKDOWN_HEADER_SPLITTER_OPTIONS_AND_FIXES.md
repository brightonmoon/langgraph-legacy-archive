# MarkdownHeaderTextSplitter 옵션 및 섹션 구분 문제 해결

## 📋 문제 분석

마크다운 파일에서 헤더가 하위 내용을 제대로 커버하지 못하는 문제가 발견되었습니다.

**문제 파일**: `Catalytic inhibition of KAT6KAT7 enhances the efficacy and overcomes primary and acquired resistance to Menin inhibitors in MLL leukaemia.md`

**문제 상황**:
```
## METHODS

## Chemicals
[내용...]

## Cell Culture
[내용...]
```

`## METHODS` 헤더가 그 하위 헤더들(`## Chemicals`, `## Cell Culture` 등)을 포함하지 못하고 있습니다.

---

## 1. MarkdownHeaderTextSplitter 옵션 확인

### 1.1 사용 가능한 옵션

```python
MarkdownHeaderTextSplitter.__init__(
    headers_to_split_on: list[tuple[str, str]],  # 필수: 분할할 헤더 레벨
    return_each_line: bool = False,                # 각 줄을 반환할지 여부
    strip_headers: bool = True,                  # 헤더를 제거할지 여부 ⚠️
    custom_header_patterns: dict[str, int] | None = None  # 커스텀 헤더 패턴
)
```

### 1.2 주요 옵션 설명

#### `strip_headers` (기본값: True) ⚠️
- **True**: 헤더를 제거하고 내용만 반환
- **False**: 헤더를 포함하여 반환
- **문제**: 헤더가 제거되면 섹션 구분이 어려울 수 있음

#### `return_each_line` (기본값: False)
- **True**: 각 줄을 개별 청크로 반환
- **False**: 헤더 기준으로 섹션 단위로 반환

#### `headers_to_split_on`
- 분할할 헤더 레벨 지정
- 예: `[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]`

---

## 2. 문제 원인 분석

### 2.1 현재 동작 방식

MarkdownHeaderTextSplitter는 다음과 같이 동작합니다:

1. 지정된 헤더 레벨을 찾음
2. 각 헤더를 기준으로 분할
3. **하위 헤더가 있으면 그 하위 헤더까지만 포함**
4. 다음 상위 헤더가 나오면 새로운 청크 시작

**문제점**:
- `## METHODS` 다음에 `## Chemicals`가 오면
- `## METHODS` 청크는 비어있거나 매우 짧음
- `## Chemicals`가 새로운 청크로 시작됨

### 2.2 실제 마크다운 구조

```markdown
## METHODS

## Chemicals
[내용...]

## Cell Culture
[내용...]

## Immunoblotting
[내용...]
```

이 경우 `## METHODS`는 상위 섹션이지만, MarkdownHeaderTextSplitter는 이를 인식하지 못합니다.

---

## 3. 해결 방안

### 3.1 방안 1: strip_headers=False로 설정

헤더를 유지하여 섹션 정보를 보존합니다.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("##", "Header 2"),  # METHODS, INTRODUCTION 등
        ("###", "Header 3"),  # Chemicals, Cell Culture 등
    ],
    strip_headers=False,  # 헤더 유지
)
```

**장점**:
- ✅ 헤더 정보 보존
- ✅ 섹션 구분 명확

**단점**:
- ⚠️ 헤더가 내용에 포함되어 중복될 수 있음

### 3.2 방안 2: 헤더 레벨 조정

상위 헤더만 분할하고 하위 헤더는 포함하도록 설정합니다.

```python
# 상위 헤더만 분할 (METHODS, INTRODUCTION 등)
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("##", "Header 2"),  # METHODS, INTRODUCTION, RESULTS 등만 분할
    ],
    strip_headers=False,
)
```

**장점**:
- ✅ 상위 섹션 단위로 분할
- ✅ 하위 헤더들이 상위 섹션에 포함됨

**단점**:
- ⚠️ METHODS 섹션이 너무 클 수 있음 (30,000자 이상)

### 3.3 방안 3: 커스텀 헤더 패턴 사용

논문의 특정 섹션을 인식하도록 커스텀 패턴을 사용합니다.

```python
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("##", "Header 2"),
    ],
    custom_header_patterns={
        r"^##\s*(ABSTRACT|INTRODUCTION|METHODS|RESULTS|DISCUSSION|References)": 2,
    },
    strip_headers=False,
)
```

### 3.4 방안 4: 하이브리드 접근 (권장 ⭐⭐⭐)

상위 헤더로 먼저 분할하고, 큰 섹션은 추가로 분할합니다.

```python
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

def chunk_markdown_with_hierarchy(
    markdown: str,
    top_level_headers: List[Tuple[str, str]] = None,
    max_chunk_size: int = 2000,
) -> List[Document]:
    """
    계층적 마크다운 chunking:
    1. 상위 헤더(##)로 먼저 분할
    2. 큰 섹션은 하위 헤더(###)로 추가 분할
    3. 여전히 크면 크기 제한으로 분할
    """
    if top_level_headers is None:
        top_level_headers = [("##", "Header 2")]
    
    # 1단계: 상위 헤더로 분할
    top_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=top_level_headers,
        strip_headers=False,
    )
    top_chunks = top_splitter.split_text(markdown)
    
    final_documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=200,
    )
    
    for chunk in top_chunks:
        section_name = chunk.metadata.get("Header 2", "Unknown")
        content = chunk.page_content
        
        # 2단계: 큰 섹션은 하위 헤더로 추가 분할
        if len(content) > max_chunk_size * 2:
            sub_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[("###", "Header 3")],
                strip_headers=False,
            )
            sub_chunks = sub_splitter.split_text(content)
            
            for sub_chunk in sub_chunks:
                if len(sub_chunk.page_content) > max_chunk_size:
                    # 3단계: 여전히 크면 크기 제한으로 분할
                    size_chunks = text_splitter.split_documents([sub_chunk])
                    for size_chunk in size_chunks:
                        size_chunk.metadata.update({
                            "section_name": section_name,
                            "sub_section": sub_chunk.metadata.get("Header 3", ""),
                        })
                    final_documents.extend(size_chunks)
                else:
                    sub_chunk.metadata.update({
                        "section_name": section_name,
                        "sub_section": sub_chunk.metadata.get("Header 3", ""),
                    })
                    final_documents.append(sub_chunk)
        elif len(content) > max_chunk_size:
            # 크기 제한으로 분할
            size_chunks = text_splitter.split_documents([chunk])
            for size_chunk in size_chunks:
                size_chunk.metadata["section_name"] = section_name
            final_documents.extend(size_chunks)
        else:
            chunk.metadata["section_name"] = section_name
            final_documents.append(chunk)
    
    return final_documents
```

---

## 4. 개선된 구현 코드

### 4.1 개선된 chunk_by_sections_markdown 함수

```python
def chunk_by_sections_markdown_improved(
    file_path: str | Path,
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
    strip_headers: bool = False,  # 헤더 유지
    max_chunk_size: Optional[int] = None,
) -> List[Document]:
    """
    개선된 Markdown 헤더 기반 chunking.
    
    Args:
        file_path: 문서 파일 경로
        headers_to_split_on: 분할할 헤더 레벨 리스트
        strip_headers: 헤더를 제거할지 여부 (기본값: False - 헤더 유지)
        max_chunk_size: 최대 청크 크기 (None이면 크기 제한 없음)
    
    Returns:
        Document 객체 리스트
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN:
        return []
    
    # 1. Docling으로 문서 변환
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    markdown = result.document.export_to_markdown()
    
    # 2. 헤더 레벨 설정
    if headers_to_split_on is None:
        headers_to_split_on = [
            ("##", "Header 2"),  # 상위 섹션만 분할
        ]
    
    # 3. MarkdownHeaderTextSplitter로 분할 (헤더 유지)
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=strip_headers,  # 헤더 유지 옵션
    )
    chunks = markdown_splitter.split_text(markdown)
    
    # 4. 크기 제한이 있으면 추가 분할
    final_documents = []
    if max_chunk_size:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=200,
        )
        
        for chunk in chunks:
            if len(chunk.page_content) > max_chunk_size:
                sub_chunks = text_splitter.split_documents([chunk])
                for sub_chunk in sub_chunks:
                    sub_chunk.metadata.update(chunk.metadata)
                final_documents.extend(sub_chunks)
            else:
                final_documents.append(chunk)
    else:
        final_documents = chunks
    
    # 5. LangChain Document로 변환
    documents = []
    for chunk in final_documents:
        # 섹션 이름 추출 (Header 2에서)
        section_name = chunk.metadata.get("Header 2", "Unknown")
        
        doc = Document(
            page_content=chunk.page_content,
            metadata={
                "source": str(file_path),
                "section_name": section_name,  # 명확한 섹션 이름
                **chunk.metadata,
            }
        )
        documents.append(doc)
    
    return documents
```

### 4.2 계층적 헤더 처리 함수

```python
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
    """
    if not HAS_DOCLING or not HAS_LANGCHAIN:
        return []
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
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
```

---

## 5. 테스트 및 검증

### 5.1 테스트 코드

```python
# 개선된 함수 테스트
documents = chunk_by_sections_markdown_improved(
    "paper.md",
    strip_headers=False,  # 헤더 유지
    max_chunk_size=2000,
)

# 결과 확인
for doc in documents:
    print(f"Section: {doc.metadata.get('section_name')}")
    print(f"Size: {len(doc.page_content)}")
    print(f"Content preview: {doc.page_content[:100]}...")
    print()
```

### 5.2 예상 개선 사항

**이전 (strip_headers=True)**:
- 섹션 이름: "Unknown"
- 헤더 정보 없음
- 섹션 구분 어려움

**개선 후 (strip_headers=False)**:
- 섹션 이름: "METHODS", "INTRODUCTION" 등
- 헤더 정보 포함
- 섹션 구분 명확

---

## 6. 권장 사항

### 6.1 즉시 적용: strip_headers=False

```python
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("##", "Header 2")],
    strip_headers=False,  # ⭐ 헤더 유지
)
```

### 6.2 장기 개선: 계층적 처리

큰 섹션(METHODS 등)을 처리하기 위해 계층적 접근 사용:

```python
documents = chunk_markdown_hierarchical(
    "paper.md",
    max_chunk_size=2000,
)
```

---

## 7. 결론

**핵심 문제**: `strip_headers=True`가 기본값이어서 헤더가 제거되고, 상위 헤더가 하위 헤더를 포함하지 못함

**해결책**:
1. ✅ `strip_headers=False`로 설정하여 헤더 유지
2. ✅ 상위 헤더만 분할하도록 헤더 레벨 조정
3. ✅ 계층적 처리로 큰 섹션 추가 분할

**권장 구현**: `chunk_markdown_hierarchical()` 함수 사용

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX






