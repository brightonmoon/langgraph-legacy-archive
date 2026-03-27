"""
Code Execution Utils - 유틸리티 함수

Docker 중심 아키텍처에 맞춘 유틸리티 모듈
- 로컬 실행 관련 유틸리티 제거됨 (subprocess_runner, path_validator, security)
- Docker 환경에서는 불필요한 로컬 경로 검증 및 subprocess 실행 제거
"""

from .result_formatter import (
    format_execution_result,
    format_simple_result
)
from .context_extractor import extract_context_from_result

__all__ = [
    # 결과 포맷팅
    "format_execution_result",
    "format_simple_result",
    # Context 추출
    "extract_context_from_result",
]

