# 비정형 PDF 파싱 설정 가이드 (UnstructuredPDFLoader)

## 📋 개요

이 가이드는 **비정형 PDF 문서**(포스터, 복잡한 레이아웃, 다중 컬럼 등)를 효과적으로 파싱하기 위한 설정 방법을 설명합니다.

## 🎯 UnstructuredPDFLoader의 강점

UnstructuredPDFLoader는 복잡한 레이아웃을 가진 PDF 문서를 구조화된 요소로 추출하는 데 특화되어 있습니다:

- ✅ **레이아웃 인식**: 문서의 구조를 이해하고 요소 단위로 추출
- ✅ **복잡한 레이아웃 처리**: 다중 컬럼, 포스터, 표 등을 효과적으로 처리
- ✅ **구조화된 추출**: 텍스트, 제목, 표, 이미지 등을 구분하여 추출
- ✅ **OCR 지원**: 이미지로 된 텍스트도 인식 가능

## 🔧 필수 의존성 설치

### 1. Python 패키지

다음 패키지들이 이미 `pyproject.toml`에 포함되어 있습니다:

- `unstructured>=0.18.21`
- `unstructured-inference>=1.1.2`
- `unstructured-pytesseract>=0.3.15`
- `pytesseract` (추가 설치됨)
- `pdf2image>=1.17.0`
- `pi-heif>=1.1.1`
- `pdfminer-six>=20221105`

**확인 및 설치:**
```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv sync  # 모든 패키지 설치
```

### 2. 시스템 패키지

#### 2.1 Poppler (필수)

PDF를 이미지로 변환하기 위해 필요합니다.

**Ubuntu/Debian/WSL:**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

**설치 확인:**
```bash
which pdftoppm
pdftoppm -h
```

#### 2.2 Tesseract OCR (선택사항, 권장)

복잡한 레이아웃 인식(`hi_res` 전략)을 사용하려면 필요합니다.

**Ubuntu/Debian/WSL:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr

# 한국어 지원 (선택사항)
sudo apt-get install -y tesseract-ocr-kor
```

**또는 설치 스크립트 사용:**
```bash
bash tests/scripts/install_ocr_dependencies.sh
```

**설치 확인:**
```bash
which tesseract
tesseract --version
```

## 🚀 사용 방법

### 기본 사용

```python
from langchain_community.document_loaders import UnstructuredPDFLoader

loader = UnstructuredPDFLoader(
    "path/to/poster.pdf",
    mode="elements",  # 요소 단위로 추출
)

documents = loader.load()
```

### 복잡한 레이아웃 처리

```python
from unstructured.partition.pdf import partition_pdf
from langchain_core.documents import Document

# hi_res 전략으로 레이아웃 인식
elements = partition_pdf(
    filename="path/to/poster.pdf",
    strategy="hi_res",  # 고해상도 레이아웃 인식
    infer_table_structure=True,  # 표 구조 인식
)

# LangChain Document로 변환
documents = []
for element in elements:
    documents.append(
        Document(
            page_content=element.text,
            metadata={
                "element_type": element.category,
                "page": element.metadata.page_number,
            }
        )
    )
```

## 📊 전략 비교

| 전략 | 설명 | OCR 필요 | 속도 | 복잡한 레이아웃 |
|------|------|----------|------|----------------|
| **hi_res** | 레이아웃 인식 및 구조화 | ✅ 필요 | 느림 | ✅ 최고 |
| **auto** | 자동 전략 선택 | 선택적 | 중간 | ✅ 좋음 |
| **fast** | 빠른 텍스트 추출 | ❌ 불필요 | 빠름 | ⚠️ 제한적 |

## 🎯 포스터 PDF 파싱 테스트

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate

# 포스터 PDF 테스트 실행
uv run tests/test_poster_pdf_parser.py
```

테스트는 자동으로 여러 전략을 시도하고 최적의 결과를 선택합니다.

## ⚙️ 파라미터 설정 가이드

### mode 옵션

- **`"single"`**: 페이지 단위로 추출 (간단한 문서)
- **`"elements"`**: 요소 단위로 추출 (복잡한 레이아웃) ⭐ **권장**

### strategy 옵션

- **`"hi_res"`**: 레이아웃 인식 및 구조화 (복잡한 레이아웃) ⭐ **최고**
- **`"auto"`**: 자동 선택
- **`"fast"`**: 빠른 추출 (단순 문서)

### 추가 파라미터

```python
partition_pdf(
    filename="poster.pdf",
    strategy="hi_res",
    infer_table_structure=True,  # 표 구조 인식
    extract_images_in_pdf=False,  # 이미지 추출 비활성화 (빠름)
    ocr_languages=['eng'],  # OCR 언어 설정
)
```

## 🔍 문제 해결

### 1. OCR 오류

**오류 메시지:**
```
Could not get the OCRAgent instance
```

**해결 방법:**
```bash
# Tesseract OCR 설치
sudo apt-get install -y tesseract-ocr

# 또는 OCR 없이 사용 (fast 전략)
strategy="fast"
```

### 2. Poppler 오류

**오류 메시지:**
```
Unable to get page count. Is poppler installed?
```

**해결 방법:**
```bash
sudo apt-get install -y poppler-utils
```

### 3. 텍스트 조각화 문제

**증상**: 텍스트가 한 글자씩 줄바꿈되어 추출됨

**해결 방법:**
- `strategy="hi_res"` 사용 (레이아웃 인식)
- `mode="elements"` 사용 (구조화된 추출)
- Tesseract OCR 설치 확인

## 📝 권장 설정

### 포스터/복잡한 레이아웃 PDF

```python
# 최고 품질 (OCR 필요)
elements = partition_pdf(
    filename="poster.pdf",
    strategy="hi_res",
    infer_table_structure=True,
)

# 빠른 처리 (OCR 없이)
elements = partition_pdf(
    filename="poster.pdf",
    strategy="auto",
    mode="elements",
)
```

### 일반 PDF 문서

```python
loader = UnstructuredPDFLoader(
    "document.pdf",
    mode="single",
)
```

## 📚 참고 자료

- [Unstructured 문서](https://unstructured.io/)
- [LangChain PDF Loaders](https://python.langchain.com/docs/integrations/document_loaders/pdf)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

## 🔗 관련 파일

- `tests/test_poster_pdf_parser.py` - 포스터 PDF 테스트 스크립트
- `tests/scripts/install_ocr_dependencies.sh` - OCR 설치 스크립트
- `tests/scripts/check_pdf_dependencies.py` - 의존성 확인 스크립트



