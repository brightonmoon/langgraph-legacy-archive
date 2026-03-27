"""
Code Execution Tools - 코드 실행 통합 도구

다양한 실행 환경(도커, 클라우드, 외부 등)을 지원하는 확장 가능한 코드 실행 시스템

주의: 이 모듈은 새로운 확장 가능한 코드 실행 시스템입니다.
기존 code_execution.py (execute_python_code_tool, execute_python_file_tool)는
별도로 유지되며 하위 호환성을 위해 계속 사용 가능합니다.
"""

from langchain.tools import tool
from .factory import CodeExecutionFactory
from .base import ExecutionEnvironment, ExecutionConfig, ExecutionResult
from .utils.result_formatter import format_execution_result
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys
import importlib.util

# 하위 호환성: 기존 code_execution.py 모듈에서 함수들 가져오기
# Python이 패키지를 우선하므로 명시적으로 모듈 파일을 import
_parent_dir = Path(__file__).parent.parent
_code_execution_module_path = _parent_dir / "code_execution.py"

if _code_execution_module_path.exists():
    spec = importlib.util.spec_from_file_location("code_execution_module", _code_execution_module_path)
    if spec and spec.loader:
        code_execution_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(code_execution_module)
        # 기존 함수들 재내보내기
        execute_python_code_tool = getattr(code_execution_module, "execute_python_code_tool", None)
        execute_python_file_tool = getattr(code_execution_module, "execute_python_file_tool", None)
    else:
        execute_python_code_tool = None
        execute_python_file_tool = None
else:
    execute_python_code_tool = None
    execute_python_file_tool = None


@tool("execute_code")
def execute_code_tool(
    code_file: str,
    environment: str = "docker",
    timeout: int = 30,
    input_files: Optional[List[str]] = None,
    output_directory: Optional[str] = None,
    **kwargs
) -> str:
    """코드를 다양한 환경에서 실행하는 통합 도구
    
    Args:
        code_file: 실행할 코드 파일 경로
        environment: 실행 환경 (docker, local, cloud, external)
        timeout: 실행 시간 제한 (초)
        input_files: 입력 파일 목록 (CSV 등)
        output_directory: 출력 디렉토리
        **kwargs: 실행 환경별 추가 설정
                 - docker_image: 도커 이미지 (도커 환경)
                 - api_endpoint: API 엔드포인트 (클라우드 환경)
                 - execution_command: 실행 명령어 (외부 환경)
    
    Returns:
        실행 결과 문자열 (포맷팅된 stdout + stderr)
    """
    try:
        # 실행 환경 타입 변환
        try:
            env = ExecutionEnvironment(environment.lower())
        except ValueError:
            available = ", ".join([e.value for e in ExecutionEnvironment])
            return f"❌ 잘못된 실행 환경: {environment}. 지원 환경: {available}"
        
        # 실행자 생성
        executor = CodeExecutionFactory.create_executor(env, **kwargs)
        
        # 설정 생성
        config = ExecutionConfig(
            environment=env,
            timeout=timeout,
            input_files=input_files,
            output_directory=output_directory
        )
        
        # 설정 검증
        is_valid, error_msg = executor.validate_config(config)
        if not is_valid:
            return f"❌ 설정 검증 실패: {error_msg}"
        
        # 코드 파일 경로 확인
        code_path = Path(code_file)
        if not code_path.exists():
            return f"❌ 코드 파일이 존재하지 않습니다: {code_file}"
        
        # 코드 실행
        result = executor.execute(code_path, config)
        
        # 결과 포맷팅
        return format_execution_result(result)
        
    except Exception as e:
        return f"❌ 코드 실행 중 오류 발생: {str(e)}"


# 편의 함수들
def execute_code_in_docker(
    code_file: str,
    docker_image: str = "csv-sandbox:test",
    input_files: Optional[List[str]] = None,
    output_directory: Optional[str] = None,
    timeout: int = 30
) -> ExecutionResult:
    """도커에서 코드 실행 (편의 함수)
    
    Args:
        code_file: 실행할 코드 파일 경로
        docker_image: 도커 이미지 이름
        input_files: 입력 파일 목록
        output_directory: 출력 디렉토리
        timeout: 실행 시간 제한
        
    Returns:
        ExecutionResult: 실행 결과
    """
    executor = CodeExecutionFactory.create_executor(
        ExecutionEnvironment.DOCKER,
        docker_image=docker_image
    )
    
    config = ExecutionConfig(
        environment=ExecutionEnvironment.DOCKER,
        timeout=timeout,
        input_files=input_files,
        output_directory=output_directory,
        docker_image=docker_image
    )
    
    return executor.execute(Path(code_file), config)


def execute_code_locally(
    code_file: str,
    timeout: int = 30,
    working_directory: Optional[str] = None,
    output_directory: Optional[str] = None
) -> ExecutionResult:
    """로컬에서 코드 실행 (편의 함수)
    
    ⚠️ DEPRECATED: LocalExecutor가 제거되었습니다.
    이 함수는 Docker로 리다이렉트됩니다.
    
    Args:
        code_file: 실행할 코드 파일 경로
        timeout: 실행 시간 제한
        working_directory: 작업 디렉토리
        output_directory: 출력 디렉토리
        
    Returns:
        ExecutionResult: 실행 결과 (Docker에서 실행됨)
    """
    # Docker로 리다이렉트 (격리된 환경 필요)
    return execute_code_in_docker(
        code_file=code_file,
        timeout=timeout,
        output_directory=output_directory
    )


