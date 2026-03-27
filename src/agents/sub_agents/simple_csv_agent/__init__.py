"""
Simple CSV Analysis Agent 모듈

단순한 CSV 파일 분석 에이전트
- ollama:gpt-oss:120b-cloud 단일 모델 사용
- 코드 생성 → 실행 → 결과 분석 → 작업 완료
"""

from .agent import (
    create_simple_csv_agent,
    agent,
)
from .state import SimpleCSVState

__all__ = [
    "create_simple_csv_agent",
    "agent",
    "SimpleCSVState",
]




