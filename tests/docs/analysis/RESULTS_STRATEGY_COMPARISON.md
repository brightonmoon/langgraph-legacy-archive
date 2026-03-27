# UnstructuredPDFLoader 전략 비교 결과

## 📄 테스트 파일
- **파일명**: `614. Acute Lymphoblastic Leukemias Biomarkers, Molecular Markers, and Measurable Residual Disease in_MON_5144_ASH2025.pdf`
- **파일 크기**: 1.33 MB
- **형식**: 학회 포스터 (복잡한 레이아웃, 다중 컬럼)

---

## 📊 전략별 테스트 결과

### 1. ✅ 성공한 전략

#### 🥇 **1위: auto (자동 선택)**
- **처리 시간**: 19.68초
- **텍스트 길이**: 8,416자
- **조각화 비율**: **0.0%** ⭐ 최고
- **요소 수**: 57개
- **요소 타입**: NarrativeText (35개), Title (15개), UncategorizedText (7개)

**특징**:
- ✅ 완벽한 텍스트 품질 (조각화 없음)
- ✅ 구조화된 요소 분류 (제목, 본문 구분)
- ✅ 적절한 처리 시간

#### 🥈 **2위: hi_res (표 구조 인식 없음)**
- **처리 시간**: **13.09초** ⭐ 가장 빠름
- **텍스트 길이**: 8,416자
- **조각화 비율**: 18.2%
- **요소 수**: 12개
- **요소 타입**: UncategorizedText (9개), Image (1개), Table (1개)

**특징**:
- ✅ 가장 빠른 처리 속도
- ⚠️ 약간의 조각화 (18.2%)
- ✅ 표와 이미지 인식

#### 🥉 **3위: hi_res (레이아웃 인식, 최고 품질)**
- **처리 시간**: 25.78초
- **텍스트 길이**: 8,416자
- **조각화 비율**: 18.2%
- **요소 수**: 12개
- **요소 타입**: UncategorizedText (9개), Image (1개), Table (1개)

**특징**:
- ⚠️ 가장 느린 처리 속도
- ⚠️ hi_res (표 구조 인식 없음)과 동일한 결과
- ✅ 표 구조 상세 분석 (하지만 시간만 더 걸림)

### 2. ❌ 실패한 전략

- **fast (빠른 추출)**: 요소 추출 실패
- **fast (표 구조 인식 포함)**: 요소 추출 실패

포스터 형식의 복잡한 레이아웃에서는 fast 전략이 작동하지 않습니다.

---

## 📈 종합 점수 비교

| 순위 | 전략 | 종합 점수 | 텍스트 길이 | 품질 | 속도 |
|------|------|----------|------------|------|------|
| 🥇 1위 | **auto (자동 선택)** | **93.3점** | 40.0점 | 40.0점 | 13.3점 |
| 🥈 2위 | hi_res (표 구조 없음) | 92.7점 | 40.0점 | 32.7점 | 20.0점 |
| 🥉 3위 | hi_res (표 구조 포함) | 82.9점 | 40.0점 | 32.7점 | 10.2점 |

---

## 🔍 상세 분석

### 텍스트 품질

| 전략 | 조각화 비율 | 평균 줄 길이 | 최대 줄 길이 |
|------|------------|-------------|-------------|
| **auto** | **0.0%** ✅ | 146.7자 | 827자 |
| hi_res (표 구조 없음) | 18.2% | 764.2자 | 7,949자 |
| hi_res (표 구조 포함) | 18.2% | 764.2자 | 7,949자 |

### 요소 분류 품질

#### auto 전략
- ✅ **NarrativeText**: 35개 (본문 텍스트)
- ✅ **Title**: 15개 (제목)
- ✅ **UncategorizedText**: 7개

**장점**: 텍스트 구조를 잘 이해하고 제목과 본문을 구분함

#### hi_res 전략들
- ⚠️ **UncategorizedText**: 9개
- ✅ **Image**: 1개
- ✅ **Table**: 1개

**장점**: 이미지와 표를 인식
**단점**: 텍스트 구조 분석이 덜 세밀함

---

## 💡 최종 권장사항

### 🏆 **1순위: auto (자동 선택)**

```python
from unstructured.partition.pdf import partition_pdf

elements = partition_pdf(
    filename="poster.pdf",
    strategy="auto",
    infer_table_structure=False,
    extract_images_in_pdf=False,
)
```

**이유**:
- ✅ **완벽한 텍스트 품질** (조각화 0%)
- ✅ **구조화된 요소 분류** (제목, 본문 구분)
- ✅ **적절한 처리 시간** (약 20초)
- ✅ **포스터 형식에 최적화**

### ⚡ **2순위: hi_res (표 구조 인식 없음)** - 속도가 중요한 경우

```python
elements = partition_pdf(
    filename="poster.pdf",
    strategy="hi_res",
    infer_table_structure=False,  # 표 구조 인식 비활성화로 속도 향상
    extract_images_in_pdf=False,
)
```

**이유**:
- ✅ **가장 빠른 속도** (약 13초)
- ⚠️ 약간의 조각화 있음 (18.2%)
- ✅ 이미지와 표 인식

### ❌ **비권장: fast 전략**

포스터 형식의 복잡한 레이아웃에서는 작동하지 않습니다.

---

## 📝 샘플 텍스트 비교

### auto 전략 (권장) ✅
```
¢ ProCan
¢ OI M5
CHILDREN'S _— (S MEDICAL bead THE UNIVERSITY OF INSTITUTE vata SYDNEY Jean for Genes *
wl Childrea's hospital at Westmead
Hospital Melbourne
Venn diagram DEA plot Multivariate modeling combining the relapse CHW cohort-specific sub-
```

- ✅ 텍스트가 잘 분리되어 있음
- ✅ 줄바꿈이 자연스러움

### hi_res 전략
```
¢ ProCan ¢ OI M5 CHILDREN'S _— (S MEDICAL bead THE UNIVERSITY OF INSTITUTE vata SYDNEY Jea
Venn diagram DEA plot Multivariate modeling combining the relapse CHW cohort-specific sub-
```

- ⚠️ 긴 줄로 합쳐져 있음
- ⚠️ 일부 조각화 발생

---

## 🎯 사용 시나리오별 권장사항

### 시나리오 1: 품질 최우선 (RAG, 검색)
**권장**: `auto` 전략
- 완벽한 텍스트 품질
- 구조화된 요소 분류
- 제목과 본문 구분으로 검색 품질 향상

### 시나리오 2: 속도와 품질의 균형
**권장**: `hi_res` (표 구조 인식 없음)
- 빠른 처리 속도
- 적절한 품질
- 이미지와 표 인식

### 시나리오 3: 표 데이터 추출이 중요한 경우
**권장**: `hi_res` (표 구조 인식 포함)
- 표 구조 상세 분석
- 느린 속도 (약 26초)

---

## ✅ 결론

**포스터 형식 PDF를 파싱할 때는 `auto` 전략을 사용하는 것이 가장 좋습니다.**

- ✅ 완벽한 텍스트 품질 (조각화 0%)
- ✅ 구조화된 요소 분류
- ✅ 적절한 처리 시간
- ✅ 포스터 형식에 최적화

---

**테스트 날짜**: 2025-01-27  
**테스트 환경**: WSL2, Python 3.13, Tesseract OCR 4.1.1



