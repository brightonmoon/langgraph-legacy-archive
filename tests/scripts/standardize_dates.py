#!/usr/bin/env python3
"""
문서 날짜 형식 표준화 스크립트

모든 .mdc 파일의 날짜 형식을 표준 형식으로 통일합니다.
표준 형식: **생성 일시**: YYYY-MM-DD HH:MM:SS
"""

import re
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# 문서 디렉토리 경로
DOCS_DIR = Path(".cursor/docs")

# 날짜 형식 패턴
PATTERNS = [
    # **생성일**: YYYY-MM-DD HH:MM:SS (이미 시간이 있는 경우는 그대로 유지)
    (r'\*\*생성일\*\*:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', r'**생성 일시**: \1 \2'),
    # **생성일**: YYYY-MM-DD (시간 없음)
    (r'\*\*생성일\*\*:\s*(\d{4}-\d{2}-\d{2})(?!\s+\d{2}:\d{2}:\d{2})', r'**생성 일시**: \1 00:00:00'),
    # **생성 일시**: YYYY-MM-DD HH:MM:SS (이미 시간이 있는 경우는 그대로 유지)
    (r'\*\*생성 일시\*\*:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', r'**생성 일시**: \1 \2'),
    # **생성 일시**: YYYY-MM-DD (시간 없음)
    (r'\*\*생성 일시\*\*:\s*(\d{4}-\d{2}-\d{2})(?!\s+\d{2}:\d{2}:\d{2})', r'**생성 일시**: \1 00:00:00'),
]

# 이미 표준 형식인 경우 (시간 포함)
STANDARD_PATTERN = r'\*\*생성 일시\*\*:\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'


def is_standard_format(line: str) -> bool:
    """이미 표준 형식인지 확인"""
    return bool(re.search(STANDARD_PATTERN, line))


def standardize_date_line(line: str) -> Tuple[str, bool]:
    """
    날짜 라인을 표준 형식으로 변환
    
    Returns:
        (변환된 라인, 변환 여부)
    """
    # 이미 표준 형식이면 변환하지 않음
    if is_standard_format(line):
        return line, False
    
    # 각 패턴 시도
    for pattern, replacement in PATTERNS:
        if re.search(pattern, line):
            new_line = re.sub(pattern, replacement, line)
            return new_line, True
    
    return line, False


def process_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    파일의 날짜 형식을 표준화
    
    Returns:
        (변환된 라인 수, 변환된 라인 목록)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {file_path} - {e}")
        return 0, []
    
    modified_lines = []
    changed_count = 0
    
    for i, line in enumerate(lines):
        new_line, changed = standardize_date_line(line)
        if changed:
            changed_count += 1
            modified_lines.append(f"  라인 {i+1}: {line.strip()} → {new_line.strip()}")
        lines[i] = new_line
    
    if changed_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            print(f"❌ 파일 쓰기 실패: {file_path} - {e}")
            return 0, []
    
    return changed_count, modified_lines


def main():
    """메인 함수"""
    print("=" * 60)
    print("문서 날짜 형식 표준화 스크립트")
    print("=" * 60)
    print(f"대상 디렉토리: {DOCS_DIR.absolute()}")
    print()
    
    # 모든 .mdc 파일 찾기
    mdc_files = list(DOCS_DIR.rglob("*.mdc"))
    
    if not mdc_files:
        print("❌ .mdc 파일을 찾을 수 없습니다.")
        return
    
    print(f"발견된 파일 수: {len(mdc_files)}")
    print()
    
    # 통계
    total_files = 0
    total_changes = 0
    changed_files = []
    
    # 각 파일 처리
    for file_path in sorted(mdc_files):
        # 템플릿 파일은 제외 (템플릿은 YYYY-MM-DD 형식 유지)
        if "templates" in str(file_path):
            continue
        
        changed_count, modified_lines = process_file(file_path)
        
        if changed_count > 0:
            total_files += 1
            total_changes += changed_count
            changed_files.append((file_path, changed_count, modified_lines))
            print(f"✅ {file_path.relative_to(DOCS_DIR)}: {changed_count}개 라인 변환")
    
    # 결과 요약
    print()
    print("=" * 60)
    print("변환 완료 요약")
    print("=" * 60)
    print(f"처리된 파일 수: {len(mdc_files)}")
    print(f"변환된 파일 수: {total_files}")
    print(f"총 변환된 라인 수: {total_changes}")
    
    if changed_files:
        print()
        print("변환된 파일 상세:")
        for file_path, count, lines in changed_files:
            print(f"\n📄 {file_path.relative_to(DOCS_DIR)} ({count}개 라인):")
            for line in lines[:5]:  # 최대 5개만 표시
                print(line)
            if len(lines) > 5:
                print(f"  ... 외 {len(lines) - 5}개 라인")
    
    print()
    print("✅ 날짜 형식 표준화 완료!")
    print()
    print("표준 형식: **생성 일시**: YYYY-MM-DD HH:MM:SS")


if __name__ == "__main__":
    main()

