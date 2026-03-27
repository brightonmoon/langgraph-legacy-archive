"""
Docker Path Converter - 호스트 경로를 도커 경로로 변환하는 유틸리티

마운트 정보를 기반으로 정확한 도커 경로 변환을 수행합니다.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def calculate_mount_info(
    code_file: Path,
    input_files: List[Path],
    output_directory: Optional[Path] = None
) -> Dict[str, str]:
    """마운트 정보 계산 (DockerExecutor._prepare_volumes와 동일한 로직)
    
    Args:
        code_file: 코드 파일 경로
        input_files: 입력 파일 경로 목록
        output_directory: 출력 디렉토리 경로
        
    Returns:
        마운트 정보 (파일명 -> 도커 경로 매핑)
    """
    mount_info: Dict[str, str] = {}
    
    # 코드 파일 자체도 마운트 정보에 포함
    mount_info[code_file.name] = f"/workspace/code/{code_file.name}"
    
    # 입력 파일 마운트
    mounted_dirs = {}
    data_dir_index = 0
    code_parent = str(code_file.parent)
    
    for input_file in input_files:
        if not input_file.exists():
            continue
            
        parent = str(input_file.parent)
        
        # 같은 디렉토리면 코드 디렉토리에서 접근 가능
        if parent == code_parent:
            docker_path = f"/workspace/code/{input_file.name}"
            mount_info[input_file.name] = docker_path
            continue
        
        # 이미 마운트된 디렉토리는 건너뛰기
        if parent in mounted_dirs:
            bind_path = mounted_dirs[parent]
            docker_path = f"{bind_path}/{input_file.name}"
            mount_info[input_file.name] = docker_path
            continue
        
        # 다른 디렉토리에 있으면 별도로 마운트
        bind_path = f"/workspace/data_{data_dir_index}" if data_dir_index > 0 else "/workspace/data"
        mounted_dirs[parent] = bind_path
        docker_path = f"{bind_path}/{input_file.name}"
        mount_info[input_file.name] = docker_path
        data_dir_index += 1
    
    # 출력 디렉토리 마운트
    if output_directory:
        mount_info["output_directory"] = "/workspace/results"
    
    return mount_info


def convert_host_paths_to_docker(
    code: str,
    code_file: Path,
    input_files: List[Path],
    mount_info: Dict[str, str]
) -> str:
    """호스트 경로를 도커 경로로 변환
    
    Args:
        code: 변환할 코드 문자열
        code_file: 코드 파일 경로
        input_files: 입력 파일 경로 목록
        mount_info: 마운트 정보 (파일명 -> 도커 경로 매핑)
        
    Returns:
        변환된 코드 문자열
    """
    code_to_execute = code
    
    if not input_files:
        return code_to_execute
    
    # 여러 파일 모드
    if len(input_files) > 1:
        filepath_vars = []
        for i, input_file_path in enumerate(input_files):
            var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
            
            # 마운트 정보에서 도커 경로 가져오기
            docker_path = mount_info.get(input_file_path.name)
            if not docker_path:
                # 마운트 정보에 없으면 기본 경로 사용
                code_parent = str(code_file.parent)
                csv_parent = str(input_file_path.parent)
                if csv_parent == code_parent:
                    docker_path = f"/workspace/code/{input_file_path.name}"
                else:
                    docker_path = f"/workspace/data/{input_file_path.name}"
            
            filepath_vars.append(f'{var_name} = "{docker_path}"')
        
        # 기존 filepath 변수들을 Docker 경로로 교체
        for i, input_file_path in enumerate(input_files):
            var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
            
            # 마운트 정보에서 도커 경로 가져오기
            docker_path = mount_info.get(input_file_path.name)
            if not docker_path:
                code_parent = str(code_file.parent)
                csv_parent = str(input_file_path.parent)
                if csv_parent == code_parent:
                    docker_path = f"/workspace/code/{input_file_path.name}"
                else:
                    docker_path = f"/workspace/data/{input_file_path.name}"
            
            # 기존 변수 정의 패턴 찾아서 교체
            var_pattern = rf'{var_name}\s*=\s*["\']([^"\']+)["\']'
            if re.search(var_pattern, code_to_execute):
                code_to_execute = re.sub(
                    var_pattern,
                    f'{var_name} = "{docker_path}"',
                    code_to_execute,
                    count=1
                )
        
        # 파일 경로 변수가 없으면 추가
        has_filepath_vars = any(
            f'filepath_{i+1}' in code_to_execute or 
            (i == 0 and 'filepath' in code_to_execute and '=' in code_to_execute.split('filepath')[1][:20])
            for i in range(len(input_files))
        )
        
        if not has_filepath_vars:
            code_to_execute = '\n'.join(filepath_vars) + '\n' + code_to_execute
        
        # 하드코딩된 경로를 변수로 교체
        for i, input_file_path in enumerate(input_files):
            var_name = 'filepath' if i == 0 else f'filepath_{i+1}'
            
            # 마운트 정보에서 도커 경로 가져오기
            docker_path = mount_info.get(input_file_path.name)
            if not docker_path:
                code_parent = str(code_file.parent)
                csv_parent = str(input_file_path.parent)
                if csv_parent == code_parent:
                    docker_path = f"/workspace/code/{input_file_path.name}"
                else:
                    docker_path = f"/workspace/data/{input_file_path.name}"
            
            # 하드코딩된 경로 패턴들
            patterns = [
                (rf'pd\.read_csv\(["\']{re.escape(input_file_path.name)}["\']', f'pd.read_csv({var_name})'),
                (rf'pd\.read_csv\(["\']{re.escape(docker_path)}["\']', f'pd.read_csv({var_name})'),
                (rf'pd\.read_csv\(["\']{re.escape(str(input_file_path))}["\']', f'pd.read_csv({var_name})'),
                (rf'pd\.read_csv\(["\']workspace/[^"\']+["\']', f'pd.read_csv({var_name})'),
                (rf'read_csv\(["\']{re.escape(input_file_path.name)}["\']', f'read_csv({var_name})'),
            ]
            
            for pattern, replacement in patterns:
                code_to_execute = re.sub(pattern, replacement, code_to_execute)
    
    # 단일 파일 모드
    else:
        input_file_path = input_files[0]
        
        # 마운트 정보에서 도커 경로 가져오기
        docker_path = mount_info.get(input_file_path.name)
        if not docker_path:
            code_parent = str(code_file.parent)
            csv_parent = str(input_file_path.parent)
            if csv_parent == code_parent:
                docker_path = f"/workspace/code/{input_file_path.name}"
            else:
                docker_path = f"/workspace/data/{input_file_path.name}"
        
        # filepath 변수가 이미 있으면 Docker 경로로 교체, 없으면 추가
        filepath_pattern = r'filepath\s*=\s*["\']([^"\']+)["\']'
        if re.search(filepath_pattern, code_to_execute):
            # 기존 filepath 변수를 Docker 경로로 교체
            code_to_execute = re.sub(
                filepath_pattern,
                f'filepath = "{docker_path}"',
                code_to_execute,
                count=1  # 첫 번째 매치만 교체
            )
        else:
            # filepath 변수가 없으면 추가
            code_to_execute = f'filepath = "{docker_path}"\n' + code_to_execute
        
        # 하드코딩된 경로를 변수로 교체
        patterns = [
            (rf'pd\.read_csv\(["\']{re.escape(input_file_path.name)}["\']', 'pd.read_csv(filepath)'),
            (rf'pd\.read_csv\(["\']{re.escape(docker_path)}["\']', 'pd.read_csv(filepath)'),
            (rf'pd\.read_csv\(["\']{re.escape(str(input_file_path))}["\']', 'pd.read_csv(filepath)'),
            (rf'pd\.read_csv\(["\']workspace/[^"\']+["\']', 'pd.read_csv(filepath)'),
            (rf'read_csv\(["\']{re.escape(input_file_path.name)}["\']', 'read_csv(filepath)'),
        ]
        
        for pattern, replacement in patterns:
            code_to_execute = re.sub(pattern, replacement, code_to_execute)
        
        # pd.read_csv("파일명") 패턴이 남아있으면 변수로 교체
        remaining_pattern = r'pd\.read_csv\(["\']([^"\']+)["\']'
        if re.search(remaining_pattern, code_to_execute):
            # filepath 변수가 이미 정의되어 있는지 확인
            filepath_defined = 'filepath' in code_to_execute.split('pd.read_csv')[0] if 'pd.read_csv' in code_to_execute else False
            if not filepath_defined:
                code_to_execute = re.sub(remaining_pattern, 'pd.read_csv(filepath)', code_to_execute)
    
    return code_to_execute


def get_docker_path_for_file(
    file_path: Path,
    code_file: Path,
    mount_info: Dict[str, str]
) -> str:
    """파일의 도커 경로 가져오기
    
    Args:
        file_path: 파일 경로
        code_file: 코드 파일 경로
        mount_info: 마운트 정보 (파일명 -> 도커 경로 매핑)
        
    Returns:
        도커 경로
    """
    # 마운트 정보에서 먼저 확인
    docker_path = mount_info.get(file_path.name)
    if docker_path:
        return docker_path
    
    # 마운트 정보에 없으면 기본 경로 계산
    code_parent = str(code_file.parent)
    file_parent = str(file_path.parent)
    
    if file_parent == code_parent:
        return f"/workspace/code/{file_path.name}"
    else:
        return f"/workspace/data/{file_path.name}"

