# Chunking 전략 비교 분석 및 권장사항

## 📋 개요

본 문서는 논문 문서에 대해 3가지 맥락 기반 chunking 전략을 테스트한 결과를 비교 분석하고, 각 전략의 선택 및 통합 방안을 제시합니다.

**분석 대상 문서**: `Catalytic inhibition of KAT6KAT7 enhances the efficacy and overcomes primary and acquired resistance to Menin inhibitors in MLL leukaemia.pdf`

**테스트 전략**:
1. **hybrid**: 섹션 단위 분할 + 크기 제한 (2000자)
2. **paper_sections**: 논문 표준 섹션 인식 (ABSTRACT, INTRODUCTION, METHODS, RESULTS, DISCUSSION, References)
3. **markdown_header**: Markdown 헤더 기반 분할 (Header 2 기준)

**분석 일자**: 2025-01-XX

---

## 1. 정량적 비교 분석

### 1.1 청크 수 및 크기 비교

| 전략 | 총 청크 수 | 평균 청크 크기 | 최소 크기 | 최대 크기 | 크기 분산 |
|------|-----------|--------------|----------|----------|----------|
| **hybrid** | 74개 | 1,297자 | 297자 | 1,999자 | 낮음 (균일) |
| **markdown_header** | 45개 | 2,112자 | 127자 | 15,172자 | 높음 (불균일) |
| **paper_sections** | 6개 | 15,593자 | 1,234자 | 30,459자 | 매우 높음 |

### 1.2 섹션 인식 정확도

| 전략 | 섹션 인식 | 인식된 섹션 수 | 섹션 이름 정확도 |
|------|----------|--------------|----------------|
| **hybrid** | ❌ 실패 | 0개 | N/A |
| **markdown_header** | ⚠️ 부분적 | 0개 (Header 2만 인식) | 낮음 (섹션 이름 추출 실패) |
| **paper_sections** | ✅ 성공 | 6개 | 높음 (ABSTRACT, INTRODUCTION, METHODS, RESULTS, DISCUSSION, References) |

### 1.3 메타데이터 풍부도

| 전략 | 메타데이터 포함 | 섹션 정보 | 하위 섹션 정보 | 추가 정보 |
|------|---------------|----------|--------------|----------|
| **hybrid** | ✅ 100% | ❌ 없음 | ✅ Header 2 | ✅ is_subsection 플래그 |
| **markdown_header** | ✅ 100% | ❌ 없음 | ✅ Header 2 | ❌ 없음 |
| **paper_sections** | ✅ 100% | ✅ 명확 | ❌ 없음 | ✅ section_type |

---

## 2. 각 전략 상세 분석

### 2.1 Hybrid 전략

#### 장점 ✅
- **균일한 청크 크기**: 평균 1,297자로 임베딩 모델에 적합한 크기
- **크기 제한 준수**: 최대 1,999자로 모든 청크가 2000자 이하
- **세밀한 분할**: 74개 청크로 상세한 검색 가능
- **하위 섹션 보존**: Header 2 정보로 하위 구조 유지
- **긴 섹션 처리**: 큰 섹션(METHODS, RESULTS)을 적절히 분할

#### 단점 ❌
- **섹션 정보 부족**: "Unknown"으로 표시되어 논문 구조 파악 어려움
- **맥락 단절 가능성**: 섹션 경계에서 잘릴 수 있음
- **검색 정확도 저하 가능**: 작은 청크로 인한 컨텍스트 손실

#### 실제 결과 예시
```json
{
  "index": 5,
  "section": "Unknown",  // ❌ 섹션 정보 없음
  "size": 1080,
  "metadata": {
    "Header 2": "INTRODUCTION",
    "is_subsection": true  // ✅ 하위 섹션 정보는 있음
  }
}
```

### 2.2 Markdown Header 전략

#### 장점 ✅
- **중간 크기 청크**: 평균 2,112자로 적절한 크기
- **헤더 구조 보존**: Header 2 정보로 문서 구조 유지
- **균형잡힌 분할**: 45개 청크로 적절한 세밀도
- **구현 간단**: LangChain 표준 기능 활용

