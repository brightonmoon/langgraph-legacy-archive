"""
경로 설정 유틸리티

프로젝트 루트, 데이터 디렉토리, 워크스페이스 디렉토리 등을 관리합니다.
환경변수를 통해 설정 가능하며, 기본값은 프로젝트 구조를 기반으로 자동 감지합니다.
"""

import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 경로 반환
    
    Returns:
        프로젝트 루트 Path 객체
    """
    # 환경변수로 설정 가능
    if project_root_env := os.getenv("AGENTIC_AI_PROJECT_ROOT"):
        return Path(project_root_env).resolve()
    
    # 현재 파일 위치를 기준으로 프로젝트 루트 찾기
    # src/utils/paths.py -> src/utils -> src -> project_root
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    
    return project_root


def get_data_directory() -> Path:
    """데이터 디렉토리 경로 반환
    
    CSV 파일 등 분석할 데이터 파일들이 저장된 디렉토리
    
    Returns:
        데이터 디렉토리 Path 객체
    """
    project_root = get_project_root()
    
    # 환경변수로 설정 가능
    if data_dir_env := os.getenv("AGENTIC_AI_DATA_DIR"):
        data_dir = Path(data_dir_env)
        if data_dir.is_absolute():
            return data_dir.resolve()
        else:
            return (project_root / data_dir).resolve()
    
    # 기본값: 프로젝트 루트의 data 디렉토리
    data_dir = project_root / "data"
    # 디렉토리가 없으면 생성
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir.resolve()


def get_workspace_directory() -> Path:
    """워크스페이스 디렉토리 경로 반환
    
    생성된 코드, 실행 결과 등이 저장되는 디렉토리
    
    Returns:
        워크스페이스 디렉토리 Path 객체
    """
    project_root = get_project_root()
    
    # 환경변수로 설정 가능
    if workspace_dir_env := os.getenv("AGENTIC_AI_WORKSPACE_DIR"):
        workspace_dir = Path(workspace_dir_env)
        if workspace_dir.is_absolute():
            return workspace_dir.resolve()
        else:
            return (project_root / workspace_dir).resolve()
    
    # 기본값: 프로젝트 루트의 workspace 디렉토리
    workspace_dir = project_root / "workspace"
    return workspace_dir.resolve()


def get_workspace_subdirectories() -> dict[str, Path]:
    """워크스페이스 하위 디렉토리 구조 반환 및 생성
    
    Returns:
        디렉토리 이름과 Path 객체의 딕셔너리
    """
    workspace_base = get_workspace_directory()
    
    subdirs = {
        "base": workspace_base,
        "generated_code": workspace_base / "generated_code",
        "approved_code": workspace_base / "approved_code",
        "executed_code": workspace_base / "executed_code",
        "results": workspace_base / "results",
    }
    
    # 디렉토리 생성
    for dir_path in subdirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return subdirs


def resolve_data_file_path(filepath: str) -> Path:
    """데이터 파일 경로 해석
    
    상대 경로인 경우 데이터 디렉토리를 기준으로 해석하고,
    절대 경로인 경우 그대로 사용합니다.
    
    Args:
        filepath: 파일 경로 (상대 또는 절대)
        
    Returns:
        해석된 파일 경로 Path 객체
    """
    path = Path(filepath)
    
    if path.is_absolute():
        return path.resolve()
    
    # 상대 경로인 경우 데이터 디렉토리 기준
    data_dir = get_data_directory()
    return (data_dir / path).resolve()


def get_docker_image_name() -> str:
    """도커 이미지 이름 반환
    
    Returns:
        도커 이미지 이름
    """
    # 환경변수로 설정 가능
    return os.getenv("CSV_AGENT_DOCKER_IMAGE", "csv-sandbox:test")

