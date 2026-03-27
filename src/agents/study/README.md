# Study Agents (학습/실험용 Agent 코드)

> ⚠️ **주의**: 이 디렉토리의 코드는 **학습 및 실험 목적**으로 작성되었으며, 프로덕션에서 사용되지 않습니다.
> Langchain/Langgraph 프레임워크의 다양한 패턴을 실험하기 위한 참고 코드입니다.

## 파일 목록 및 학습 포인트

| 파일 | 패턴 | 핵심 학습 내용 |
|------|------|----------------|
| `basic_agent.py` | 기본 LangChain | 가장 단순한 Agent 구조: `SystemMessage` + `HumanMessage` → `model.invoke()` |
| `langgraph_agent.py` | LangGraph StateGraph | 노드 기반 워크플로우: `input_processor → llm_call → response_formatter` |
| `langgraph_agent_tools.py` | StateGraph + Tool Calling | `model.bind_tools()` 패턴, 조건부 분기(`should_continue`), Checkpointer |
| `langgraph_agent_mcp.py` | StateGraph + MCP | MCP 서버 통합, 로컬/MCP 도구 분류 및 동적 로딩 |
| `langgraph_agent_tools_middleware.py` | StateGraph + Middleware | Logging/RateLimiting 미들웨어 패턴, `astream_events` 토큰 스트리밍 |
| `langgraph_agent_chaining.py` | Prompt Chaining | Gate function 검증, 조건부 라우팅으로 다단계 개선 워크플로우 |
| `langgraph_agent_parallel.py` | Parallelization | START에서 3개 노드 동시 분기 → Aggregator 통합 패턴 |
| `coding_agent.py` | Orchestrator-Worker | 대형 모델(분석) + 소형 모델(코딩), 에러 기반 자동 재시도 루프 |
| `cursor_style_agent.py` | LangGraph + Interrupt (HITL) | `interrupt()` 기반 실시간 권한 요청, `Command(resume=...)` 재개 패턴 |
| `multiple_workers_coding_agent.py` | Multiple Workers | 2개 Worker 병렬 생성 → Orchestrator 품질 평가 → 최적 선택 패턴 |

## 관련 프레임워크 한계점 (개발 중단 이유)

- LangGraph의 State 관리 복잡성이 실제 프로덕션 수준에서 지나치게 높아짐
- Sub-agent 구성 시 Checkpointer/MemorySaver 의존성 문제
- MCP 통합 시 async/sync 이벤트 루프 충돌
- Tool calling의 불안정한 JSON 파싱 및 에러 핸들링
