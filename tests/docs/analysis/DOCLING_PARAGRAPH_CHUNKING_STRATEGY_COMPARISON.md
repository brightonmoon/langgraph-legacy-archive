# Docling 단락별 Chunking 전략 비교 분석

## 📋 개요

본 문서는 test_output의 JSON 결과를 분석하여, Docling을 사용한 **단락별 chunking 전략**을 비교하고 최적의 접근 방식을 제시합니다.

**분석 대상 문서**: `Catalytic inhibition of KAT6KAT7 enhances the efficacy and overcomes primary and acquired resistance to Menin inhibitors in MLL leukaemia.pdf`

**분석 일자**: 2025-01-XX

---

## 1. 테스트 결과 요약

### 1.1 전략별 정량적 비교

| 전략 | 총 청크 수 | 평균 청크 크기 | 최소 크기 | 최대 크기 | 섹션 인식 | 단락 보존 |
|------|-----------|--------------|----------|----------|----------|----------|
| **paper_sections** | 6개 | 15,593자 | 1,234자 | 30,459자 | ✅ 완벽 | ❌ 없음 |
| **section_aware** | 65개 | 1,468자 | 1,097자 | 1,973자 | ✅ 완벽 | ⚠️ 부분적 |
| **hybrid** | 78개 | 1,260자 | 297자 | 1,999자 | ❌ 실패 | ⚠️ 부분적 |
| **hierarchical_markdown** | 78개 | 1,254자 | 297자 | 1,997자 | ⚠️ 부분적 | ⚠️ 부분적 |
| **markdown_header** | 48개 | 2,027자 | 127자 | 15,172자 | ⚠️ 부분적 | ⚠️ 부분적 |

### 1.2 전략별 특징 분석

#### paper_sections
- **청크 수**: 6개 (가장 적음)
- **평균 크기**: 15,593자 (가장 큼)
- **섹션 인식**: ✅ ABSTRACT, INTRODUCTION, METHODS, RESULTS, DISCUSSION, References
- **단락 보존**: ❌ 없음 (섹션 단위만)
- **문제점**: 임베딩 모델 제한 초과 가능성 높음

#### section_aware (권장 ⭐⭐⭐)
- **청크 수**: 65개 (적절)
- **평균 크기**: 1,468자 (임베딩 모델에 적합)
- **섹션 인식**: ✅ 완벽 (6개 주요 섹션)
- **단락 보존**: ⚠️ 부분적 (크기 제한으로 분할 시 단락 경계 무시 가능)
- **장점**: 섹션 정보 + 적절한 크기

#### hybrid
- **청크 수**: 78개 (많음)
- **평균 크기**: 1,260자 (적절)
- **섹션 인식**: ❌ 실패 (섹션 이름 추출 실패)
- **단락 보존**: ⚠️ 부분적
- **문제점**: 섹션 정보 부족

#### hierarchical_markdown
- **청크 수**: 78개
- **평균 크기**: 1,254자
- **섹션 인식**: ⚠️ 부분적 (하위 헤더까지 포함)
- **단락 보존**: ⚠️ 부분적
- **특징**: 계층적 구조 활용

#### markdown_header
- **청크 수**: 48개
- **평균 크기**: 2,027자
- **섹션 인식**: ⚠️ 부분적
- **단락 보존**: ⚠️ 부분적
- **문제점**: 크기 불균일 (127자 ~ 15,172자)

---

## 2. 단락별 Chunking의 필요성

### 2.1 현재 전략의 한계

현재 테스트된 전략들은 다음과 같은 한계가 있습니다:

1. **섹션 단위만 고려**: 단락(paragraph) 단위는 고려하지 않음
2. **크기 제한 시 단락 경계 무시**: RecursiveCharacterTextSplitter가 단락 중간에서 분할 가능
3. **의미 단위 손실**: 문단이 여러 청크로 나뉘어 의미 손실 가능

### 2.2 단락별 Chunking의 장점

- ✅ **의미 단위 보존**: 각 단락은 하나의 완전한 의미 단위
- ✅ **자연스러운 분할**: 문서의 자연스러운 구조 활용
- ✅ **컨텍스트 유지**: 단락 내 모든 문장이 함께 유지
- ✅ **검색 정확도 향상**: 완전한 의미 단위로 검색

