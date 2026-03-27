"""
포스터 PDF를 Markdown으로 변환하는 스크립트

포스터 PDF를 읽어서 구조화된 Markdown 문서로 변환하고,
원본 PDF 내용과 비교합니다.

사용법:
    source /home/doyamoon/agentic_ai/.venv/bin/activate
    uv run tests/scripts/poster_to_markdown.py
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    from unstructured.partition.pdf import partition_pdf
    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False
    print("❌ unstructured 모듈을 사용할 수 없습니다.")
    sys.exit(1)

from src.utils.paths import get_data_directory, get_project_root


def element_to_markdown(element, title_level: int = 2) -> str:
    """Unstructured 요소를 Markdown 형식으로 변환"""
    if not hasattr(element, 'text') or not element.text:
        return ""
    
    text = element.text.strip()
    if not text:
        return ""
    
    # 요소 타입에 따라 Markdown 형식 적용
    element_type = getattr(element, 'category', 'Unknown')
    
    if element_type == 'Title':
        # 제목 처리
        first_line = text.split('\n')[0] if '\n' in text else text
        
        # 매우 짧은 텍스트는 헤더로 변환하지 않음
        if len(text) < 5:
            return f"{text}\n\n"
        
        # 긴 제목은 단락으로 처리
        if len(text) > 150:
            return f"{text}\n\n"
        
        # 일반 제목은 ## (h2)로
        return f"## {text}\n\n"
    
    elif element_type == 'NarrativeText':
        # 본문 텍스트 - 단락으로 처리
        return f"{text}\n\n"
    
    elif element_type == 'Table':
        # 표는 코드 블록으로
        return f"```\n{text}\n```\n\n"
    
    elif element_type == 'Image':
        # 이미지 참조
        return f"![Image](image)\n\n"
    
    elif element_type == 'ListItem':
        # 리스트 항목
        return f"- {text}\n"
    
    else:
        # 기타 (UncategorizedText 등) - 단락으로
        return f"{text}\n\n"


def convert_poster_to_markdown(
    pdf_path: Path,
    output_path: Path | None = None,
    strategy: str = "auto"
) -> Dict:
    """포스터 PDF를 Markdown으로 변환"""
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    print(f"📄 PDF 파싱 중: {pdf_path.name}")
    print(f"   전략: {strategy}\n")
    
    start_time = time.time()
    
    # PDF 파싱
    elements = partition_pdf(
        filename=str(pdf_path),
        strategy=strategy,
        infer_table_structure=False,
        extract_images_in_pdf=False,
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"✅ 파싱 완료 ({elapsed_time:.2f}초)")
    print(f"   추출된 요소 수: {len(elements)}개\n")
    
    # Markdown 변환
    markdown_parts = []
    
    # 헤더 추가
    pdf_name = pdf_path.stem
    markdown_parts.append(f"# {pdf_name}\n\n")
    markdown_parts.append(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    markdown_parts.append(f"**원본 파일**: `{pdf_path.name}`\n\n")
    markdown_parts.append("---\n\n")
    
    # 요소별로 Markdown 변환
    element_count_by_type = {}
    for element in elements:
        if hasattr(element, 'text') and element.text:
            element_type = getattr(element, 'category', 'Unknown')
            element_count_by_type[element_type] = element_count_by_type.get(element_type, 0) + 1
            
            md_content = element_to_markdown(element)
            if md_content:
                markdown_parts.append(md_content)
    
    # 통계 추가
    markdown_parts.append("\n---\n\n")
    markdown_parts.append("## 추출 통계\n\n")
    markdown_parts.append(f"- 총 요소 수: {len(elements)}개\n")
    for elem_type, count in sorted(element_count_by_type.items(), key=lambda x: -x[1]):
        markdown_parts.append(f"- {elem_type}: {count}개\n")
    markdown_parts.append(f"- 처리 시간: {elapsed_time:.2f}초\n\n")
    
    full_markdown = "".join(markdown_parts)
    
    # 원본 텍스트도 추출 (비교용)
    original_text_parts = []
    original_text_only = []  # 타입 정보 없이 순수 텍스트만
    
    for element in elements:
        if hasattr(element, 'text') and element.text:
            element_type = getattr(element, 'category', 'Unknown')
            text = element.text.strip()
            if text:
                original_text_parts.append(f"[{element_type}] {text}")
                original_text_only.append(text)
    
    original_text = "\n\n".join(original_text_parts)
    original_text_clean = "\n\n".join(original_text_only)  # 비교용 순수 텍스트
    
    # 출력 경로 결정
    if output_path is None:
        output_dir = pdf_path.parent / "poster_markdown"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{pdf_path.stem}.md"
    
    # MD 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_markdown)
    
    print(f"💾 Markdown 파일 저장: {output_path}")
    print(f"   파일 크기: {output_path.stat().st_size / 1024:.2f} KB\n")
    
    return {
        "markdown_path": output_path,
        "markdown_content": full_markdown,
        "original_text": original_text,
        "original_text_clean": original_text_clean,  # 비교용 순수 텍스트
        "element_count": len(elements),
        "element_count_by_type": element_count_by_type,
        "elapsed_time": elapsed_time,
        "pdf_path": pdf_path,
    }


def extract_text_from_markdown(markdown_content: str) -> str:
    """Markdown에서 실제 텍스트만 추출 (메타데이터 섹션 제외)"""
    import re
    lines = markdown_content.split('\n')
    
    # 메타데이터 섹션 찾기 (---로 둘러싸인 부분)
    content_start_idx = 0
    content_end_idx = len(lines)
    
    found_first_dash = False
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not found_first_dash:
                found_first_dash = True
                continue
            else:
                # 두 번째 ---를 만남 = 메타데이터 끝
                content_start_idx = i + 1
                break
    
    # 통계 섹션 찾기
    for i in range(content_start_idx, len(lines)):
        if lines[i].strip().startswith('## 추출 통계'):
            content_end_idx = i
            break
    
    # 실제 내용만 추출
    content_lines = lines[content_start_idx:content_end_idx]
    text = '\n'.join(content_lines)
    
    # Markdown 문법 제거 (텍스트만 남김)
    # 헤더 제거 (#, ## 등) - # 기호만 제거하고 텍스트는 유지
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 볼드/이탤릭 제거
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # 코드 블록 제거 (내용은 유지)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 링크 제거
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 이미지 제거
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
    
    return text.strip()


def compare_pdf_and_markdown(
    pdf_path: Path,
    markdown_path: Path,
    original_text: str,
    markdown_content: str
):
    """PDF 원본과 Markdown 변환 결과 상세 비교"""
    
    print(f"\n{'='*80}")
    print("🔍 PDF 원본과 Markdown 비교")
    print(f"{'='*80}\n")
    
    # Markdown에서 실제 텍스트만 추출 (메타데이터 제외)
    md_text_only = extract_text_from_markdown(markdown_content)
    
    # PDF 원본 텍스트 정리 (요소 타입 제거)
    pdf_text_clean = original_text
    
    # 통계 비교
    pdf_lines = [line.strip() for line in pdf_text_clean.split('\n') if line.strip()]
    md_lines = [line.strip() for line in md_text_only.split('\n') if line.strip()]
    
    pdf_words = len(pdf_text_clean.split())
    md_words = len(md_text_only.split())
    
    pdf_chars = len(pdf_text_clean.replace('\n', '').replace(' ', ''))
    md_chars = len(md_text_only.replace('\n', '').replace(' ', ''))
    
    print("📊 통계 비교")
    print("-" * 80)
    print(f"{'항목':<30} {'PDF 원본':<20} {'Markdown':<20} {'차이':<15}")
    print("-" * 80)
    print(f"{'단어 수':<30} {pdf_words:<20} {md_words:<20} {abs(pdf_words - md_words):<15}")
    print(f"{'문자 수 (공백 제외)':<30} {pdf_chars:<20} {md_chars:<20} {abs(pdf_chars - md_chars):<15}")
    print(f"{'줄 수 (비어있지 않은)':<30} {len(pdf_lines):<20} {len(md_lines):<20} {abs(len(pdf_lines) - len(md_lines)):<15}")
    
    diff_ratio = abs(pdf_chars - md_chars) / pdf_chars * 100 if pdf_chars > 0 else 0
    similarity = 100 - diff_ratio
    print(f"\n📏 텍스트 유사도: {similarity:.2f}%")
    
    if similarity > 95:
        print("   ✅ 매우 높은 유사도 - 변환이 성공적입니다!")
    elif similarity > 80:
        print("   ✅ 높은 유사도 - 변환이 양호합니다.")
    elif similarity > 60:
        print("   ⚠️  중간 유사도 - 일부 내용이 누락되었을 수 있습니다.")
    else:
        print("   ❌ 낮은 유사도 - 변환에 문제가 있을 수 있습니다.")
    
    print()
    
    # 공통 키워드 확인
    import re
    pdf_keywords = set(re.findall(r'\b[A-Z][A-Za-z]{2,}\b', pdf_text_clean))
    md_keywords = set(re.findall(r'\b[A-Z][A-Za-z]{2,}\b', md_text_only))
    common_keywords = pdf_keywords & md_keywords
    
    print(f"🔑 공통 키워드: {len(common_keywords)}개 (PDF: {len(pdf_keywords)}개, MD: {len(md_keywords)}개)")
    if common_keywords:
        sorted_common = sorted([kw for kw in common_keywords if len(kw) > 3], key=len, reverse=True)
        print(f"   예시: {', '.join(sorted_common[:15])}")
    print()
    
    # 샘플 비교
    print("📝 샘플 텍스트 비교 (처음 1000자)")
    print("-" * 80)
    
    print("\n【PDF 원본】")
    pdf_sample = pdf_text_clean[:1000]
    # 여러 줄로 표시
    pdf_sample_lines = pdf_sample.split('\n')[:15]
    for line in pdf_sample_lines:
        print(f"  {line[:90]}")
    if len(pdf_text_clean) > 1000:
        print("  ...")
    
    print("\n【Markdown 변환】")
    md_sample = md_text_only[:1000]
    md_sample_lines = md_sample.split('\n')[:15]
    for line in md_sample_lines:
        print(f"  {line[:90]}")
    if len(md_text_only) > 1000:
        print("  ...")
    
    print()
    
    # 주요 내용 추출 비교
    print("📌 주요 내용 추출 비교")
    print("-" * 80)
    
    # 제목 후보 비교
    pdf_titles = []
    md_titles = []
    
    for line in pdf_lines[:50]:
        if 10 < len(line) < 150 and line and (line[0].isupper() or line.startswith('#')):
            pdf_titles.append(line)
    
    for line in md_lines[:50]:
        if 10 < len(line) < 150 and line and (line[0].isupper() or line.startswith('#')):
            md_titles.append(line)
    
    print("\n제목/섹션 후보:")
    print("  PDF 원본 (상위 5개):")
    for title in pdf_titles[:5]:
        print(f"    - {title[:80]}")
    
    print("\n  Markdown (상위 5개):")
    for title in md_titles[:5]:
        print(f"    - {title[:80]}")
    
    print()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="포스터 PDF를 Markdown으로 변환")
    parser.add_argument(
        "--pdf",
        type=str,
        default="614. Acute Lymphoblastic Leukemias Biomarkers, Molecular Markers, and Measurable Residual Disease in_MON_5144_ASH2025.pdf",
        help="변환할 포스터 PDF 파일명",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="출력 Markdown 파일 경로 (지정하지 않으면 자동 생성)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="auto",
        choices=["auto", "hi_res", "fast"],
        help="PDF 파싱 전략 (기본: auto)",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="비교 분석 건너뛰기",
    )
    
    args = parser.parse_args()
    
    data_dir = get_data_directory()
    pdf_path = data_dir / args.pdf
    
    if not pdf_path.exists():
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return 1
    
    print(f"📂 데이터 디렉토리: {data_dir}")
    print(f"📂 프로젝트 루트: {get_project_root()}\n")
    
    # 출력 경로
    output_path = None
    if args.output:
        output_path = Path(args.output)
    
    try:
        # PDF를 Markdown으로 변환
        result = convert_poster_to_markdown(
            pdf_path=pdf_path,
            output_path=output_path,
            strategy=args.strategy,
        )
        
        # 비교 분석
        if not args.no_compare:
            compare_pdf_and_markdown(
                pdf_path=result["pdf_path"],
                markdown_path=result["markdown_path"],
                original_text=result.get("original_text_clean", result["original_text"]),
                markdown_content=result["markdown_content"],
            )
        
        print(f"\n{'='*80}")
        print("✅ 변환 완료!")
        print(f"{'='*80}\n")
        print(f"📄 PDF: {pdf_path.name}")
        print(f"📝 Markdown: {result['markdown_path']}")
        print(f"⏱️ 처리 시간: {result['elapsed_time']:.2f}초")
        print(f"📊 추출된 요소: {result['element_count']}개")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

