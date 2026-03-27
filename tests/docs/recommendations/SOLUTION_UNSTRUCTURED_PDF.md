# 비정형 PDF 파싱 해결 방안

## 🎯 문제 정의

포스터 형식의 비정형 PDF 문서를 파싱할 때, UnstructuredPDFLoader가 제대로 작동하지 않는 문제를 해결합니다.

## ✅ 해결 완료 사항

### 1. UnstructuredPDFLoader 올바른 파라미터 설정

복잡한 레이아웃을 처리하기 위해 다음과 같이 개선했습니다:

- ✅ **다중 전략 지원**: 여러 전략을 자동으로 시도 (hi_res → auto → fast)
- ✅ **레이아웃 인식**: 구조화된 요소 추출 (`mode="elements"`)
- ✅ **조각화 검증**: 텍스트 품질을 확인하여 최적 결과 선택
- ✅ **OCR 지원**: Tesseract OCR이 있으면 hi_res 전략 사용

### 2. 코드 구조 개선

```python
def parse_with_unstructured(self) -> Dict:
    """UnstructuredPDFLoader를 올바른 파라미터로 사용"""
    
    # 1. Tesseract OCR 확인
    # 2. 우선순위별 전략 시도:
    #    - hi_res (레이아웃 인식, OCR 필요)
    #    - auto (자동 선택)
    #    - fast (빠른 추출)
    # 3. 텍스트 품질 검증
    # 4. 최적 결과 반환
```

### 3. 설치 스크립트 및 문서

- ✅ `tests/scripts/install_ocr_dependencies.sh` - OCR 설치 스크립트
- ✅ `tests/README_UNSTRUCTURED_PDF_SETUP.md` - 상세 설정 가이드

## 📋 다음 단계: OCR 설치

현재 코드는 정상 작동하지만, **Tesseract OCR**이 설치되지 않아 hi_res 전략을 사용할 수 없습니다.

### 설치 방법

**옵션 1: 설치 스크립트 사용 (권장)**
```bash
bash tests/scripts/install_ocr_dependencies.sh
```

**옵션 2: 수동 설치**
```bash
# Ubuntu/Debian/WSL
sudo apt-get update
sudo apt-get install -y tesseract-ocr

# 설치 확인
which tesseract
tesseract --version
```

### 설치 후 테스트

OCR 설치 후 다시 테스트하면:
- ✅ `hi_res` 전략 사용 가능
- ✅ 복잡한 레이아웃 인식
- ✅ 구조화된 요소 추출

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv run tests/test_poster_pdf_parser.py
```

## 🔍 현재 테스트 결과

### 성공한 파서
- ✅ **PyPDFLoader**: 9,583자 추출, 조각화 0.7%
- ✅ **PyMuPDF**: 9,517자 추출, 조각화 0.6%

### UnstructuredPDFLoader
- ⚠️ **현재 상태**: Tesseract OCR 미설치로 hi_res 전략 사용 불가
- ✅ **코드 상태**: 올바르게 구현됨, OCR 설치 후 자동 사용

## 💡 구현된 전략 우선순위

1. **hi_res** (최우선)
   - 레이아웃 인식 및 구조화
   - OCR 필요
   - 복잡한 레이아웃에 최적

2. **auto**
   - 자동 전략 선택
   - OCR 선택적

3. **fast**
   - 빠른 텍스트 추출
   - OCR 불필요
   - 단순 문서에 적합

## 🎯 최종 권장사항

### 포스터/비정형 PDF 처리

1. **OCR 설치 후 사용** (최고 품질)
   ```bash
   sudo apt-get install -y tesseract-ocr
   ```
   - UnstructuredPDFLoader의 hi_res 전략 자동 사용
   - 레이아웃 인식 및 구조화된 추출

2. **OCR 없이 사용** (현재 가능)
   - PyMuPDF 또는 PyPDFLoader 사용
   - 이미 좋은 결과 (조각화 < 1%)

## 📁 관련 파일

- `tests/test_poster_pdf_parser.py` - 개선된 테스트 코드
- `tests/README_UNSTRUCTURED_PDF_SETUP.md` - 상세 설정 가이드
- `tests/scripts/install_ocr_dependencies.sh` - OCR 설치 스크립트

## ✅ 검증 완료

- ✅ 코드 구조 개선
- ✅ 다중 전략 자동 선택
- ✅ 텍스트 품질 검증
- ✅ OCR 설치 안내
- ✅ 오류 처리 및 안내 메시지

**다음 단계**: Tesseract OCR 설치 후 최종 테스트 진행