---

## 3. Docling을 활용한 단락별 Chunking 전략

### 3.1 Docling의 구조 정보 활용

Docling은 `iterate_items()`를 통해 문서의 구조 요소를 순회할 수 있습니다:

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 문서 구조 요소 순회
for item_tuple in result.document.iterate_items():
    item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
    depth = item_tuple[1] if isinstance(item_tuple, tuple) else 0
    item_type = type(item).__name__
    
    # ParagraphItem, TextItem 등을 확인
    if item_type == "ParagraphItem":
        # 단락 처리
        pass
```

### 3.2 전략 1: Docling Item 기반 단락 Chunking (권장 ⭐⭐⭐)

**개념**: Docling의 구조 요소를 직접 활용하여 단락 단위로 chunking

**장점**:
- ✅ Docling이 인식한 단락 구조 활용
- ✅ 문서의 자연스러운 구조 보존
- ✅ 테이블, 수식 등 구조 요소 자동 처리

**구현**:

```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from typing import List, Optional

def chunk_by_paragraphs_docling(
    file_path: str | Path,
    min_paragraph_size: int = 50,
    max_chunk_size: int = 2000,
    merge_small_paragraphs: bool = True,
) -> List[Document]:
    """
    Docling의 구조 정보를 활용하여 단락 단위로 chunking.
    
    Args:
        file_path: 문서 파일 경로
        min_paragraph_size: 최소 단락 크기 (이보다 작으면 병합)
        max_chunk_size: 최대 청크 크기 (초과 시 여러 단락 병합)
        merge_small_paragraphs: 작은 단락 병합 여부
    
    Returns:
        Document 객체 리스트
    """
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    
    paragraphs = []
    current_paragraph = []
    current_section = None
    
    # Docling 구조 요소 순회
    for item_tuple in result.document.iterate_items():
        item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
        depth = item_tuple[1] if isinstance(item_tuple, tuple) else 0
        item_type = type(item).__name__
        
        # 섹션 헤더 감지
        if item_type in ["TitleItem", "SectionItem"]:
            if hasattr(item, 'text') and item.text:
                current_section = item.text.strip()
        
        # 단락 추출
        if item_type == "ParagraphItem":
            if hasattr(item, 'text') and item.text:
                para_text = item.text.strip()
                if para_text:
                    paragraphs.append({
                        'text': para_text,
                        'section': current_section,
                        'size': len(para_text),
                    })
        elif item_type == "TextItem":
            # TextItem도 단락으로 간주
            if hasattr(item, 'text') and item.text:
                para_text = item.text.strip()
                if para_text and len(para_text) > min_paragraph_size:
                    paragraphs.append({
                        'text': para_text,
                        'section': current_section,
                        'size': len(para_text),
                    })
    
    # 단락 병합 및 청크 생성
    documents = []
    current_chunk = []
    current_chunk_size = 0
    current_chunk_section = None
    
    for para in paragraphs:
        para_text = para['text']
        para_size = para['size']
        para_section = para['section']
        
        # 섹션이 변경되면 현재 청크 저장
        if current_chunk_section and para_section and current_chunk_section != para_section:
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                documents.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "source": str(file_path),
                        "section_name": current_chunk_section,
                        "chunk_type": "paragraph_based",
                        "paragraph_count": len(current_chunk),
                    }
                ))
                current_chunk = []
                current_chunk_size = 0
        
        # 크기 제한 확인
        if current_chunk_size + para_size > max_chunk_size and current_chunk:
            # 현재 청크 저장
            chunk_text = '\n\n'.join(current_chunk)
            documents.append(Document(
                page_content=chunk_text,
                metadata={
                    "source": str(file_path),
                    "section_name": current_chunk_section or "Unknown",
                    "chunk_type": "paragraph_based",
                    "paragraph_count": len(current_chunk),
                }
            ))
            current_chunk = []
            current_chunk_size = 0
        
        # 단락 추가
        if merge_small_paragraphs and para_size < min_paragraph_size:
            # 작은 단락은 다음 단락과 병합
            current_chunk.append(para_text)
            current_chunk_size += para_size
        else:
            # 큰 단락은 별도 청크로
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                documents.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "source": str(file_path),
                        "section_name": current_chunk_section or "Unknown",
                        "chunk_type": "paragraph_based",
                        "paragraph_count": len(current_chunk),
                    }
                ))
                current_chunk = []
                current_chunk_size = 0
            
            # 단일 단락 청크
            documents.append(Document(
                page_content=para_text,
                metadata={
                    "source": str(file_path),
                    "section_name": para_section or "Unknown",
                    "chunk_type": "single_paragraph",
                }
            ))
            current_chunk_section = para_section
    
    # 마지막 청크 저장
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        documents.append(Document(
            page_content=chunk_text,
            metadata={
                "source": str(file_path),
                "section_name": current_chunk_section or "Unknown",
                "chunk_type": "paragraph_based",
                "paragraph_count": len(current_chunk),
            }
        ))
    
    return documents