#### 단점 ❌
- **섹션 인식 실패**: "Unknown"으로 표시되어 논문 구조 파악 어려움
- **크기 불균일**: 127자 ~ 15,172자로 편차 큼
- **큰 청크 문제**: References 섹션이 15,172자로 너무 큼
- **섹션 이름 추출 실패**: Header 2는 있지만 섹션 이름으로 활용 안 됨

#### 실제 결과 예시
```json
{
  "index": 4,
  "section": "Unknown",  // ❌ 섹션 정보 없음
  "size": 1220,
  "metadata": {
    "Header 2": "ABSTRACT"  // ✅ 헤더는 있지만 활용 안 됨
  }
}
```

### 2.3 Paper Sections 전략

#### 장점 ✅
- **완벽한 섹션 인식**: 6개 주요 섹션 모두 정확히 인식
  - ABSTRACT, INTRODUCTION, METHODS, RESULTS, DISCUSSION, References
- **명확한 메타데이터**: `section_name`과 `section_type`으로 구조 명확
- **논문 구조 보존**: 논문의 논리적 구조 완벽 반영
- **검색 정확도 향상**: 섹션 단위로 검색 시 높은 정확도 기대
- **사용자 경험 우수**: "METHODS 섹션에서 찾기" 같은 직관적 검색 가능

#### 단점 ❌
- **청크 크기 과다**: 평균 15,593자로 임베딩 모델 제한 초과 가능
- **큰 섹션 문제**: METHODS(30,459자), RESULTS(23,663자), References(28,485자)가 너무 큼
- **세밀한 검색 어려움**: 6개 청크만으로는 상세 검색 제한적
- **임베딩 모델 제한**: 대부분의 임베딩 모델이 512~2048 토큰 제한

#### 실제 결과 예시
```json
{
  "index": 3,
  "section": "METHODS",  // ✅ 명확한 섹션 정보
  "size": 30459,  // ❌ 너무 큼
  "metadata": {
    "section_name": "METHODS",
    "section_type": "paper_section"  // ✅ 구조 정보 명확
  }
}
```

---

## 3. 사용 사례별 적합성 분석

### 3.1 RAG 검색 정확도 우선

**권장 전략**: **Paper Sections + 하이브리드 접근**

**이유**:
- 섹션 정보가 명확하여 검색 정확도 향상
- 하지만 큰 섹션은 추가 분할 필요

**구현 방안**:
```python
# 1단계: Paper Sections로 주요 섹션 분할
# 2단계: 큰 섹션(METHODS, RESULTS 등)은 추가로 크기 제한 분할
# 3단계: 섹션 메타데이터 유지하면서 하위 청크 생성
```

### 3.2 임베딩 모델 제한 고려

**권장 전략**: **Hybrid 전략**

**이유**:
- 모든 청크가 2000자 이하로 임베딩 모델 제한 준수
- 균일한 크기로 일관된 임베딩 품질

**단점 보완**:
- 섹션 정보를 메타데이터로 추가 필요
- Header 2 정보를 활용하여 섹션 추론

### 3.3 일반적인 문서 처리

**권장 전략**: **Markdown Header 전략**

**이유**:
- 다양한 문서 형식에 적용 가능
- 논문뿐만 아니라 보고서, 매뉴얼 등에도 사용 가능
- 구현이 간단하고 안정적

**개선 필요**:
- 섹션 이름 추출 로직 추가
- 큰 청크 자동 분할 기능 추가

---

## 4. 통합 및 병행 솔루션 제안

### 4.1 하이브리드 통합 전략 (권장 ⭐⭐⭐)

**개념**: Paper Sections의 섹션 인식 + Hybrid의 크기 제한

**구현 방식**:
1. Paper Sections로 주요 섹션 분할
2. 각 섹션이 크기 제한(예: 2000자) 초과 시 추가 분할
3. 하위 청크에도 원본 섹션 정보를 메타데이터로 유지

