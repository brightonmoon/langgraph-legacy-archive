#!/usr/bin/env python3
"""
문서 인덱스 자동 생성 스크립트

모든 문서의 메타데이터를 파싱하여 검색 가능한 인덱스를 생성합니다.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# 문서 디렉토리 경로
DOCS_DIR = Path(".cursor/docs")

# 메타데이터 패턴
METADATA_PATTERNS = {
    "생성 일시": r'\*\*생성 일시\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
    "문서 유형": r'\*\*문서 유형\*\*:\s*(.+)',
    "관련 주제": r'\*\*관련 주제\*\*:\s*\[(.+?)\]',
    "목적": r'\*\*목적\*\*:\s*(.+)',
    "프로젝트": r'\*\*프로젝트\*\*:\s*(.+)',
}


def extract_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    """파일에서 메타데이터 추출"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {file_path} - {e}")
        return {}
    
    metadata = {
        "제목": None,
        "생성 일시": None,
        "문서 유형": None,
        "관련 주제": None,
        "목적": None,
        "프로젝트": None,
        "경로": str(file_path.relative_to(DOCS_DIR)),
    }
    
    # 제목 추출 (첫 번째 # 제목)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata["제목"] = title_match.group(1).strip()
    
    # 메타데이터 추출
    for key, pattern in METADATA_PATTERNS.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip()
            if key == "관련 주제":
                # 태그 리스트로 변환
                tags = [tag.strip() for tag in value.split(',')]
                metadata[key] = tags
            else:
                metadata[key] = value
    
    return metadata


def generate_index() -> str:
    """전체 문서 인덱스 생성"""
    index_lines = []
    index_lines.append("# 문서 인덱스")
    index_lines.append("")
    index_lines.append(f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    index_lines.append("**목적**: 모든 문서의 검색 가능한 인덱스")
    index_lines.append("")
    index_lines.append("---")
    index_lines.append("")
    
    # 카테고리별 문서 수집
    categories = {}
    total_count = 0
    
    # completed 디렉토리의 하위 디렉토리 검색
    completed_dir = DOCS_DIR / "completed"
    
    for category_dir in sorted(completed_dir.iterdir()):
        if not category_dir.is_dir() or category_dir.name == "README.md":
            continue
        
        category = category_dir.name
        categories[category] = []
        
        for mdc_file in sorted(category_dir.glob("*.mdc")):
            metadata = extract_metadata(mdc_file)
            if metadata:
                categories[category].append(metadata)
                total_count += 1
    
    # 루트 레벨 문서 (completed 디렉토리 직접)
    root_docs = []
    for mdc_file in sorted(completed_dir.glob("*.mdc")):
        metadata = extract_metadata(mdc_file)
        if metadata:
            root_docs.append(metadata)
            total_count += 1
    
    # 인덱스 생성
    index_lines.append(f"## 📊 통계")
    index_lines.append("")
    index_lines.append(f"- **총 문서 수**: {total_count}개")
    index_lines.append(f"- **카테고리 수**: {len(categories)}개")
    index_lines.append("")
    index_lines.append("---")
    index_lines.append("")
    
    # 카테고리별 인덱스
    for category, docs in sorted(categories.items()):
        if not docs:
            continue
        
        index_lines.append(f"## 📁 {category.capitalize()} ({len(docs)}개)")
        index_lines.append("")
        
        for doc in docs:
            title = doc.get("제목", "제목 없음")
            path = doc.get("경로", "")
            date = doc.get("생성 일시", "")
            tags = doc.get("관련 주제", [])
            
            index_lines.append(f"### {title}")
            index_lines.append("")
            index_lines.append(f"- **경로**: `{path}`")
            if date:
                index_lines.append(f"- **생성 일시**: {date}")
            tags = doc.get("관련 주제", [])
            if tags is None:
                tags = []
            if tags:
                index_lines.append(f"- **태그**: {', '.join(tags)}")
            index_lines.append("")
        
        index_lines.append("---")
        index_lines.append("")
    
    # 루트 레벨 문서
    if root_docs:
        index_lines.append(f"## 📄 루트 레벨 문서 ({len(root_docs)}개)")
        index_lines.append("")
        
        for doc in root_docs:
            title = doc.get("제목", "제목 없음")
            path = doc.get("경로", "")
            index_lines.append(f"- [{title}]({path})")
        index_lines.append("")
    
    # 태그별 인덱스
    tag_index = defaultdict(list)
    for category, docs in categories.items():
        for doc in docs:
            tags = doc.get("관련 주제", [])
            if tags is None:
                tags = []
            title = doc.get("제목", "제목 없음")
            path = doc.get("경로", "")
            
            for tag in tags:
                tag_index[tag].append((title, path))
    
    if tag_index:
        index_lines.append("## 🏷️ 태그별 인덱스")
        index_lines.append("")
        
        for tag in sorted(tag_index.keys()):
            docs = tag_index[tag]
            index_lines.append(f"### {tag} ({len(docs)}개)")
            index_lines.append("")
            for title, path in docs:
                index_lines.append(f"- [{title}]({path})")
            index_lines.append("")
    
    return "\n".join(index_lines)


def main():
    """메인 함수"""
    print("=" * 60)
    print("문서 인덱스 자동 생성 스크립트")
    print("=" * 60)
    print(f"대상 디렉토리: {DOCS_DIR.absolute()}")
    print()
    
    # 인덱스 생성
    index_content = generate_index()
    
    # 인덱스 파일 저장
    index_file = DOCS_DIR / "index.mdc"
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        print(f"✅ 인덱스 파일 생성 완료: {index_file.relative_to(DOCS_DIR)}")
    except Exception as e:
        print(f"❌ 인덱스 파일 생성 실패: {e}")
        return
    
    print()
    print("=" * 60)
    print("인덱스 생성 완료")
    print("=" * 60)
    print(f"인덱스 파일: {index_file.relative_to(DOCS_DIR)}")
    print()
    print("✅ 문서 인덱스 자동 생성 완료!")


if __name__ == "__main__":
    main()