def execute_code_in_ipython(
    code_file: str,
    session_id: Optional[str] = None,
    timeout: int = 60,
    working_directory: Optional[str] = None,
    output_directory: Optional[str] = None,
    docker_image: str = "csv-sandbox:test"
) -> ExecutionResult:
    """IPython에서 코드 실행 (편의 함수)
    
    ⚠️ DEPRECATED: DockerExecutor를 사용합니다.
    격리된 환경에서 실행하기 위해 Docker 세션 모드를 사용합니다.
    
    Args:
        code_file: 실행할 코드 파일 경로
        session_id: 세션 ID (None이면 새로 생성, 같은 ID면 세션 유지)
        timeout: 실행 시간 제한 (기본값: 60초)
        working_directory: 작업 디렉토리 (무시됨, Docker 내부에서 처리)
        output_directory: 출력 디렉토리
        docker_image: Docker 이미지 이름
        
    Returns:
        ExecutionResult: 실행 결과 (metadata에 session_id와 visualizations 포함)
    """
    # DockerExecutor로 리다이렉트 (격리된 환경)
    return execute_code_interactive(
        code_file=code_file,
        session_id=session_id,
        docker_image=docker_image,
        output_directory=output_directory,
        timeout=timeout
    )


def execute_code_in_repl(
    code_file: str,
    session_id: Optional[str] = None,
    timeout: int = 30,
    working_directory: Optional[str] = None,
    output_directory: Optional[str] = None,
    docker_image: str = "csv-sandbox:test"
) -> ExecutionResult:
    """REPL 세션에서 코드 실행 (편의 함수)
    
    참고: 세션 관리 기능이 제거되었습니다. 각 실행은 독립적인 Docker 컨테이너에서 수행됩니다.
    session_id 파라미터는 하위 호환성을 위해 유지되지만 사용되지 않습니다.
    
    Args:
        code_file: 실행할 코드 파일 경로
        session_id: 세션 ID (하위 호환성용, 사용되지 않음)
        timeout: 실행 시간 제한
        working_directory: 작업 디렉토리 (무시됨, Docker 내부에서 처리)
        output_directory: 출력 디렉토리
        docker_image: Docker 이미지 이름
        
    Returns:
        ExecutionResult: 실행 결과
    """
    return execute_code_interactive(
        code_file=code_file,
        session_id=session_id,
        docker_image=docker_image,
        output_directory=output_directory,
        timeout=timeout
    )


def execute_code_interactive(
    code_file: str,
    session_id: Optional[str] = None,
    docker_image: str = "csv-sandbox:test",
    input_files: Optional[List[str]] = None,
    output_directory: Optional[str] = None,
    timeout: int = 60
) -> ExecutionResult:
    """대화형 모드: Docker에서 코드 실행 (편의 함수)
    
    참고: 세션 관리 기능이 제거되었습니다. 각 실행은 독립적인 Docker 컨테이너에서 수행됩니다.
    session_id 파라미터는 하위 호환성을 위해 유지되지만 사용되지 않습니다.
    
    Args:
        code_file: 실행할 코드 파일 경로
        session_id: 세션 ID (하위 호환성용, 사용되지 않음)
        docker_image: Docker 이미지 이름
        input_files: 입력 파일 목록 (CSV 등)
        output_directory: 출력 디렉토리
        timeout: 실행 시간 제한
        
    Returns:
        ExecutionResult: 실행 결과
    """
    from .executors.docker_executor import DockerExecutor
    
    executor = DockerExecutor(default_image=docker_image)
    
    config = ExecutionConfig(
        environment=ExecutionEnvironment.DOCKER,
        timeout=timeout,
        input_files=input_files,
        output_directory=output_directory,
        docker_image=docker_image
    )
    
    return executor.execute(Path(code_file), config)


# 하위 호환성을 위한 함수 (기존 코드와의 호환성 유지)
def execute_code_in_docker_sandbox(
    code_file: Path,
    csv_file=None,
    csv_files=None,
    output_dir=None,
    image: str = "csv-sandbox:test"
) -> Dict[str, Any]:
    """기존 docker_execution.py와의 호환성을 위한 래퍼 함수
    
    Deprecated: execute_code_in_docker() 사용 권장
    """
    input_files = []
    if csv_files:
        input_files.extend([str(f) for f in csv_files if f])
    elif csv_file:
        input_files.append(str(csv_file))
    
    result = execute_code_in_docker(
        code_file=str(code_file),
        docker_image=image,
        input_files=input_files if input_files else None,
        output_directory=str(output_dir) if output_dir else None
    )
    
    # 기존 형식으로 변환
    return result.to_dict()


__all__ = [
    "execute_code_tool",
    "execute_code_in_docker",  # 배치 모드
    "execute_code_interactive",  # 대화형 모드 (세션 유지, 권장)
    "execute_code_locally",  # deprecated: Docker로 리다이렉트
    "execute_code_in_ipython",  # deprecated: DockerExecutor 사용
    "execute_code_in_repl",  # deprecated: DockerExecutor 사용
    "execute_code_in_docker_sandbox",  # 하위 호환성
    "execute_python_code_tool",  # 하위 호환성: 기존 code_execution.py에서
    "execute_python_file_tool",  # 하위 호환성: 기존 code_execution.py에서
    "CodeExecutionFactory",
    "ExecutionEnvironment",
    "ExecutionConfig",
    "ExecutionResult",
]