**장점**:
- ✅ 섹션 정보 명확
- ✅ 임베딩 모델 제한 준수
- ✅ 검색 정확도 향상
- ✅ 세밀한 검색 가능

**예상 결과**:
- 총 청크 수: 약 30-40개 (추정)
- 평균 청크 크기: 약 1,500-2,000자
- 섹션 인식: 완벽
- 크기 제한: 준수

### 4.2 다층 전략 병행 (고급)

**개념**: 여러 전략을 병행하여 다양한 검색 시나리오 지원

**구현 방식**:
1. **Level 1 (Paper Sections)**: 섹션 단위 검색용 (6개 청크)
2. **Level 2 (Hybrid)**: 상세 검색용 (74개 청크)
3. **Level 3 (Markdown Header)**: 하위 섹션 검색용 (45개 청크)

**장점**:
- ✅ 다양한 검색 시나리오 지원
- ✅ 사용자 쿼리에 따라 적절한 레벨 선택
- ✅ 검색 정확도와 세밀도 균형

**단점**:
- ❌ 저장 공간 3배 필요
- ❌ 관리 복잡도 증가

### 4.3 적응형 전략 (스마트)

**개념**: 문서 특성에 따라 자동으로 전략 선택

**구현 방식**:
1. 문서 구조 분석 (논문인지, 보고서인지 등)
2. 섹션 크기 분석 (큰 섹션이 있는지)
3. 자동으로 최적 전략 선택

**논문 문서의 경우**:
- Paper Sections + 크기 제한 하이브리드

**일반 문서의 경우**:
- Markdown Header + 크기 제한

---

## 5. 최종 권장사항

### 5.1 즉시 적용 권장: 하이브리드 통합 전략 ⭐⭐⭐

**전략**: Paper Sections 섹션 인식 + 크기 제한 추가 분할

**이유**:
1. **섹션 정보 명확**: 논문 구조를 완벽히 반영
2. **임베딩 모델 호환**: 크기 제한으로 모든 모델과 호환
3. **검색 정확도 향상**: 섹션 정보로 필터링 및 검색 개선
4. **균형잡힌 분할**: 적절한 청크 수와 크기

**구현 우선순위**: **높음 (High Priority)**

### 5.2 단기 개선: Markdown Header 개선 ⭐⭐

**개선 사항**:
1. 섹션 이름 추출 로직 추가
2. 큰 청크 자동 분할 기능
3. 섹션 메타데이터 강화

**이유**:
- 일반 문서에도 적용 가능한 범용성
- 기존 구현 기반 활용 가능

**구현 우선순위**: **중간 (Medium Priority)**

### 5.3 장기 고려: 다층 전략 병행 ⭐

**고려 사항**:
- 저장 공간 및 관리 복잡도
- 실제 검색 성능 향상 효과 측정 필요

**구현 우선순위**: **낮음 (Low Priority, 연구용)**

---

## 6. 구체적 구현 방안

### 6.1 하이브리드 통합 전략 구현

```python
def chunk_paper_with_section_awareness(
    file_path: str | Path,
    max_chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    논문 섹션 인식 + 크기 제한 하이브리드 chunking.
    """
    # 1단계: Paper Sections로 주요 섹션 분할
    section_docs = chunk_by_paper_sections(file_path)
    
    # 2단계: 큰 섹션은 추가 분할
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    final_documents = []
    for section_doc in section_docs:
        section_name = section_doc.metadata.get('section_name', 'Unknown')
        
        if len(section_doc.page_content) <= max_chunk_size:
            # 작은 섹션은 그대로 사용
            final_documents.append(section_doc)
        else:
            # 큰 섹션은 추가 분할하되 섹션 정보 유지
            sub_chunks = text_splitter.split_documents([section_doc])
            for i, sub_chunk in enumerate(sub_chunks, 1):
                sub_chunk.metadata.update({
                    'section_name': section_name,
                    'section_type': 'paper_section',
                    'is_subsection': True,
                    'subsection_index': i,
                    'total_subsections': len(sub_chunks),
                })
            final_documents.extend(sub_chunks)
    
    return final_documents
```

