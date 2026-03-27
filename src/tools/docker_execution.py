"""
Docker 샌드박스 환경에서 Python 코드 실행 도구

이 모듈은 Docker Python SDK를 사용하여 격리된 Docker 컨테이너에서
Python 코드를 안전하게 실행하는 기능을 제공합니다.

⚠️ DEPRECATED: 이 모듈은 하위 호환성을 위해 유지되지만,
새로운 통합 코드 실행 시스템(src.tools.code_execution)의 DockerExecutor 사용을 권장합니다.
"""

import docker
from pathlib import Path
from typing import Dict, Any, Optional, List


def _validate_mount_path(path: Path) -> bool:
    """호스트 파일시스템 경로가 허용된 디렉토리에 속하는지 검증

    Args:
        path: 검증할 경로

    Returns:
        허용된 경로이면 True, 아니면 False
    """
    try:
        # 절대 경로로 변환
        resolved_path = path.resolve()

        # 프로젝트 루트 디렉토리 찾기 (pyproject.toml이 있는 디렉토리)
        current = Path(__file__).resolve()
        project_root = None
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists():
                project_root = parent
                break

        if project_root is None:
            # pyproject.toml을 찾지 못한 경우, 현재 작업 디렉토리 사용
            project_root = Path.cwd().resolve()

        # 허용된 베이스 디렉토리들
        allowed_bases = [
            project_root,
            project_root / "data",
            project_root / "workspace",
        ]

        # 경로가 허용된 베이스 디렉토리 중 하나에 속하는지 확인
        for base in allowed_bases:
            try:
                if resolved_path.is_relative_to(base):
                    return True
            except ValueError:
                continue

        return False
    except Exception:
        # 경로 해석 실패 시 거부
        return False


