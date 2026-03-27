"""
Docker Executor - 도커 환경에서 코드 실행

기존 docker_execution.py를 리팩토링하여 CodeExecutor 인터페이스를 구현
"""

import docker
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..base import CodeExecutor, ExecutionResult, ExecutionConfig, ExecutionEnvironment


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


class DockerExecutor(CodeExecutor):
    """도커 환경에서 코드 실행"""
    
    def __init__(self, default_image: str = "csv-sandbox:test"):
        """도커 실행자 초기화
        
        Args:
            default_image: 기본 도커 이미지 이름
        """
        self.default_image = default_image
        self._client = None
    
    def _get_client(self):
        """도커 클라이언트 가져오기 (lazy initialization)"""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except Exception as e:
                raise RuntimeError(f"Docker 클라이언트 연결 실패: {str(e)}")
        return self._client
    
    def get_environment(self) -> ExecutionEnvironment:
        return ExecutionEnvironment.DOCKER
    
    def is_available(self) -> bool:
        """도커가 사용 가능한지 확인"""
        try:
            client = self._get_client()
            client.ping()
            return True
        except Exception:
            return False
    
    def validate_config(self, config: ExecutionConfig) -> tuple[bool, Optional[str]]:
        """도커 설정 검증"""
        if config.environment != ExecutionEnvironment.DOCKER:
            return False, "도커 실행자는 DOCKER 환경만 지원합니다."
        
        # 도커 이미지 확인
        docker_image = config.extra_config.get("docker_image", self.default_image)
        try:
            client = self._get_client()
            client.images.get(docker_image)
        except docker.errors.ImageNotFound:
            return False, f"Docker 이미지를 찾을 수 없습니다: {docker_image}"
        except Exception as e:
            return False, f"Docker 이미지 확인 실패: {str(e)}"
        
        return True, None
    
    def execute(
        self,
        code_file: Path,
        config: ExecutionConfig
    ) -> ExecutionResult:
        """도커에서 코드 실행"""
        start_time = time.time()
        
        try:
            client = self._get_client()
            docker_image = config.extra_config.get("docker_image", self.default_image)
            
            # 볼륨 마운트 설정 및 마운트 정보 수집
            volumes, mount_info = self._prepare_volumes(code_file, config)
            
            # 작업 디렉토리 설정
            working_dir = "/workspace/results" if config.output_directory else "/workspace/code"
            
            # 컨테이너 실행
            result = client.containers.run(
                docker_image,
                f"python /workspace/code/{code_file.name}",
                volumes=volumes,
                working_dir=working_dir,
                remove=True,
                stderr=True,
                stdout=True,
                mem_limit="512m",  # 512MB 메모리 제한
                nano_cpus=1_000_000_000,  # 1 CPU 제한
                pids_limit=100,  # 100 프로세스 제한
                network_mode="none",  # 네트워크 비활성화
            )
            
            stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            execution_time = time.time() - start_time
            
            # 출력 파일 수집
            output_files = self._collect_output_files(config.output_directory)
            
            return ExecutionResult(
                success=True,
                stdout=stdout,
                stderr="",
                exit_code=0,
                execution_time=execution_time,
                output_files=output_files,
                metadata={
                    "docker_image": docker_image,
                    "mount_info": mount_info
                }
            )
            
        except docker.errors.ContainerError as e:
            execution_time = time.time() - start_time
            try:
                stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else str(e)
                stdout = e.stdout.decode('utf-8') if hasattr(e, 'stdout') and e.stdout else ""
            except (AttributeError, UnicodeDecodeError):
                stderr = str(e)
                stdout = ""
            
            exit_code = e.exit_status if hasattr(e, 'exit_status') else -1
            
            # 마운트 정보 수집 (에러 발생 시에도 포함)
            try:
                _, mount_info = self._prepare_volumes(code_file, config)
            except Exception:
                mount_info = {}
            
            return ExecutionResult(
                success=False,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
                error=f"도커 컨테이너 실행 실패 (exit_code: {exit_code})",
                metadata={
                    "docker_image": config.extra_config.get("docker_image", self.default_image),
                    "mount_info": mount_info
                }
            )
            
        except docker.errors.ImageNotFound as e:
            execution_time = time.time() - start_time
            docker_image = config.extra_config.get("docker_image", self.default_image)
            return ExecutionResult(
                success=False,
                stderr="",
                exit_code=-1,
                execution_time=execution_time,
                error=f"Docker 이미지를 찾을 수 없습니다: {docker_image}",
                metadata={
                    "docker_image": docker_image,
                    "mount_info": {}
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            docker_image = config.extra_config.get("docker_image", self.default_image)
            return ExecutionResult(
                success=False,
                stderr="",
                exit_code=-1,
                execution_time=execution_time,
                error=f"도커 실행 중 오류 발생: {str(e)}",
                metadata={
                    "docker_image": docker_image,
                    "mount_info": {}
                }
            )
    
    def _prepare_volumes(
        self,
        code_file: Path,
        config: ExecutionConfig
    ) -> tuple[Dict[str, Dict[str, str]], Dict[str, str]]:
        """볼륨 마운트 준비 및 마운트 정보 생성

        Returns:
            (volumes, mount_info) 튜플
            - volumes: 도커 볼륨 마운트 설정
            - mount_info: 파일명 -> 도커 경로 매핑
        """
        # 코드 파일 경로를 절대 경로로 변환
        code_file = code_file.resolve()

        # 경로 검증
        if not _validate_mount_path(code_file.parent):
            raise ValueError(f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {code_file.parent}")

        volumes = {
            str(code_file.parent.resolve()): {"bind": "/workspace/code", "mode": "ro"}
        }
        
        # 마운트 정보: 파일명 -> 도커 경로 매핑
        mount_info: Dict[str, str] = {}
        
        # 코드 파일 자체도 마운트 정보에 포함
        mount_info[code_file.name] = f"/workspace/code/{code_file.name}"
        
        # 입력 파일 마운트 (CSV 파일 등)
        mounted_dirs = {}
        data_dir_index = 0
        
        if config.input_files:
            for input_file in config.input_files:
                input_path = Path(input_file).resolve()
                if input_path.exists():
                    # 경로 검증
                    if not _validate_mount_path(input_path.parent):
                        raise ValueError(f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {input_path.parent}")

                    parent = str(input_path.parent.resolve())
                    code_parent = str(code_file.parent.resolve())

                    # 같은 디렉토리면 코드 디렉토리에서 접근 가능
                    if parent == code_parent:
                        docker_path = f"/workspace/code/{input_path.name}"
                        mount_info[input_path.name] = docker_path
                        continue

                    # 이미 마운트된 디렉토리는 건너뛰기
                    if parent in mounted_dirs:
                        bind_path = mounted_dirs[parent]
                        docker_path = f"{bind_path}/{input_path.name}"
                        mount_info[input_path.name] = docker_path
                        continue

                    # 다른 디렉토리에 있으면 별도로 마운트
                    bind_path = f"/workspace/data_{data_dir_index}" if data_dir_index > 0 else "/workspace/data"
                    volumes[parent] = {"bind": bind_path, "mode": "ro"}
                    mounted_dirs[parent] = bind_path
                    docker_path = f"{bind_path}/{input_path.name}"
                    mount_info[input_path.name] = docker_path
                    print(f"🐳 도커 마운트: {parent} -> {bind_path}")
                    data_dir_index += 1
        
        # 출력 디렉토리 마운트
        if config.output_directory:
            output_path = Path(config.output_directory).expanduser().resolve()

            # 경로 검증
            if not _validate_mount_path(output_path):
                raise ValueError(f"보안 오류: 허용되지 않은 디렉토리 마운트 시도: {output_path}")

            output_path.mkdir(parents=True, exist_ok=True)
            volumes[str(output_path)] = {"bind": "/workspace/results", "mode": "rw"}
            mount_info["output_directory"] = "/workspace/results"
        
        return volumes, mount_info
    
    def _collect_output_files(self, output_dir: Optional[str]) -> List[str]:
        """출력 파일 수집"""
        if not output_dir:
            return []
        
        output_path = Path(output_dir)
        if not output_path.exists():
            return []
        
        return [str(f) for f in output_path.iterdir() if f.is_file()]

