# PDF 파서 비교 테스트 설정 가이드

## 📋 개요

이 가이드는 PDF 파서 비교 테스트(`test_pdf_parser_comparison.py`)를 실행하기 위해 필요한 모든 의존성을 설치하는 방법을 설명합니다.

## 🔧 필수 의존성

### 1. Python 패키지

다음 Python 패키지들이 필요합니다:

- `langchain-community` - LangChain 커뮤니티 로더
- `pypdf` - PyPDFLoader용
- `pymupdf` - PyMuPDF용
- `unstructured` - UnstructuredPDFLoader용
- `pdfminer.six` - PDF 텍스트 추출용
- `pi-heif` - 이미지 처리용
- `unstructured-inference` - 고급 PDF 파싱용
- `pdf2image` - PDF를 이미지로 변환용

**자동 설치:**
```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv sync  # pyproject.toml에 이미 포함되어 있음
```

**수동 설치:**
```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv pip install pdfminer-six pi-heif unstructured-inference pdf2image
```

### 2. 시스템 패키지

#### Poppler (UnstructuredPDFLoader 필수)

UnstructuredPDFLoader를 사용하려면 시스템 레벨에서 **Poppler**를 설치해야 합니다.

**Ubuntu/Debian/WSL:**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**설치 확인:**
```bash
which pdftoppm
# 또는
pdftoppm -h
```

## ✅ 의존성 확인

의존성 확인 스크립트를 실행하여 모든 패키지가 제대로 설치되었는지 확인할 수 있습니다:

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv run tests/scripts/check_pdf_dependencies.py
```

## 🚀 테스트 실행

의존성이 모두 설치되면 다음 명령으로 테스트를 실행할 수 있습니다:

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate

# 모든 PDF 파일 테스트 (최대 3개)
uv run tests/test_pdf_parser_comparison.py

# 특정 PDF 파일만 테스트
uv run tests/test_pdf_parser_comparison.py --pdf "파일명.pdf"

# 테스트할 파일 수 제한
uv run tests/test_pdf_parser_comparison.py --limit 5

# pytest로 실행
uv run pytest tests/test_pdf_parser_comparison.py -v
```

## 📊 비교 대상 파서

1. **PyPDFLoader (pypdf)** - 가장 기본적인 PDF 파서
2. **PyMuPDF (pymupdf)** - 빠른 성능의 PDF 파서
3. **UnstructuredPDFLoader** - 레이아웃 분석 및 OCR 지원 (Poppler 필요)

## ⚠️ 문제 해결

### Poppler 오류

**오류 메시지:**
```
Unable to get page count. Is poppler installed and in PATH?
```

**해결 방법:**
1. Poppler가 설치되어 있는지 확인:
   ```bash
   which pdftoppm
   ```

2. 설치되어 있지 않다면 설치:
   ```bash
   sudo apt-get update
   sudo apt-get install -y poppler-utils
   ```

3. PATH에 Poppler가 있는지 확인:
   ```bash
   echo $PATH | grep poppler
   ```

### 모듈을 찾을 수 없는 오류

**오류 메시지:**
```
No module named 'xxx'
```

**해결 방법:**
1. 가상환경이 활성화되어 있는지 확인
2. 필요한 패키지 설치:
   ```bash
   uv pip install <패키지명>
   ```

## 📝 참고사항

- **PyPDFLoader**와 **PyMuPDF**는 Python 패키지만 필요하며, 시스템 레벨 의존성이 없습니다.
- **UnstructuredPDFLoader**는 Poppler를 포함한 여러 시스템 의존성이 필요하며, 더 많은 기능을 제공하지만 설정이 복잡합니다.
- 테스트 결과에서 각 파서의 성능, 텍스트 추출 품질, 속도를 비교할 수 있습니다.

## 🔗 관련 문서

- [LangChain PDF Loaders 문서](https://python.langchain.com/docs/integrations/document_loaders/pdf)
- [PyMuPDF 문서](https://pymupdf.readthedocs.io/)
- [Unstructured 문서](https://unstructured.io/)

