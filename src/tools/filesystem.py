"""
File System Tools - 파일 시스템 관리 도구
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from langchain.tools import tool


@tool("ls")
def ls_tool(directory: str = ".") -> str:
    """디렉토리의 내용을 나열합니다.
    
    Args:
        directory: 나열할 디렉토리 경로 (기본값: 현재 디렉토리)
        
    Returns:
        디렉토리 내용 목록 (파일 및 폴더 이름)
    """
    try:
        path = Path(directory).expanduser().resolve()
        
        # 보안: 현재 작업 디렉토리 외부 접근 제한
        current_dir = Path.cwd()
        if not path.is_relative_to(current_dir):
            return f"❌ 보안: {directory} 디렉토리에 접근할 수 없습니다."
        
        if not path.exists():
            return f"❌ 디렉토리가 존재하지 않습니다: {directory}"
        
        if not path.is_dir():
            return f"❌ 경로가 디렉토리가 아닙니다: {directory}"
        
        # 디렉토리 내용 나열
        items = []
        for item in sorted(path.iterdir()):
            item_type = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                try:
                    size = f" ({item.stat().st_size} bytes)"
                except Exception:
                    size = ""
            items.append(f"{item_type} {item.name}{size}")
        
        if not items:
            return f"📂 {directory} (비어있음)"
        
        return f"📂 {directory}\n" + "\n".join(items)
        
    except PermissionError:
        return f"❌ 권한이 없어 {directory} 디렉토리에 접근할 수 없습니다."
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@tool("read_file")
def read_file_tool(filepath: str) -> str:
    """파일을 읽어 내용을 반환합니다.

    Args:
        filepath: 읽을 파일 경로

    Returns:
        파일 내용
    """
    try:
        path = Path(filepath).expanduser().resolve()

        # 보안: 현재 작업 디렉토리 외부 접근 제한
        current_dir = Path.cwd()
        if not path.is_relative_to(current_dir):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다."

        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        if not path.is_file():
            return f"❌ 경로가 파일이 아닙니다: {filepath}"
        
        # 파일 크기 제한 (10MB)
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            return f"❌ 파일이 너무 큽니다 ({file_size} bytes). 최대 10MB까지 읽을 수 있습니다."
        
        # 파일 읽기
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return f"📄 {filepath}\n{'=' * 50}\n{content}"
        
    except PermissionError:
        return f"❌ 권한이 없어 {filepath} 파일을 읽을 수 없습니다."
    except UnicodeDecodeError:
        return f"❌ 파일을 텍스트로 읽을 수 없습니다: {filepath}"
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@tool("write_file")
def write_file_tool(filepath: str, content: str) -> str:
    """파일을 작성합니다. 파일이 존재하면 덮어씁니다.

    Args:
        filepath: 작성할 파일 경로
        content: 파일에 쓸 내용

    Returns:
        작업 결과 메시지
    """
    try:
        path = Path(filepath).expanduser().resolve()

        # 보안: 현재 작업 디렉토리 외부 접근 제한
        current_dir = Path.cwd()
        if not path.is_relative_to(current_dir):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다."

        # 디렉토리가 없으면 생성
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 쓰기
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        file_size = path.stat().st_size
        return f"✅ 파일 작성 완료: {filepath} ({file_size} bytes)"
        
    except PermissionError:
        return f"❌ 권한이 없어 {filepath} 파일을 작성할 수 없습니다."
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@tool("edit_file")
def edit_file_tool(filepath: str, edits: List[Dict[str, str]]) -> str:
    """파일을 편집합니다. 여러 편집 작업을 일괄 처리할 수 있습니다.

    Args:
        filepath: 편집할 파일 경로
        edits: 편집 작업 리스트
            각 편집 작업은 다음 중 하나의 형식:
            - {"type": "insert", "line": 10, "content": "새로운 내용"}
            - {"type": "replace", "line": 5, "old": "기존 내용", "new": "새 내용"}
            - {"type": "delete", "line": 3}

    Returns:
        작업 결과 메시지
    """
    try:
        path = Path(filepath).expanduser().resolve()

        # 보안: 현재 작업 디렉토리 외부 접근 제한
        current_dir = Path.cwd()
        if not path.is_relative_to(current_dir):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다."

        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        # 파일 읽기
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 편집 작업 수행
        for edit in edits:
            edit_type = edit.get("type")
            line_num = edit.get("line", 0) - 1  # 1-based to 0-based
            
            if edit_type == "insert":
                content = edit.get("content", "")
                lines.insert(line_num, content + "\n" if not content.endswith("\n") else content)
            elif edit_type == "replace":
                old_content = edit.get("old", "")
                new_content = edit.get("new", "")
                if line_num < len(lines) and old_content in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(old_content, new_content)
            elif edit_type == "delete":
                if 0 <= line_num < len(lines):
                    del lines[line_num]
        
        # 파일 쓰기
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return f"✅ 파일 편집 완료: {filepath} ({len(edits)}개의 편집 작업 적용)"
        
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"
















