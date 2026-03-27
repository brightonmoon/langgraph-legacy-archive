# 포스터 PDF 파서 비교 테스트 결과

## 📄 테스트 파일
- **파일명**: `614. Acute Lymphoblastic Leukemias Biomarkers, Molecular Markers, and Measurable Residual Disease in_MON_5144_ASH2025.pdf`
- **파일 크기**: 1.33 MB
- **형식**: 학회 포스터 (복잡한 레이아웃, 다중 컬럼, 이미지 포함)

---

## 📊 비교 결과 요약

### 기본 통계 비교

| 파서 | 시간(초) | 텍스트 길이 | 단어 수 | 문장 수 |
|------|---------|------------|---------|---------|
| **PyPDFLoader (pypdf)** | 0.251 | 9,583자 | 1,439 | 79 |
| **PyMuPDF (pymupdf)** | 0.030 | 9,517자 | 1,428 | 79 |
| **UnstructuredPDFLoader** | 0.256 | 9,401자 | 1,398 | 79 |

### 텍스트 품질 비교

| 파서 | 평균 줄 길이 | 최대 줄 길이 | 조각화 비율 |
|------|-------------|-------------|------------|
| **PyPDFLoader (pypdf)** | 30.8 | 271 | **0.7%** ✅ |
| **PyMuPDF (pymupdf)** | 27.1 | 271 | **0.6%** ✅ |
| **UnstructuredPDFLoader** | 64.1 | 9075 | **98.6%** ❌ |

---

## 🔍 주요 발견 사항

### ✅ 우수한 성능: PyPDFLoader & PyMuPDF

1. **텍스트 구조 보존**
   - 정상적인 줄바꿈과 문단 구조 유지
   - 조각화 비율이 매우 낮음 (0.6-0.7%)
   - 가독성 우수

2. **속도**
   - PyMuPDF: 0.030초 (가장 빠름)
   - PyPDFLoader: 0.251초

3. **텍스트 추출량**
   - 두 파서 모두 9,500자 이상 추출
   - 거의 동일한 양의 텍스트 추출

### ❌ 문제 발견: UnstructuredPDFLoader (pdfminer)

1. **심각한 텍스트 조각화**
   - 조각화 비율: 98.6%
   - 한 글자씩 줄바꿈되어 추출됨
   - 가독성 극히 낮음

2. **예시**:
   ```
   n
   i
   e
   s
   a
   e
   s
   D
   ```

---

## 📝 샘플 텍스트 비교

### PyPDFLoader (pypdf) ✅
```
Scan the 
QR code 
to view this 
poster on 
a mobile 
device.
ASH2025
 614. Acute Lymphoblastic Leukemias: Biomarkers, Molecular Markers, and Measurable Residual Disease in
Diagnosis and Prognosis: Poster III
Veronica Yeung
MON-5144
Two Pediatric ALL cohorts: Children's Hospital at Westmead 
(CHW); Royal Children's Hospital in Melbourne (RCH). White 
blood cells from bone marrow or peripheral blood samples 
were processed for analysis.
```

### PyMuPDF (pymupdf) ✅
```
Scan the 
QR code 
to view this 
poster on 
a mobile 
device.
ASH2025
614. Acute Lymphoblastic Leukemias: Biomarkers, Molecular Markers, and Measurable Residual Disease in
Diagnosis and Prognosis: Poster III
Veronica Yeung
MON-5144
Two Pediatric ALL cohorts: Children's Hospital at Westmead 
(CHW); Royal Children's Hospital in Melbourne (RCH). White 
blood cells from bone marrow or peripheral blood samples 
were processed for analysis.
```

### UnstructuredPDFLoader (pdfminer) ❌
```
n

i

e
s
a
e
s
D

i

l

l
...
```
(한 글자씩 조각나서 추출됨)

---

## 🎯 결론 및 권장사항

### 포스터 형식 PDF 처리

1. **최고 선택: PyMuPDF (pymupdf)**
   - ⚡ 가장 빠른 속도 (0.030초)
   - ✅ 우수한 텍스트 품질
   - ✅ 낮은 조각화 비율 (0.6%)
   - ✅ 안정적인 레이아웃 보존

2. **대안: PyPDFLoader (pypdf)**
   - ✅ 우수한 텍스트 품질
   - ✅ 낮은 조각화 비율 (0.7%)
   - ⚠️ 상대적으로 느림 (0.251초)
   - ✅ 안정적인 동작

3. **비권장: UnstructuredPDFLoader (pdfminer)**
   - ❌ 포스터 형식에서 심각한 텍스트 조각화
   - ❌ 가독성 극히 낮음
   - ❌ 후처리 필요

---

## 📋 공통 키워드 추출

모든 파서에서 발견된 공통 키워드:
- British, Proteomics, Acute, Reg, Jennifer, Wu, Centre, Control, Research, Using

---

## 💡 실용적 권장사항

### RAG 에이전트에서 사용할 경우:

1. **포스터/복잡한 레이아웃 PDF**
   - ✅ **PyMuPDF** 사용 권장 (속도 + 품질)
   - 또는 **PyPDFLoader** 사용 (안정성)

2. **일반 PDF 문서**
   - 세 파서 모두 사용 가능
   - 속도가 중요하면 PyMuPDF
   - LangChain 통합이 중요하면 PyPDFLoader

3. **UnstructuredPDFLoader**
   - 포스터 형식에서는 비권장
   - 구조화된 문서나 OCR이 필요한 경우에만 고려

---

## 🔧 테스트 실행 방법

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate

# 포스터 PDF 테스트
uv run tests/test_poster_pdf_parser.py

# 특정 포스터 파일 테스트
uv run tests/test_poster_pdf_parser.py --pdf "파일명.pdf"
```

---

**생성일**: 2025-01-27  
**테스트 환경**: WSL2, Python 3.13, LangChain Community

