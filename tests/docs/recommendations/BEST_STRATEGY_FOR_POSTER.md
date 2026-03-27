# 포스터 PDF 파싱 최적 전략

## 🏆 최종 권장 설정

### ✅ **1순위: `auto` 전략 (권장)**

```python
from unstructured.partition.pdf import partition_pdf
from langchain_core.documents import Document

elements = partition_pdf(
    filename="poster.pdf",
    strategy="auto",
    infer_table_structure=False,
    extract_images_in_pdf=False,
)

# LangChain Document로 변환
documents = []
for element in elements:
    documents.append(
        Document(
            page_content=element.text,
            metadata={
                "source": "poster.pdf",
                "element_type": element.category,  # Title, NarrativeText 등
            }
        )
    )
```

**성능**:
- ✅ 조각화 비율: **0.0%** (완벽!)
- ✅ 처리 시간: 19.68초
- ✅ 텍스트 길이: 8,416자
- ✅ 요소 수: 57개 (구조화된 분류)

**특징**:
- 제목(Title)과 본문(NarrativeText)을 자동으로 구분
- 텍스트 품질이 매우 우수함
- 포스터 형식에 최적화

---

### ⚡ **2순위: `hi_res` 전략 (속도 중시)**

```python
elements = partition_pdf(
    filename="poster.pdf",
    strategy="hi_res",
    infer_table_structure=False,  # 표 구조 인식 비활성화로 속도 향상
    extract_images_in_pdf=False,
)
```

**성능**:
- ⚠️ 조각화 비율: 18.2%
- ✅ 처리 시간: **13.09초** (가장 빠름)
- ✅ 텍스트 길이: 8,416자
- ✅ 표와 이미지 인식

**특징**:
- 속도가 가장 빠름
- 표와 이미지를 인식함
- 약간의 조각화가 있음

---

## 📊 테스트 결과 요약

| 전략 | 조각화 | 속도 | 품질 | 권장도 |
|------|--------|------|------|--------|
| **auto** | **0.0%** ✅ | 19.68초 | ⭐⭐⭐⭐⭐ | ✅ **최고** |
| hi_res (표 없음) | 18.2% | **13.09초** ⚡ | ⭐⭐⭐⭐ | ⚡ 속도 중시 |
| hi_res (표 포함) | 18.2% | 25.78초 | ⭐⭐⭐⭐ | ⏱️ 표 추출 필요시 |
| fast | 실패 | - | - | ❌ 비권장 |

---

## 💡 사용 예시

### 예시 1: RAG 시스템용 (품질 최우선)

```python
from unstructured.partition.pdf import partition_pdf
from langchain_core.documents import Document

def parse_poster_pdf(pdf_path: str) -> list[Document]:
    """포스터 PDF를 파싱하여 LangChain Document로 변환"""
    elements = partition_pdf(
        filename=pdf_path,
        strategy="auto",  # 최고 품질
        infer_table_structure=False,
        extract_images_in_pdf=False,
    )
    
    documents = []
    for element in elements:
        if hasattr(element, 'text') and element.text:
            documents.append(
                Document(
                    page_content=element.text,
                    metadata={
                        "source": pdf_path,
                        "element_type": getattr(element, 'category', 'Unknown'),
                        "page": getattr(element.metadata, 'page_number', None) if hasattr(element, 'metadata') else None,
                    }
                )
            )
    
    return documents
```

### 예시 2: 빠른 처리 필요시

```python
elements = partition_pdf(
    filename=pdf_path,
    strategy="hi_res",
    infer_table_structure=False,  # 속도 향상
    extract_images_in_pdf=False,
)
```

---

## 🔍 요소 분류 비교

### auto 전략 (권장)
- **Title**: 15개 (제목)
- **NarrativeText**: 35개 (본문)
- **UncategorizedText**: 7개

**장점**: 구조를 잘 이해하고 제목과 본문을 구분함

### hi_res 전략
- **UncategorizedText**: 9개
- **Image**: 1개
- **Table**: 1개

**장점**: 이미지와 표를 인식

---

## ✅ 결론

**포스터 형식 PDF 파싱에는 `auto` 전략을 사용하세요!**

1. ✅ **완벽한 텍스트 품질** (조각화 0%)
2. ✅ **구조화된 요소 분류** (제목/본문 구분)
3. ✅ **적절한 처리 시간**
4. ✅ **포스터 형식에 최적화**

---

**테스트 완료**: 2025-01-27  
**최적 전략**: `auto`  
**테스트 파일**: `test_unstructured_strategies.py`