```

### 3.3 전략 2: Markdown 단락 기반 Chunking

**개념**: Docling이 생성한 Markdown에서 단락(`\n\n`)을 기준으로 분할

**장점**:
- ✅ 구현 간단
- ✅ Markdown 구조 활용
- ✅ LangChain과 호환

**구현**:

```python
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_by_paragraphs_markdown(
    file_path: str | Path,
    max_chunk_size: int = 2000,
    chunk_overlap: int = 200,
    respect_paragraph_boundaries: bool = True,
) -> List[Document]:
    """
    Markdown에서 단락 단위로 chunking.
    
    Args:
        file_path: 문서 파일 경로
        max_chunk_size: 최대 청크 크기
        chunk_overlap: 청크 간 겹침
        respect_paragraph_boundaries: 단락 경계 존중 여부
    """
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    markdown = result.document.export_to_markdown()
    
    if respect_paragraph_boundaries:
        # 단락 단위로 먼저 분할
        paragraphs = markdown.split('\n\n')
        
        # 단락 병합
        documents = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # 크기 제한 확인
            if current_size + para_size > max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = '\n\n'.join(current_chunk)
                documents.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "source": str(file_path),
                        "chunk_type": "paragraph_based",
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
            documents.append(Document(
                page_content=chunk_text,
                metadata={
                    "source": str(file_path),
                    "chunk_type": "paragraph_based",
                    "paragraph_count": len(current_chunk),
                }
            ))
        
        return documents
    else:
        # 기본 크기 기반 분할
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],  # 단락 우선
        )
        doc = Document(
            page_content=markdown,
            metadata={"source": str(file_path)}
        )
        return splitter.split_documents([doc])
```

### 3.4 전략 3: 하이브리드 접근 (섹션 + 단락)

**개념**: 섹션 인식 + 단락 단위 분할

**장점**:
- ✅ 섹션 정보 보존
- ✅ 단락 경계 존중
- ✅ 적절한 크기 관리

**구현**:

```python
def chunk_by_section_and_paragraphs(
    file_path: str | Path,
    max_chunk_size: int = 2000,
) -> List[Document]:
    """
    섹션 인식 + 단락 단위 chunking.
    """
    # 1단계: 섹션 분할
    section_docs = chunk_by_paper_sections(file_path)
    
    # 2단계: 각 섹션을 단락 단위로 분할
    final_documents = []
    
    for section_doc in section_docs:
        section_name = section_doc.metadata.get('section_name', 'Unknown')
        content = section_doc.page_content
        
        # 단락 단위로 분할
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = '\n\n'.join(current_chunk)
                final_documents.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "source": str(file_path),
                        "section_name": section_name,
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
                    "chunk_type": "section_paragraph",
                    "paragraph_count": len(current_chunk),
                }
            ))
    
    return final_documents
