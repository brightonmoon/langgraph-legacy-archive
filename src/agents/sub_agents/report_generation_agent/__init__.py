"""
Report Generation Agent - 보고서 생성 전용 서브 에이전트

다른 에이전트/도구들이 생성한 context를 받아서 보고서만 생성하는 특화 에이전트입니다.

핵심 특징:
- 독립적인 LLM 모델 사용 (router/orchestrator와 분리)
- Context 기반 보고서 생성 (다른 에이전트가 context 생성)
- 사전 정의된 prompt 템플릿 사용
- 토큰 사용 최소화 (보고서 생성만 담당)
"""

from .agent import create_report_generation_agent, agent

__all__ = ["create_report_generation_agent", "agent"]

