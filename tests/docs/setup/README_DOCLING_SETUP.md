# Docling Setup 및 사용 가이드

## 📋 개요

[Docling](https://github.com/docling-project/docling)은 다양한 문서 형식을 파싱하고 Gen AI 생태계와 통합할 수 있는 강력한 문서 처리 라이브러리입니다.

### 주요 기능

- 🗂️ **다양한 문서 형식 지원**: PDF, DOCX, PPTX, XLSX, HTML, WAV, MP3, VTT, 이미지 (PNG, TIFF, JPEG 등)
- 📑 **고급 PDF 이해**: 페이지 레이아웃, 읽기 순서, 테이블 구조, 코드, 수식, 이미지 분류 등
- 🧬 **통합 문서 표현**: DoclingDocument 형식으로 통일된 문서 표현
- ↪️ **다양한 export 형식**: Markdown, HTML, DocTags, 무손실 JSON
- 🔒 **로컬 실행**: 민감한 데이터 및 air-gapped 환경 지원
- 🤖 **AI 프레임워크 통합**: LangChain, LlamaIndex, Crew AI, Haystack
- 🔍 **OCR 지원**: 스캔된 PDF 및 이미지용 광학 문자 인식
- 👓 **Visual Language Models**: GraniteDocling 등 VLM 지원
- 🎙️ **오디오 지원**: 자동 음성 인식 (ASR) 모델
- 🔌 **MCP 서버**: Agentic 애플리케이션을 위한 MCP 서버 연결
- 💻 **CLI 도구**: 간편한 명령줄 인터페이스

## 🚀 설치

### 기본 설치

```bash
# pip를 사용한 설치
pip install docling

# 또는 uv를 사용한 설치 (프로젝트에서 권장)
uv pip install docling
```

### 프로젝트 의존성에 추가

`pyproject.toml`에 다음을 추가:

```toml
dependencies = [
    # ... 기존 의존성 ...
    "docling>=2.65.0",
]
```

그 후:

```bash
uv sync
```

### 추가 기능 설치

#### Visual Language Models (VLM) 지원

GraniteDocling 등 VLM을 사용하려면:

```bash
# MLX 가속화 (Apple Silicon)
pip install docling[vlm]

# 또는 전체 기능
pip install docling[all]
```

#### OCR 지원

스캔된 PDF 및 이미지 처리를 위해:

```bash
pip install docling[ocr]
```

## 📖 기본 사용법

### Python에서 사용

#### 1. 기본 문서 변환

```python
from docling.document_converter import DocumentConverter

# URL 또는 로컬 파일 경로
source = "https://arxiv.org/pdf/2408.09869"
# 또는
# source = "/path/to/document.pdf"

converter = DocumentConverter()
result = converter.convert(source)

# Markdown으로 export
markdown_output = result.document.export_to_markdown()
print(markdown_output)

# HTML로 export
html_output = result.document.export_to_html()

# JSON으로 export
json_output = result.document.export_to_dict()
```

#### 2. 다양한 문서 형식 처리

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

# PDF
result = converter.convert("document.pdf")

# DOCX
result = converter.convert("document.docx")

# PPTX
result = converter.convert("presentation.pptx")

# XLSX
result = converter.convert("spreadsheet.xlsx")

# HTML
result = converter.convert("page.html")

# 이미지 (PNG, JPEG, TIFF 등)
result = converter.convert("image.png")
```

#### 3. 기본 사용 (설정 커스터마이징)

```python
from docling.document_converter import DocumentConverter

# DocumentConverter는 기본 생성자만 사용합니다
# (현재 버전에서는 파라미터 없이 사용)
converter = DocumentConverter()
result = converter.convert("document.pdf")

# 변환 결과에서 테이블, 이미지 등을 자동으로 추출합니다
markdown = result.document.export_to_markdown()
```

### CLI에서 사용

#### 기본 사용

```bash
# 단일 문서 변환
docling document.pdf

# 출력 파일 지정
docling document.pdf -o output.md

# Markdown 형식으로 출력
docling document.pdf --format markdown

# HTML 형식으로 출력
docling document.pdf --format html
```

#### VLM 사용 (GraniteDocling)

```bash
# GraniteDocling을 사용한 변환
docling --pipeline vlm --vlm-model granite_docling document.pdf
```

#### URL에서 변환

```bash
docling https://arxiv.org/pdf/2408.09869
```

## 🔧 고급 사용법

### 1. 테이블 구조 추출

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document_with_tables.pdf")

# 테이블 정보 접근
tables = result.document.tables
print(f"발견된 테이블 수: {len(tables)}")
for table in tables:
    if hasattr(table, 'data') and table.data:
        print(f"테이블 행 수: {table.data.num_rows}, 열 수: {table.data.num_cols}")
```

### 2. 이미지 및 수식 처리

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# 이미지 및 수식 정보 접근
pictures = result.document.pictures
print(f"발견된 이미지 수: {len(pictures)}")

# 수식은 iterate_items()를 통해 찾을 수 있습니다
formula_count = 0
for item_tuple in result.document.iterate_items():
    item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
    if type(item).__name__ == 'FormulaItem':
        formula_count += 1
print(f"발견된 수식 수: {formula_count}")
```

### 3. LangChain 통합

```python
from docling.integrations.langchain import DoclingLoader
from langchain_community.document_loaders import DoclingLoader

# LangChain DocumentLoader로 사용
loader = DoclingLoader("document.pdf")
documents = loader.load()

# 또는 직접 사용
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document

converter = DocumentConverter()
result = converter.convert("document.pdf")
markdown = result.document.export_to_markdown()

doc = Document(
    page_content=markdown,
    metadata={"source": "document.pdf"}
)
```

### 4. 배치 처리

```python
from docling.document_converter import DocumentConverter
from pathlib import Path

converter = DocumentConverter()
pdf_dir = Path("documents/")

for pdf_file in pdf_dir.glob("*.pdf"):
    print(f"Processing {pdf_file}...")
    result = converter.convert(str(pdf_file))
    
    # 출력 저장
    output_file = pdf_file.with_suffix(".md")
    output_file.write_text(result.document.export_to_markdown())
```

### 5. MCP 서버 연동

Docling은 MCP (Model Context Protocol) 서버를 제공합니다. `mcp_config.json`에 추가:

```json
{
  "servers": {
    "docling": {
      "command": "python",
      "args": ["-m", "docling.mcp"],
      "enabled": true,
      "transport": "stdio",
      "env": {}
    }
  }
}
```

## 📊 기존 PDF 파서와 비교

### Docling의 장점

1. **고급 레이아웃 이해**: 복잡한 레이아웃, 다중 컬럼, 포스터 형식 문서 처리에 우수
2. **테이블 구조 보존**: 테이블의 구조와 관계를 정확히 유지
3. **읽기 순서 인식**: 문서의 논리적 읽기 순서를 자동으로 인식
4. **이미지 및 수식 처리**: 이미지 분류 및 수식 인식 기능
5. **다양한 형식 지원**: PDF뿐만 아니라 Office 문서, HTML, 오디오 등 다양한 형식 지원
6. **AI 통합**: LangChain, LlamaIndex 등과의 네이티브 통합

### 언제 Docling을 사용해야 할까?

- ✅ 복잡한 레이아웃의 PDF 문서 (포스터, 논문, 보고서)
- ✅ 테이블이 많은 문서
- ✅ 이미지와 텍스트가 혼합된 문서
- ✅ 다양한 문서 형식을 통합 처리해야 하는 경우
- ✅ LangChain/LlamaIndex와 통합이 필요한 경우
- ✅ OCR이 필요한 스캔된 문서

### 언제 다른 파서를 사용할까?

- ✅ 단순한 텍스트 기반 PDF (PyPDFLoader로 충분)
- ✅ 빠른 처리가 필요한 경우 (Docling은 더 무겁지만 정확함)
- ✅ 최소한의 의존성만 원하는 경우

## 🧪 테스트 및 예제

프로젝트의 `tests/` 디렉토리에 다음 예제 파일들이 있습니다:

1. **test_docling_basic.py**: 기본 사용법 예제
2. **test_docling_advanced.py**: 고급 기능 예제
3. **test_docling_comparison.py**: 기존 PDF 파서와의 비교

### 예제 실행

```bash
# 기본 예제
uv run python tests/test_docling_basic.py

# 고급 예제
uv run python tests/test_docling_advanced.py

# 비교 테스트
uv run python tests/test_docling_comparison.py
```

## 🔗 참고 자료

- [Docling GitHub](https://github.com/docling-project/docling)
- [Docling 문서](https://docling-project.github.io/docling)
- [Docling Technical Report](https://arxiv.org/abs/2408.09869)
- [LangChain Docling 통합](https://python.langchain.com/docs/integrations/document_loaders/docling)

## ⚠️ 주의사항

1. **의존성**: Docling은 상대적으로 많은 의존성을 필요로 합니다. 설치 시간이 다소 걸릴 수 있습니다.

2. **처리 속도**: 고급 기능을 사용할 경우 처리 속도가 느릴 수 있습니다. 단순한 문서는 더 가벼운 파서를 고려하세요.

3. **메모리 사용**: 큰 문서를 처리할 때 메모리 사용량이 높을 수 있습니다.

4. **모델 라이선스**: 일부 VLM 모델은 별도의 라이선스가 필요할 수 있습니다.

## 🐛 문제 해결

### 설치 오류

```bash
# 의존성 문제가 있는 경우
uv pip install --upgrade docling

# 또는 특정 버전 설치
uv pip install docling==2.65.0
```

### OCR 오류

OCR 기능을 사용하려면 Tesseract가 설치되어 있어야 합니다:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki 에서 설치
```

### 메모리 부족

큰 문서를 처리할 때 메모리 부족이 발생하면:

```python
# 배치 크기 조정
converter = DocumentConverter(
    # 설정 조정
    max_workers=1  # 병렬 처리 비활성화
)
```

## 📝 업데이트 이력

- **2025-01-XX**: 초기 문서 작성
- Docling v2.65.0 기준

