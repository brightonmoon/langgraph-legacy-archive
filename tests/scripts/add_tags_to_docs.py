#!/usr/bin/env python3
"""
문서 태그 자동 추가 스크립트

태그가 없는 문서에 카테고리와 파일명 기반으로 태그를 자동 추가합니다.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

# 문서 디렉토리 경로
DOCS_DIR = Path(".cursor/docs")

# 카테고리별 기본 태그
CATEGORY_TAGS: Dict[str, List[str]] = {
    "architecture": ["Architecture", "Design", "System Design"],
    "implementation": ["Implementation", "Agent", "Development"],
    "analysis": ["Analysis", "Comparison", "Research"],
    "integration": ["Integration", "MCP", "Migration"],
    "fixes": ["Fixes", "Bug Fix", "Troubleshooting"],
    "guides": ["Guides", "Tutorial", "Documentation"],
    "reports": ["Reports", "Completion", "Summary"],
    "research": ["Research", "Testing", "Experiment"],
    "setup": ["Setup", "Configuration", "Strategy"],
    "legacy": ["Legacy", "Backup"],
}

# 파일명 기반 태그 매핑
FILENAME_TAGS: Dict[str, List[str]] = {
    "langgraph": ["LangGraph"],
    "langchain": ["LangChain"],
    "mcp": ["MCP"],
    "middleware": ["Middleware"],
    "streaming": ["Streaming"],
    "agent": ["Agent"],
    "coding": ["Coding Agent"],
    "orchestrator": ["Orchestrator", "Worker"],
    "deepagent": ["DeepAgent"],
    "ollama": ["Ollama"],
    "tool": ["Tool Calling"],
    "cli": ["CLI"],
    "refactoring": ["Refactoring"],
    "phase": ["Phase Report"],
}


def extract_tags_from_filename(filename: str) -> List[str]:
    """파일명에서 태그 추출"""
    tags = []
    filename_lower = filename.lower()
    
    for keyword, tag_list in FILENAME_TAGS.items():
        if keyword in filename_lower:
            tags.extend(tag_list)
    
    return tags


def get_category_tags(category: str) -> List[str]:
    """카테고리별 기본 태그 반환"""
    return CATEGORY_TAGS.get(category, [])


def has_tags(file_path: Path) -> bool:
    """파일에 태그가 있는지 확인"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return bool(re.search(r'\*\*관련 주제\*\*:\s*\[', content))
    except Exception:
        return False


def add_tags_to_file(file_path: Path, category: str) -> bool:
    """파일에 태그 추가"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {file_path} - {e}")
        return False
    
    # 태그 생성
    category_tags = get_category_tags(category)
    filename_tags = extract_tags_from_filename(file_path.name)
    
    # 중복 제거 및 정렬
    all_tags = list(set(category_tags + filename_tags))
    all_tags.sort()
    
    if not all_tags:
        all_tags = ["Documentation"]
    
    tags_line = f"**관련 주제**: [{', '.join(all_tags)}]"
    
    # 생성 일시 라인 찾기
    date_pattern = r'\*\*생성 일시\*\*:\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
    date_inserted = False
    
    for i, line in enumerate(lines):
        # 생성 일시 라인 찾기
        if re.search(date_pattern, line):
            # 다음 줄에 태그 추가
            if i + 1 < len(lines) and not re.search(r'\*\*관련 주제\*\*', lines[i + 1]):
                lines.insert(i + 1, tags_line + "\n")
                date_inserted = True
                break
    
    # 생성 일시가 없으면 제목 다음에 추가
    if not date_inserted:
        for i, line in enumerate(lines):
            if line.startswith("# "):
                # 제목 다음 빈 줄 이후에 추가
                if i + 2 < len(lines):
                    lines.insert(i + 2, tags_line + "\n")
                break
    
    # 파일 저장
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ 파일 쓰기 실패: {file_path} - {e}")
        return False


def main():
    """메인 함수"""
    print("=" * 60)
    print("문서 태그 자동 추가 스크립트")
    print("=" * 60)
    print(f"대상 디렉토리: {DOCS_DIR.absolute()}")
    print()
    
    # completed 디렉토리의 하위 디렉토리 검색
    completed_dir = DOCS_DIR / "completed"
    
    total_files = 0
    tagged_files = 0
    
    for category_dir in sorted(completed_dir.iterdir()):
        if not category_dir.is_dir() or category_dir.name == "README.md":
            continue
        
        category = category_dir.name
        
        for mdc_file in sorted(category_dir.glob("*.mdc")):
            total_files += 1
            
            if not has_tags(mdc_file):
                if add_tags_to_file(mdc_file, category):
                    tagged_files += 1
                    print(f"✅ {category}/{mdc_file.name}: 태그 추가 완료")
    
    print()
    print("=" * 60)
    print("태그 추가 완료 요약")
    print("=" * 60)
    print(f"처리된 파일 수: {total_files}")
    print(f"태그 추가된 파일 수: {tagged_files}")
    print()
    print("✅ 문서 태그 자동 추가 완료!")


if __name__ == "__main__":
    main()




