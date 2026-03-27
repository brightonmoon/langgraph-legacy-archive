# Agentic AI - LangChain & LangGraph Agent 시스템

> ⚠️ **프로젝트 상태**: 이 프로젝트는 Langchain/Langgraph 프레임워크의 한계로 인해 개발이 중단된 레거시 아카이브입니다.

LangChain과 LangGraph를 사용한 모듈화된 Agent 시스템입니다.

## 프로젝트 구조

```
src/
├── agents/          # Agent 모듈 (main agent, sub-agents, study 코드)
│   ├── agent.py     # 메인 Agent
│   ├── base.py      # BaseAgent 인터페이스
│   ├── factory.py   # Agent 팩토리
│   ├── sub_agents/  # Sub-agent 모듈 (8개)
│   └── study/       # 학습/실험용 Agent 패턴 코드 (README 참조)
├── tools/           # 도구 모듈 (calculator, brave_search, code_execution 등)
├── utils/           # 유틸리티 (config, errors, paths, token_tracker)
└── mcp/             # MCP (Model Context Protocol) 모듈

tests/               # 테스트 코드 (agents, csv, docker, rag 등 9개 카테고리)
archive/             # 이전 deepagent 실험 코드 (README 참조)
docs/                # 참고 문서
```

## 설치

```bash
# uv 사용
uv sync

# 환경변수 설정
cp env_example.txt .env
# .env 파일에 OLLAMA_API_KEY 등 설정
```

## Agent 타입 요약

| Agent | 패턴 | 핵심 기능 |
|-------|------|-----------|
| Basic | LangChain 기본 | 단순 질문-답변 |
| LangGraph | StateGraph | 노드 기반 워크플로우 |
| LangGraph Tools | StateGraph + Tool Calling | 도구 통합 (계산기, 웹 검색) |
| LangGraph MCP | StateGraph + MCP | 동적 도구 로딩 |
| Chaining | Prompt Chaining | Gate function 검증, 다단계 개선 |
| Parallel | Parallelization | 병렬 처리 후 결과 통합 |
| Coding | Orchestrator-Worker | 대형 모델(분석) + 소형 모델(코딩) |
| Multiple Workers | Orchestrator-Multi Worker | 병렬 생성 → 품질 평가 → 최적 선택 |

## 사용법

```bash
# CLI 실행
uv run cli.py
```

```python
from src.agents.factory import AgentFactory

agent = AgentFactory.create_agent("langgraph_tools")
response = agent.generate_response("질문")
```