```

---

## 4. 전략 비교 및 권장사항

### 4.1 전략 비교표

| 전략 | 구현 난이도 | 단락 보존 | 섹션 정보 | 크기 관리 | Docling 활용 | 권장도 |
|------|------------|----------|----------|----------|-------------|--------|
| **Docling Item 기반** | ⭐⭐⭐ 어려움 | ⭐⭐⭐ 완벽 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ 최대 | ⭐⭐⭐ |
| **Markdown 단락 기반** | ⭐⭐ 보통 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ |
| **하이브리드 (섹션+단락)** | ⭐⭐ 보통 | ⭐⭐⭐ 우수 | ⭐⭐⭐ 완벽 | ⭐⭐⭐ 우수 | ⭐⭐ 보통 | ⭐⭐⭐ |

### 4.2 예상 결과 비교

#### Docling Item 기반 단락 Chunking
- **예상 청크 수**: 약 100-150개
- **평균 크기**: 약 600-800자
- **단락 보존**: ✅ 완벽
- **섹션 정보**: ✅ 포함
- **장점**: 가장 자연스러운 분할

#### Markdown 단락 기반
- **예상 청크 수**: 약 80-120개
- **평균 크기**: 약 800-1,200자
- **단락 보존**: ✅ 우수
- **섹션 정보**: ⚠️ 부분적
- **장점**: 구현 간단, 안정적

#### 하이브리드 (섹션+단락)
- **예상 청크 수**: 약 70-90개
- **평균 크기**: 약 1,000-1,500자
- **단락 보존**: ✅ 우수
- **섹션 정보**: ✅ 완벽
- **장점**: 섹션 정보 + 단락 보존

---

## 5. 최종 권장사항

### 5.1 즉시 적용 권장: 하이브리드 접근 (섹션+단락) ⭐⭐⭐

**이유**:
1. ✅ 섹션 정보 완벽 보존 (section_aware의 장점)
2. ✅ 단락 경계 존중 (의미 단위 보존)
3. ✅ 적절한 크기 관리 (임베딩 모델 호환)
4. ✅ 구현 복잡도 적절

**구현 우선순위**: **높음 (High Priority)**

### 5.2 장기 개선: Docling Item 기반 단락 Chunking ⭐⭐

**이유**:
- Docling의 구조 정보를 최대한 활용
- 가장 자연스러운 문서 구조 반영

**구현 우선순위**: **중간 (Medium Priority)**

### 5.3 대안: Markdown 단락 기반 ⭐

**이유**:
- 구현 간단
- 안정적

**구현 우선순위**: **낮음 (Low Priority)**

---

## 6. 구현 예시

### 6.1 하이브리드 접근 구현

```python
# tests/test_contextual_chunking.py에 추가

def chunk_by_section_and_paragraphs(
    file_path: str | Path,
    max_chunk_size: int = 2000,
) -> List[Document]:
    """
    섹션 인식 + 단락 단위 chunking (권장).
    """
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
```

---

## 7. 예상 성능 비교

### 7.1 현재 전략 vs 단락 기반 전략

| 지표 | section_aware | 하이브리드 (섹션+단락) | 개선 효과 |
|------|--------------|---------------------|----------|
| **청크 수** | 65개 | 70-90개 | +8-38% |
| **평균 크기** | 1,468자 | 1,000-1,500자 | 유사 |
| **단락 보존** | ⚠️ 부분적 | ✅ 완벽 | ⬆️ 향상 |
| **의미 단위** | ⚠️ 부분적 | ✅ 완벽 | ⬆️ 향상 |
| **검색 정확도** | ⭐⭐ | ⭐⭐⭐ | ⬆️ 향상 예상 |

---

## 8. 결론

### 8.1 핵심 요약

1. **현재 전략의 한계**: 단락 경계를 존중하지 않아 의미 단위 손실 가능
2. **단락별 Chunking의 필요성**: 자연스러운 문서 구조 활용으로 검색 정확도 향상
3. **권장 전략**: 하이브리드 접근 (섹션 인식 + 단락 단위 분할)

### 8.2 실행 계획

#### Phase 1: 하이브리드 접근 구현 (1주)
- [ ] `chunk_by_section_and_paragraphs()` 함수 구현
- [ ] 테스트 및 검증
- [ ] 기존 전략과 성능 비교

#### Phase 2: Docling Item 기반 구현 (2주)
- [ ] `chunk_by_paragraphs_docling()` 함수 구현
- [ ] Docling 구조 요소 분석
- [ ] 성능 최적화

#### Phase 3: 통합 및 최적화 (1주)
- [ ] VectorStoreManager에 통합
- [ ] 실제 검색 성능 측정
- [ ] 최종 최적화

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX  
**작성자**: agentic_ai 프로젝트 팀






