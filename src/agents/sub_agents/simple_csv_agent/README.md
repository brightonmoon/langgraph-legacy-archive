# Simple CSV Analysis Agent

단순한 CSV 파일 분석 서브에이전트

## 목적

- ollama:gpt-oss:120b-cloud 단일 모델 사용
- CSV 파일 분석 워크플로우 테스트
- 코드 생성 → 실행 → 결과 분석 → 작업 완료 과정 검증

## 구조

```
simple_csv_agent/
├── __init__.py      # 모듈 초기화
├── agent.py         # 메인 에이전트 구현
├── state.py         # State 정의
└── README.md        # 이 파일
```

## 워크플로우

1. **read_csv_metadata**: CSV 파일 메타데이터 읽기
2. **generate_code**: 데이터 분석 코드 생성 (ollama:gpt-oss:120b-cloud)
3. **execute_code**: 가상환경(.venv)에서 코드 직접 실행
4. **analyze_result**: 결과 분석 및 재시도 여부 결정
   - 오류 발생 시 최대 3회까지 재시도
   - 성공 시 최종 결과 반환

## 사용 방법

```python
from src.agents.sub_agents.simple_csv_agent import create_simple_csv_agent
from langchain.messages import HumanMessage

# 에이전트 생성
agent = create_simple_csv_agent(
    model="ollama:gpt-oss:120b-cloud",
    max_iterations=3
)

# 초기 상태 설정
initial_state = {
    "messages": [HumanMessage(content="test_data.csv 파일을 분석하세요.")],
    "csv_file_path": "test_data.csv",
    "max_iterations": 3,
    "iteration_count": 0
}

# Checkpointer 사용 시 thread_id 필요
config = {"configurable": {"thread_id": "test_session"}}

# 에이전트 실행
for state in agent.stream(initial_state, config=config):
    for node_name, node_state in state.items():
        print(f"[{node_name}] 상태: {node_state.get('status')}")
        if "final_result" in node_state:
            print(node_state["final_result"])
```

## 테스트

```bash
cd /home/doyamoon/agentic_ai
source .venv/bin/activate
uv run tests/test_simple_csv_agent.py
```

## 특징

- **단순한 구조**: 복잡한 로직 없이 핵심 워크플로우만 구현
- **단일 모델**: ollama:gpt-oss:120b-cloud 하나만 사용
- **자동 재시도**: 오류 발생 시 최대 3회까지 자동 재시도
- **상태 관리**: LangGraph Checkpointer를 통한 상태 지속성

## 주의사항

- 가상환경(.venv)이 필요합니다 (코드 실행용)
- CSV 파일은 `data/` 디렉토리에 있어야 합니다
- OLLAMA_API_KEY 환경변수가 설정되어 있어야 합니다
- 코드 생성 시 pandas, numpy만 사용 (matplotlib, seaborn은 사용하지 않음)