def execute_code_in_docker_sandbox(
    code_file: Path,
    csv_file: Optional[Path] = None,
    csv_files: Optional[List[Path]] = None,
    output_dir: Optional[Path] = None,
    image: str = "csv-sandbox:test"
) -> Dict[str, Any]:
    """Docker 샌드박스에서 Python 코드를 실행하고 출력을 반환합니다.
    
    ⚠️ DEPRECATED: 이 함수는 하위 호환성을 위해 유지되지만,
    src.tools.code_execution.execute_code_in_docker() 사용을 권장합니다.
    
    **핵심 원칙**:
    1. 코드와 파일이 외부(호스트)에 있고, 도커 환경에서 실행
    2. 출력은 print()를 통한 stdout 또는 /workspace/results/ 디렉토리의 파일로 저장
    3. LLM이 파악할 수 있도록 모든 출력을 stdout에 포함
    
    여러 CSV 파일을 지원합니다.
    
    Args:
        code_file: 실행할 Python 코드 파일 경로 (호스트 경로)
        csv_file: CSV 데이터 파일 경로 (단일 파일 모드, 하위 호환성)
        csv_files: CSV 데이터 파일 경로 목록 (다중 파일 모드)
        output_dir: 결과 출력 디렉토리 (호스트 경로, 선택사항)
        image: 사용할 Docker 이미지 (기본값: csv-sandbox:test)
        
    Returns:
        실행 결과 딕셔너리:
        - success: 실행 성공 여부 (bool)
        - stdout: 표준 출력 (str) - print 출력 + 출력 파일 내용 포함
        - stderr: 표준 에러 출력 (str, 에러 발생 시)
        - error: 일반 에러 메시지 (str, 에러 발생 시)
        - exit_code: 종료 코드 (int)
        - output_files: 출력 파일 목록 (List[str], 선택사항)
        - mount_info: 마운트 정보 (Dict[str, str], 선택사항) - 파일명 -> 도커 경로 매핑
    """
    try:
        client = docker.from_env()
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"Docker 클라이언트 연결 실패: {str(e)}",
            "exit_code": -1
        }
    
    # 볼륨 마운트 설정
    # 핵심: 코드 파일은 항상 /workspace/code/로 마운트
    # 경로 검증
    if not _validate_mount_path(code_file.parent):
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {code_file.parent}",
            "exit_code": -1
        }

    volumes = {
        str(code_file.parent): {"bind": "/workspace/code", "mode": "ro"},
    }
    
    # CSV 파일 마운트 정보 추적 (파일명 -> 도커 경로 매핑)
    mount_info = {}  # 파일명 -> 도커 경로 매핑
    
    # 여러 파일 모드
    if csv_files and len(csv_files) > 0:
        data_dir_index = 0
        mounted_dirs = {}  # 부모 디렉토리 -> 마운트 포인트 매핑

        for csv_file_item in csv_files:
            if csv_file_item and csv_file_item.exists():
                # 경로 검증
                if not _validate_mount_path(csv_file_item.parent):
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": "",
                        "error": f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {csv_file_item.parent}",
                        "exit_code": -1
                    }

                csv_parent = str(csv_file_item.parent)
                code_parent = str(code_file.parent)

                # 같은 디렉토리면 /workspace/code/에서 접근 가능
                if csv_parent == code_parent:
                    docker_path = f"/workspace/code/{csv_file_item.name}"
                    mount_info[csv_file_item.name] = docker_path
                    print(f"🐳 CSV 파일 마운트: {csv_file_item.name} -> {docker_path} (코드 디렉토리)")
                    continue

                # 이미 마운트된 디렉토리는 건너뛰기
                if csv_parent in mounted_dirs:
                    docker_path = f"{mounted_dirs[csv_parent]}/{csv_file_item.name}"
                    mount_info[csv_file_item.name] = docker_path
                    continue

                # 다른 디렉토리에 있으면 별도로 마운트
                bind_path = f"/workspace/data_{data_dir_index}" if data_dir_index > 0 else "/workspace/data"
                volumes[csv_parent] = {"bind": bind_path, "mode": "ro"}
                mounted_dirs[csv_parent] = bind_path
                docker_path = f"{bind_path}/{csv_file_item.name}"
                mount_info[csv_file_item.name] = docker_path
                print(f"🐳 도커 마운트: {csv_parent} -> {bind_path} (CSV 파일: {csv_file_item.name} -> {docker_path})")
                data_dir_index += 1
    
    # 단일 파일 모드 (하위 호환성)
    elif csv_file and csv_file.exists():
        # 경로 검증
        if not _validate_mount_path(csv_file.parent):
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {csv_file.parent}",
                "exit_code": -1
            }

        csv_parent = str(csv_file.parent)
        code_parent = str(code_file.parent)
        if csv_parent == code_parent:
            # 같은 디렉토리면 /workspace/code/에서 접근 가능
            docker_path = f"/workspace/code/{csv_file.name}"
            mount_info[csv_file.name] = docker_path
            print(f"🐳 CSV 파일 마운트: {csv_file.name} -> {docker_path} (코드 디렉토리)")
        else:
            # CSV 파일이 코드 파일과 다른 디렉토리에 있으면 별도로 마운트
            volumes[csv_parent] = {"bind": "/workspace/data", "mode": "ro"}
            docker_path = f"/workspace/data/{csv_file.name}"
            mount_info[csv_file.name] = docker_path
            print(f"🐳 도커 마운트: {csv_parent} -> /workspace/data (CSV 파일: {csv_file.name} -> {docker_path})")
    
    # 결과 디렉토리가 있으면 마운트
    if output_dir:
        # 경로 검증
        if not _validate_mount_path(output_dir):
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {output_dir}",
                "exit_code": -1
            }

        output_dir.mkdir(parents=True, exist_ok=True)
        volumes[str(output_dir)] = {"bind": "/workspace/results", "mode": "rw"}
    
    # 컨테이너 실행
    try:
        # Docker SDK의 run() 메서드는 timeout 파라미터를 지원하지 않음
        # 대신 detach=False로 실행하고, 컨테이너가 자동으로 종료되도록 함
        # 작업 디렉토리를 /workspace/results로 설정하여 출력 파일이 results 디렉토리에 저장되도록 함
        working_dir = "/workspace/results" if output_dir else "/workspace/code"
        result = client.containers.run(
            image,
            f"python /workspace/code/{code_file.name}",
            volumes=volumes,
            working_dir=working_dir,  # 작업 디렉토리 설정
            remove=True,  # 실행 후 자동 삭제
            stderr=True,  # stderr도 캡처
            stdout=True,  # stdout 캡처
            mem_limit="512m",  # 512MB 메모리 제한
            nano_cpus=1_000_000_000,  # 1 CPU 제한
            pids_limit=100,  # 100 프로세스 제한
            network_mode="none",  # 네트워크 비활성화
        )
        
        stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
        
        # 출력 파일 수집 및 내용 추가 (핵심: LLM이 파악할 수 있도록)
        output_files = []
        output_file_contents = {}
        
        if output_dir and output_dir.exists():
            for file in output_dir.iterdir():
                if file.is_file():
                    output_files.append(str(file))
                    try:
                        content = file.read_text(encoding='utf-8')
                        output_file_contents[str(file)] = content
                    except Exception as e:
                        print(f"⚠️ 출력 파일 읽기 실패: {file} - {str(e)}")
        
        # 출력 파일 내용을 stdout에 추가 (LLM이 파악할 수 있도록)
        if output_file_contents:
            stdout += "\n\n=== 출력 파일 내용 ===\n"
            for file_path, content in output_file_contents.items():
                file_name = Path(file_path).name
                stdout += f"\n📄 {file_name}:\n{content}\n"
        
        return {
            "success": True,
            "stdout": stdout,
            "stderr": "",
            "error": None,
            "exit_code": 0,
            "output_files": output_files,
            "mount_info": mount_info  # 마운트 정보 포함
        }
    except docker.errors.ContainerError as e:
        # 컨테이너 실행 중 에러 발생
        # ContainerError는 stdout과 stderr 속성이 없을 수 있음
        try:
            stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else ""
            stdout = e.stdout.decode('utf-8') if hasattr(e, 'stdout') and e.stdout else ""
        except (AttributeError, UnicodeDecodeError):
            stderr = str(e)
            stdout = ""
        
        exit_code = e.exit_status if hasattr(e, 'exit_status') else -1
        
        # 경로 오류 감지 및 명확한 오류 메시지 추가
        if "FileNotFoundError" in stderr or "No such file or directory" in stderr:
            stderr += "\n\n💡 경로 오류 해결 방법:\n"
            stderr += "- 코드 파일과 같은 디렉토리의 파일: /workspace/code/파일명\n"
            stderr += "- 다른 디렉토리의 파일: /workspace/data/파일명 또는 /workspace/data_N/파일명\n"
            if mount_info:
                stderr += "\n📋 마운트된 파일 경로:\n"
                for file_name, docker_path in mount_info.items():
                    stderr += f"  - {file_name} -> {docker_path}\n"
        
        return {
            "success": False,
            "stdout": stdout,
            "stderr": stderr,
            "error": None,
            "exit_code": exit_code,
            "mount_info": mount_info  # 마운트 정보 포함 (오류 시에도)
        }
    except docker.errors.ImageNotFound:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"Docker 이미지를 찾을 수 없습니다: {image}. 먼저 이미지를 빌드하세요.",
            "exit_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": f"도커 실행 중 오류 발생: {str(e)}",
            "exit_code": -1
        }

