"""
워크스페이스 관리 유틸리티

코드 파일 저장 및 관리 기능을 제공합니다.
"""

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from src.utils.paths import get_workspace_subdirectories


def setup_workspace_directories(base_path: Optional[Path] = None) -> Dict[str, Path]:
    """Workspace 디렉토리 구조 생성 및 반환
    
    Args:
        base_path: 기본 경로 (None이면 프로젝트 루트 사용, deprecated - get_workspace_subdirectories 사용 권장)
        
    Returns:
        디렉토리 경로 딕셔너리
    """
    # 새로운 경로 유틸리티 사용 (환경변수 지원)
    if base_path is None:
        return get_workspace_subdirectories()
    
    # 하위 호환성을 위해 base_path가 제공된 경우
    workspace_base = base_path / "workspace"
    
    directories = {
        "base": workspace_base,
        "generated_code": workspace_base / "generated_code",
        "approved_code": workspace_base / "approved_code",
        "executed_code": workspace_base / "executed_code",
        "results": workspace_base / "results"
    }
    
    # 디렉토리 생성
    for dir_path in directories.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return directories


def save_code_to_workspace(
    code: str,
    directory: str = "generated_code",
    prefix: str = "analysis",
    base_path: Optional[Path] = None
) -> Path:
    """코드를 workspace 디렉토리에 파일로 저장
    
    Args:
        code: 저장할 코드 문자열
        directory: 저장할 디렉토리 (generated_code, approved_code, executed_code)
        prefix: 파일명 접두사
        base_path: 기본 경로 (None이면 프로젝트 루트 사용)
        
    Returns:
        저장된 파일 경로
    """
    directories = setup_workspace_directories(base_path)
    
    if directory not in directories:
        raise ValueError(f"잘못된 디렉토리: {directory}. 가능한 값: generated_code, approved_code, executed_code")
    
    target_dir = directories[directory]
    
    # 타임스탬프 기반 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.py"
    file_path = target_dir / filename
    
    # 파일 저장
    file_path.write_text(code, encoding='utf-8')
    
    print(f"💾 코드 파일 저장: {file_path}")
    
    return file_path


def move_code_file(
    source_file: Path,
    target_directory: str = "approved_code",
    base_path: Optional[Path] = None
) -> Path:
    """코드 파일을 다른 디렉토리로 이동
    
    Args:
        source_file: 이동할 파일 경로
        target_directory: 대상 디렉토리
        base_path: 기본 경로
        
    Returns:
        이동된 파일 경로
    """
    directories = setup_workspace_directories(base_path)
    
    if target_directory not in directories:
        raise ValueError(f"잘못된 디렉토리: {target_directory}")
    
    target_dir = directories[target_directory]
    target_file = target_dir / source_file.name
    
    # 파일 이동
    source_file.rename(target_file)
    
    print(f"📦 코드 파일 이동: {source_file.name} → {target_directory}/")
    
    return target_file