### 6.2 예상 결과

**입력**: 논문 문서 (93,557자)

**출력 예상**:
- 총 청크 수: 약 35-40개
- 섹션별 분포:
  - ABSTRACT: 1개 (1,234자)
  - INTRODUCTION: 2개 (평균 1,958자)
  - METHODS: 15-18개 (평균 1,700자)
  - RESULTS: 12-15개 (평균 1,600자)
  - DISCUSSION: 3개 (평균 1,933자)
  - References: 14-17개 (평균 1,700자)

**메타데이터 예시**:
```json
{
  "section_name": "METHODS",
  "section_type": "paper_section",
  "is_subsection": true,
  "subsection_index": 3,
  "total_subsections": 16
}
```

---

## 7. 성능 예측 및 검증 계획

### 7.1 예상 성능 지표

| 지표 | Hybrid | Markdown Header | Paper Sections | 하이브리드 통합 |
|------|--------|----------------|----------------|----------------|
| **검색 정확도** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **검색 세밀도** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ |
| **임베딩 호환성** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ |
| **구조 보존** | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **구현 복잡도** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

### 7.2 검증 계획

1. **정량적 검증**:
   - 청크 수, 크기 분포 측정
   - 메타데이터 완성도 확인
   - 임베딩 모델 호환성 테스트

2. **정성적 검증**:
   - 실제 검색 쿼리로 정확도 테스트
   - 섹션 필터링 기능 테스트
   - 사용자 피드백 수집

3. **성능 비교**:
   - 각 전략별 검색 정확도 측정
   - 응답 시간 비교
   - 저장 공간 사용량 비교

---

## 8. 결론 및 실행 계획

### 8.1 최종 결론

**즉시 적용 권장 전략**: **하이브리드 통합 전략 (Paper Sections + 크기 제한)**

**핵심 이유**:
1. ✅ 논문 구조를 완벽히 반영하는 섹션 인식
2. ✅ 임베딩 모델 제한을 준수하는 크기 관리
3. ✅ 검색 정확도와 세밀도의 균형
4. ✅ 구현 복잡도가 적절함

### 8.2 실행 계획

#### Phase 1: 하이브리드 통합 전략 구현 (1-2주)
- [ ] `chunk_paper_with_section_awareness()` 함수 구현
- [ ] 테스트 및 검증
- [ ] VectorStoreManager에 통합

#### Phase 2: Markdown Header 개선 (2-3주)
- [ ] 섹션 이름 추출 로직 추가
- [ ] 큰 청크 자동 분할 기능
- [ ] 일반 문서 지원 강화

#### Phase 3: 성능 검증 및 최적화 (1-2주)
- [ ] 실제 검색 성능 측정
- [ ] 사용자 피드백 수집
- [ ] 최종 최적화

### 8.3 보류 사항

- **다층 전략 병행**: 저장 공간 및 관리 복잡도 고려하여 보류
- **적응형 전략**: 문서 분석 로직의 정확도 검증 후 고려

---

## 9. 부록: 상세 통계

### 9.1 Hybrid 전략 상세

- **총 청크 수**: 74개
- **평균 크기**: 1,297자
- **크기 범위**: 297자 ~ 1,999자
- **섹션 인식**: 실패 (모두 "Unknown")
- **메타데이터**: Header 2 정보 포함

### 9.2 Markdown Header 전략 상세

- **총 청크 수**: 45개
- **평균 크기**: 2,112자
- **크기 범위**: 127자 ~ 15,172자
- **섹션 인식**: 실패 (모두 "Unknown")
- **메타데이터**: Header 2 정보 포함

### 9.3 Paper Sections 전략 상세

- **총 청크 수**: 6개
- **평균 크기**: 15,593자
- **크기 범위**: 1,234자 ~ 30,459자
- **섹션 인식**: 성공 (6개 섹션 모두 인식)
- **메타데이터**: section_name, section_type 포함

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX  
**작성자**: agentic_ai 프로젝트 팀






