"""
Docling 변환 결과 후처리 스크립트

문제:
1. 문서 구조 순서 문제 (ARTICLE INFO → ABSTRACT → Introduction)
2. 이미지로 인한 텍스트 끊김 문제

사용법:
    uv run python tests/scripts/fix_docling_structure.py <input_md_file> [--output <output_md_file>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

from src.utils.paths import get_project_root


def reorder_document_sections(markdown: str) -> str:
    """
    문서 섹션을 올바른 순서로 재정렬
    
    순서: ARTICLE INFO → ABSTRACT → Introduction → ...
    """
    lines = markdown.split('\n')
    
    # 섹션별로 분리
    sections = {
        'header': [],        # 문서 헤더 (제목, 저자 등, ARTICLE INFO 이전)
        'article_info': [],  # ARTICLE INFO
        'abstract': [],      # ABSTRACT
        'introduction': [],  # Introduction
        'rest': []          # 나머지 본문
    }
    
    current_section = 'header'
    i = 0
    found_article_info = False
    found_abstract = False
    found_introduction = False
    
    while i < len(lines):
        line = lines[i]
        
        # ARTICLE INFO 섹션 찾기
        if re.search(r'A\s+R\s+T\s+I\s+C\s+L\s+E\s+I\s+N\s+F\s+O', line, re.IGNORECASE):
            found_article_info = True
            current_section = 'article_info'
            sections[current_section].append(line)
        # ABSTRACT 섹션 찾기 (헤더 형식)
        elif re.search(r'^##\s*A\s+B\s+S\s+T\s+R\s+A\s+C\s+T', line, re.IGNORECASE):
            found_abstract = True
            # ARTICLE INFO 섹션 종료
            if current_section == 'article_info':
                current_section = 'abstract'
            sections['abstract'].append(line)
        # Introduction 섹션 찾기
        elif re.search(r'^##\s*1\.\s*Introduction', line, re.IGNORECASE):
            found_introduction = True
            # ABSTRACT 섹션 종료
            if current_section == 'abstract':
                current_section = 'introduction'
            sections['introduction'].append(line)
        # 다른 섹션 헤더가 나오면 Introduction 종료
        elif re.search(r'^##\s*[2-9]\.', line) or re.search(r'^##\s*[A-Z]', line):
            if current_section == 'introduction':
                current_section = 'rest'
            sections[current_section].append(line)
        else:
            sections[current_section].append(line)
        
        i += 1
    
    # 올바른 순서로 재조합
    reordered = []
    
    # 헤더 (ARTICLE INFO 이전)
    reordered.extend(sections['header'])
    
    # ARTICLE INFO
    if found_article_info:
        reordered.extend(sections['article_info'])
    
    # ABSTRACT
    if found_abstract:
        reordered.extend(sections['abstract'])
    
    # Introduction
    if found_introduction:
        reordered.extend(sections['introduction'])
    
    # 나머지
    reordered.extend(sections['rest'])
    
    return '\n'.join(reordered)


def fix_text_continuity(markdown: str) -> str:
    """
    이미지로 인한 텍스트 끊김 문제 수정
    
    패턴: "텍스트\n\n<!-- image -->\n\n(인용)" 
    → "텍스트 (인용)\n\n<!-- image -->"
    """
    lines = markdown.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 이미지 플레이스홀더 발견
        if '<!-- image -->' in line:
            # 연속된 이미지 찾기
            image_lines = [line]
            j = i + 1
            while j < len(lines) and '<!-- image -->' in lines[j]:
                image_lines.append(lines[j])
                j += 1
            
            # 빈 줄 건너뛰기
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            # 이전 텍스트 확인
            prev_idx = len(result) - 1
            while prev_idx >= 0 and not result[prev_idx].strip():
                prev_idx -= 1
            
            # 다음 텍스트 확인
            next_idx = j
            
            if prev_idx >= 0 and next_idx < len(lines):
                prev_text = result[prev_idx].strip()
                next_text = lines[next_idx].strip()
                
                # 이전 텍스트가 문장 중간이고, 다음이 인용문인 경우
                # 예: "invasiveness" 다음에 "(Coopman et al., 1998; Wang et al., 2002)."
                if prev_text and not prev_text.endswith('.') and \
                   not prev_text.endswith('!') and not prev_text.endswith('?') and \
                   not prev_text.endswith(':') and not prev_text.endswith(';') and \
                   next_text.startswith('(') and ')' in next_text:
                    # 이전 텍스트와 다음 텍스트를 병합
                    result[prev_idx] = prev_text + ' ' + next_text
                    # 이미지들은 그대로 추가
                    result.extend(image_lines)
                    # 다음 텍스트는 건너뛰기
                    i = next_idx + 1
                    continue
            
            # 일반적인 경우: 이미지 그대로 추가
            result.extend(image_lines)
            i = j
        else:
            result.append(line)
            i += 1
    
    return '\n'.join(result)


def fix_specific_pattern(markdown: str) -> str:
    """
    특정 패턴 수정: "invasiveness\n\n<!-- image -->\n\n(Coopman et al., 1998; Wang et al., 2002)."
    """
    # 패턴: 단어 끝 + 빈 줄 + 이미지(들) + 빈 줄 + 인용문
    # 더 정확한 패턴: 단어로 끝나는 줄 + 빈 줄 + 이미지 + 빈 줄 + 인용문으로 시작하는 줄
    pattern = r'([a-zA-Z가-힣]+)\n\n(<!-- image -->\n)+([^<\(]*?)(\([^\)]+\))'
    
    def replace_func(match):
        word = match.group(1)
        images = match.group(2)
        middle = match.group(3).strip()
        citation = match.group(4)
        
        # 단어와 인용문을 연결
        if middle:
            return f"{word} {middle} {citation}\n\n{images}"
        else:
            return f"{word} {citation}\n\n{images}"
    
    markdown = re.sub(pattern, replace_func, markdown, flags=re.MULTILINE | re.DOTALL)
    
    # 더 구체적인 패턴: "invasiveness" 다음에 바로 인용문
    pattern2 = r'(invasiveness)\n\n(<!-- image -->\n)+\(([^\)]+)\)'
    replacement2 = r'\1 (\3)\n\n\2'
    markdown = re.sub(pattern2, replacement2, markdown, flags=re.MULTILINE)
    
    return markdown


def process_markdown(input_path: str, output_path: str) -> None:
    """Markdown 파일을 후처리하여 저장"""
    print(f"📖 읽는 중: {input_path}")
    
    # 원본 읽기
    markdown = Path(input_path).read_text(encoding='utf-8')
    original_length = len(markdown)
    
    print(f"📊 원본 길이: {original_length:,} 자")
    
    # 1. 섹션 재정렬
    print("🔄 섹션 재정렬 중...")
    markdown = reorder_document_sections(markdown)
    
    # 2. 텍스트 끊김 수정
    print("🔧 텍스트 끊김 수정 중...")
    markdown = fix_text_continuity(markdown)
    
    # 3. 특정 패턴 수정
    print("🎯 특정 패턴 수정 중...")
    markdown = fix_specific_pattern(markdown)
    
    # 결과 저장
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown, encoding='utf-8')
    
    final_length = len(markdown)
    print(f"✅ 처리 완료: {output_path}")
    print(f"📊 최종 길이: {final_length:,} 자")
    print(f"📈 변화: {final_length - original_length:+,} 자")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Docling 변환 결과 후처리 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 사용
  uv run python tests/scripts/fix_docling_structure.py input.md
  
  # 출력 파일 지정
  uv run python tests/scripts/fix_docling_structure.py input.md --output output.md
  
  # 실제 파일 예제
  uv run python tests/scripts/fix_docling_structure.py \\
    "data/Docs/DiscoveryAI/Improving fascin inhibitors to block tumor cell migration and emtastasis.md" \\
    --output "data/Docs/DiscoveryAI/Improving fascin inhibitors to block tumor cell migration and emtastasis_fixed.md"
        """
    )
    
    parser.add_argument(
        "input",
        type=str,
        help="입력 Markdown 파일 경로"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="출력 Markdown 파일 경로 (기본: 입력 파일명_fixed.md)"
    )
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    # 출력 파일 경로 결정
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_fixed{input_path.suffix}"
    
    # 처리 실행
    try:
        process_markdown(str(input_path), str(output_path))
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

