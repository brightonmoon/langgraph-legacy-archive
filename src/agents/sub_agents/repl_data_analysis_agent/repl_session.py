"""
REPL 세션 관리 모듈

Python REPL 세션의 상태를 유지하고 관리하는 모듈입니다.
세션 기반으로 변수, 임포트, 실행 히스토리를 유지합니다.

주의: 이 모듈은 하위 호환성을 위해 유지되며, 내부적으로는
새로운 통합 코드 실행 시스템(src.tools.code_execution)을 사용합니다.

참고: 세션 관리 기능이 제거되었으며, 각 실행은 독립적인 Docker 컨테이너에서 수행됩니다.
"""

import uuid
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 새로운 통합 시스템 사용
from src.tools.code_execution.executors.docker_executor import DockerExecutor
from src.tools.code_execution.base import ExecutionConfig, ExecutionEnvironment
from src.utils.paths import get_workspace_subdirectories


class REPLSession:
    """REPL 세션 관리 클래스
    
    세션 기반으로 Python 코드 실행 상태를 유지합니다.
    - 실행 히스토리 관리
    - 출력 누적
    
    내부적으로 DockerExecutor를 사용하여 격리된 환경에서 실행합니다.
    각 실행은 독립적인 컨테이너에서 수행되며, 변수 상태는 유지되지 않습니다.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """REPL 세션 초기화
        
        Args:
            session_id: 세션 ID (None이면 새로 생성, 현재는 히스토리 추적용으로만 사용)
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.executor = DockerExecutor()
        self.variables: Dict[str, Any] = {}  # 하위 호환성 (사용되지 않음)
        self.imports: List[str] = []  # 하위 호환성 (사용되지 않음)
        self.created_at = datetime.now()
        self.history: List[str] = []  # 실행 히스토리
        self._accumulated_output: str = ""  # 누적된 출력
    
    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """코드를 독립적인 Docker 컨테이너에서 실행
        
        각 실행은 독립적인 Docker 컨테이너에서 수행되며,
        이전 실행의 변수나 상태는 유지되지 않습니다.
        
        Args:
            code: 실행할 Python 코드
            timeout: 실행 시간 제한 (초)
            
        Returns:
            실행 결과 딕셔너리 (success, error, stdout, stderr, return_code)
        """
        try:
            # 임시 파일로 코드 저장
            directories = get_workspace_subdirectories()
            temp_dir = directories.get("generated_code", Path("/tmp"))
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            temp_file = temp_dir / f"repl_code_{self.session_id}_{os.getpid()}.py"
            temp_file.write_text(code, encoding='utf-8')
            
            # 실행 설정 생성
            config = ExecutionConfig(
                environment=ExecutionEnvironment.DOCKER,
                timeout=timeout,
                extra_config={
                    "docker_image": "csv-sandbox:test"
                }
            )
            
            # 코드 실행 (독립적인 컨테이너에서)
            result = self.executor.execute(temp_file, config)
            
            # 히스토리 및 출력 누적
            self.history.append(code)
            if result.stdout:
                self._accumulated_output += result.stdout + "\n"
            if result.stderr:
                self._accumulated_output += result.stderr + "\n"
            
            # 임시 파일 정리
            try:
                temp_file.unlink()
            except Exception:
                pass
            
            # 하위 호환성을 위해 기존 형식으로 변환
            return {
                "success": result.success,
                "error": result.error,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.exit_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    def get_accumulated_output(self) -> str:
        """누적된 출력 반환
        
        Returns:
            누적된 출력 문자열
        """
        return self._accumulated_output
    
    def reset(self):
        """세션 초기화 (히스토리만 초기화)"""
        self.variables.clear()
        self.imports.clear()
        self.history.clear()
        self._accumulated_output = ""
        # 참고: 각 실행은 독립적인 컨테이너에서 수행되므로 별도 정리 불필요


# 전역 세션 저장소 (래퍼 클래스용, 하위 호환성)
_sessions: Dict[str, REPLSession] = {}


def get_or_create_session(session_id: Optional[str] = None) -> REPLSession:
    """세션 가져오기 또는 생성 (하위 호환성 래퍼)
    
    내부적으로 새로운 통합 시스템을 사용합니다.
    
    Args:
        session_id: 세션 ID (None이면 새로 생성)
        
    Returns:
        REPLSession 인스턴스 (래퍼)
    """
    # 세션 ID로 기존 래퍼 찾기
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    
    # 새 래퍼 생성
    session = REPLSession(session_id)
    _sessions[session.session_id] = session
    return session


def cleanup_session(session_id: str):
    """세션 정리 (하위 호환성)
    
    참고: 세션 관리 기능이 제거되어 각 실행은 독립적인 컨테이너에서 수행됩니다.
    이 함수는 래퍼 세션만 정리합니다.
    
    Args:
        session_id: 정리할 세션 ID
    """
    if session_id in _sessions:
        del _sessions[session_id]

