# 포스터 PDF를 Markdown으로 변환

## 📋 개요

포스터 형식의 비정형 PDF를 구조화된 Markdown 문서로 변환하는 도구입니다.

## 🚀 사용 방법

### 기본 사용

```bash
source /home/doyamoon/agentic_ai/.venv/bin/activate
uv run tests/scripts/poster_to_markdown.py
```

### 특정 PDF 파일 지정

```bash
uv run tests/scripts/poster_to_markdown.py --pdf "your_poster.pdf"
```

### 출력 파일 지정

```bash
uv run tests/scripts/poster_to_markdown.py --output "output.md"
```

### 비교 분석 건너뛰기

```bash
uv run tests/scripts/poster_to_markdown.py --no-compare
```

## 📄 생성된 파일

- **출력 위치**: `data/poster_markdown/{pdf_filename}.md`
- **포함 내용**:
  - PDF 메타데이터 (생성일, 원본 파일)
  - 구조화된 본문 (제목, 본문 텍스트)
  - 추출 통계

## 🔍 기능

1. **PDF 파싱**: `auto` 전략을 사용하여 최고 품질로 파싱
2. **Markdown 변환**: 요소 타입에 따라 적절한 Markdown 형식으로 변환
   - Title → `## 제목`
   - NarrativeText → 일반 텍스트
   - Table → 코드 블록
   - Image → 이미지 참조
3. **비교 분석**: PDF 원본과 변환된 Markdown의 통계 비교

## 📊 출력 예시

```
📄 PDF 파싱 중: poster.pdf
   전략: auto
✅ 파싱 완료 (20.00초)
   추출된 요소 수: 57개

💾 Markdown 파일 저장: data/poster_markdown/poster.md
   파일 크기: 8.82 KB

🔍 PDF 원본과 Markdown 비교
   - 단어 수 비교
   - 텍스트 유사도
   - 주요 섹션 비교
```

## ✅ 완료된 작업

- ✅ 포스터 PDF 파싱 (auto 전략)
- ✅ Markdown 형식 변환
- ✅ 비교 분석 기능
- ✅ 통계 정보 포함

## 📝 참고

- 최적 전략: `auto` (조각화 0%, 완벽한 텍스트 품질)
- 처리 시간: 약 20초 (1.33MB PDF 기준)
- 생성 위치: `data/poster_markdown/` 디렉토리



