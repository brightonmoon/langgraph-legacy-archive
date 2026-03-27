"""
Code Execution Executors - 실행 환경별 구현

Docker 중심 아키텍처:
- DockerExecutor: Docker 컨테이너에서 코드 실행 (일회성 실행)

참고: 세션 관리 기능이 제거되었습니다. 각 실행은 독립적인 컨테이너에서 수행됩니다.

로컬 환경 실행자 제거:
- REPLExecutor, IPythonExecutor, IPythonSessionExecutor 제거됨
  (격리되지 않은 로컬 환경 실행은 보안상 위험)
- DockerSessionExecutor 제거됨 (세션 관리 불필요)
"""

from .docker_executor import DockerExecutor

__all__ = [
    "DockerExecutor",  # Docker 컨테이너 실행
]

