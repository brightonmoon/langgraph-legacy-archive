"""
CSV 파일 경로 처리 유틸리티

파일 경로 정규화, 해석, 검색 등의 기능을 제공합니다.
단일/다중 파일 모드를 통합하여 처리합니다.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from src.utils.paths import (
    get_project_root,
    get_data_directory,
    resolve_data_file_path,
)


def normalize_csv_path(csv_filepath: str) -> str:
    """CSV 파일 경로 정규화
    
    Args:
        csv_filepath: 정규화할 CSV 파일 경로
        
    Returns:
        정규화된 파일 경로
    """
    if not csv_filepath:
        return ""
    
    try:
        # resolve_data_file_path를 사용하여 경로 해석
        resolved_path = resolve_data_file_path(csv_filepath)
        csv_filepath = str(resolved_path)
    except Exception:
        # 경로 해석 실패 시 기존 방식으로 폴백
        if not csv_filepath.startswith("/"):
            if "/" not in csv_filepath:
                # 파일명만 있는 경우
                data_dir = get_data_directory()
                csv_filepath = str(data_dir / csv_filepath)
            else:
                # 상대 경로인 경우
                project_root = get_project_root()
                csv_filepath = str(project_root / csv_filepath)
    
    # 중복된 경로 수정 및 tests -> data 변환 (하위 호환성)
    if "/data/data/" in csv_filepath:
        csv_filepath = csv_filepath.replace("/data/data/", "/data/")
    if "/tests/tests/" in csv_filepath:
        csv_filepath = csv_filepath.replace("/tests/tests/", "/data/")
    if "/tests/" in csv_filepath and not csv_filepath.startswith("/tests/"):
        # tests/ 경로를 data/로 변환 (하위 호환성)
        csv_filepath = csv_filepath.replace("/tests/", "/data/")
    
    return csv_filepath


def find_csv_file(csv_path_str: str) -> Optional[Path]:
    """CSV 파일을 찾아서 Path 객체로 반환
    
    여러 경로를 시도하며, 대소문자 무시 검색도 수행합니다.
    
    Args:
        csv_path_str: CSV 파일 경로 문자열
        
    Returns:
        찾은 파일의 Path 객체, 없으면 None
    """
    # tests -> data 경로 변환 (하위 호환성)
    if "/tests/tests/" in csv_path_str:
        csv_path_str = csv_path_str.replace("/tests/tests/", "/data/")
    elif "/tests/" in csv_path_str and not csv_path_str.startswith("/tests/"):
        csv_path_str = csv_path_str.replace("/tests/", "/data/")
    
    csv_file_path = Path(csv_path_str).expanduser()
    
    # 파일이 존재하면 반환
    if csv_file_path.exists():
        return csv_file_path.resolve()
    
    # 대안 경로 시도 (data/ 디렉토리에서 대소문자 무시 검색)
    print(f"⚠️ CSV 파일이 존재하지 않음: {csv_path_str}")
    data_dir = get_data_directory()
    filename = csv_file_path.name
    alt_path = data_dir / filename
    
    if alt_path.exists():
        print(f"✅ 대안 경로 사용: {alt_path}")
        return alt_path.resolve()
    
    # 대소문자 무시 검색
    filename_lower = filename.lower()
    if data_dir.exists():
        for file in data_dir.iterdir():
            if file.is_file() and file.name.lower() == filename_lower:
                found_path = file.resolve()
                print(f"✅ 대소문자 무시 검색으로 파일 발견: {found_path}")
                return found_path
    
    return None


def resolve_csv_file_paths(
    csv_file_path: Optional[str] = None,
    csv_file_paths: Optional[List[str]] = None
) -> List[Path]:
    """단일/다중 파일 모드를 통합하여 CSV 파일 경로 리스트 반환
    
    Args:
        csv_file_path: 단일 CSV 파일 경로 (하위 호환성)
        csv_file_paths: CSV 파일 경로 목록 (다중 파일 모드)
        
    Returns:
        찾은 CSV 파일들의 Path 객체 리스트
    """
    resolved_paths = []
    
    # 여러 파일 모드
    if csv_file_paths and len(csv_file_paths) > 0:
        for csv_path_str in csv_file_paths:
            file_path = find_csv_file(csv_path_str)
            if file_path:
                resolved_paths.append(file_path)
    
    # 단일 파일 모드 (하위 호환성)
    elif csv_file_path:
        file_path = find_csv_file(csv_file_path)
        if file_path:
            resolved_paths.append(file_path)
    
    return resolved_paths


def resolve_csv_files(state: Dict[str, Any]) -> List[Path]:
    """단일/다중 파일 모드를 통합하여 CSV 파일 경로 리스트 반환 (Phase 2)
    
    state에서 직접 CSV_file_path와 CSV_file_paths를 가져와서 처리합니다.
    이 함수는 노드 함수에서 직접 사용하기 위해 설계되었습니다.
    
    Args:
        state: CSVAnalysisState 딕셔너리
        
    Returns:
        찾은 CSV 파일들의 Path 객체 리스트
    """
    csv_file_path = state.get("CSV_file_path")
    csv_file_paths = state.get("CSV_file_paths", [])
    
    return resolve_csv_file_paths(
        csv_file_path=csv_file_path,
        csv_file_paths=csv_file_paths
    )

