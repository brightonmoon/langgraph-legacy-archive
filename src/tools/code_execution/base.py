"""
Code Execution Base - 코드 실행 기본 인터페이스 및 추상 클래스

다양한 실행 환경(도커, 클라우드, 외부 등)을 지원하는 확장 가능한 코드 실행 시스템의 기본 구조
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum
from datetime import datetime


class ExecutionEnvironment(str, Enum):
    """실행 환경 타입"""
    DOCKER = "docker"
    LOCAL = "local"
    IPYTHON = "ipython"
    REPL = "repl"
    CLOUD = "cloud"
    EXTERNAL = "external"
    REMOTE = "remote"


class ExecutionResult:
    """실행 결과 표준 형식"""
    
    def __init__(
        self,
        success: bool,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        execution_time: float = 0.0,
        output_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time = execution_time
        self.output_files = output_files or []
        self.metadata = metadata or {}
        self.error = error
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "output_files": self.output_files,
            "metadata": self.metadata,
            "error": self.error,
            "timestamp": self.timestamp
        }
    
    def __repr__(self) -> str:
        status = "✅ 성공" if self.success else "❌ 실패"
        return f"ExecutionResult({status}, exit_code={self.exit_code}, time={self.execution_time:.2f}s)"


class ExecutionConfig:
    """실행 환경 설정"""
    
    def __init__(
        self,
        environment: ExecutionEnvironment,
        timeout: int = 30,
        working_directory: Optional[str] = None,
        input_files: Optional[List[str]] = None,
        output_directory: Optional[str] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        self.environment = environment
        self.timeout = timeout
        self.working_directory = working_directory
        self.input_files = input_files or []
        self.output_directory = output_directory
        self.environment_vars = environment_vars or {}
        self.extra_config = kwargs  # 환경별 추가 설정
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "environment": self.environment.value,
            "timeout": self.timeout,
            "working_directory": self.working_directory,
            "input_files": self.input_files,
            "output_directory": self.output_directory,
            "environment_vars": self.environment_vars,
            "extra_config": self.extra_config
        }


class CodeExecutor(ABC):
    """코드 실행자 추상 클래스
    
    모든 실행 환경은 이 인터페이스를 구현해야 합니다.
    """
    
    @abstractmethod
    def execute(
        self,
        code_file: Path,
        config: ExecutionConfig
    ) -> ExecutionResult:
        """코드를 실행하고 결과를 반환
        
        Args:
            code_file: 실행할 코드 파일 경로
            config: 실행 환경 설정
            
        Returns:
            ExecutionResult: 실행 결과
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: ExecutionConfig) -> tuple[bool, Optional[str]]:
        """실행 환경 설정 검증
        
        Args:
            config: 검증할 설정
            
        Returns:
            (is_valid, error_message) 튜플
            - is_valid: 설정이 유효한지 여부
            - error_message: 오류 메시지 (유효하지 않은 경우)
        """
        pass
    
    @abstractmethod
    def get_environment(self) -> ExecutionEnvironment:
        """지원하는 실행 환경 반환"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """실행 환경이 사용 가능한지 확인
        
        Returns:
            사용 가능하면 True, 아니면 False
        """
        pass

