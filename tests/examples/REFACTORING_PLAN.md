# Examples 디렉토리 리팩토링 플랜

## 현재 상태 분석

- **리팩토링 완료일**: 2026-02-04
- **상태**: 완료

## 완료된 작업

### Phase 1: 기반 구조 설정

#### 1.1 공통 유틸리티 모듈 생성

```
tests/examples/
├── __init__.py
├── _utils/
│   ├── __init__.py
│   ├── paths.py          # 경로 설정 (sys.path 조작 대체)
│   ├── display.py        # 출력 포맷팅 헬퍼
│   └── runner.py         # 예제 실행 공통 패턴
└── ...
```

#### 1.2 `_utils/paths.py`
- 프로젝트 루트 자동 설정
- sys.path 조작 코드 중앙화
- 테스트 데이터 디렉토리 헬퍼 함수 제공

#### 1.3 `_utils/display.py`
- `print_header()`: 헤더 출력
- `print_section()`: 섹션 제목 출력
- `print_result()`: 라벨-값 쌍 출력
- `print_separator()`: 구분선 출력
- `print_agent_info()`: Agent 정보 출력
- `print_success/error/warning/info()`: 상태 메시지 출력

#### 1.4 `_utils/runner.py`
- `@run_example()`: 동기 예제 실행 데코레이터
- `@run_async_example()`: 비동기 예제 실행 데코레이터
- `run_test_cases()`: 테스트 케이스 실행 헬퍼
- `check_agent_ready()`: Agent 준비 상태 확인

### Phase 2: 파일 정리 및 리네이밍

#### 2.1 새로운 디렉토리 구조

```
tests/examples/
├── __init__.py               # 패키지 설명
├── REFACTORING_PLAN.md       # 리팩토링 문서
├── _utils/                   # 공통 유틸리티
│   ├── __init__.py
│   ├── paths.py
│   ├── display.py
│   └── runner.py
├── patterns/                 # LangGraph 패턴 예제
│   ├── __init__.py
│   ├── parallel_demo.py
│   ├── chaining_demo.py
│   └── checkpointer_demo.py
├── agents/                   # Agent 유형별 예제
│   ├── __init__.py
│   ├── cursor_style_demo.py
│   ├── mcp_agent_demo.py
│   └── deepagent_subagents_demo.py
├── data_analysis/            # 데이터 분석 예제
│   ├── __init__.py
│   └── csv_basic_demo.py
├── tools/                    # 도구 사용 예제
│   ├── __init__.py
│   ├── brave_search_demo.py
│   └── structured_output_demo.py
└── studio/                   # LangGraph Studio 관련
    ├── __init__.py
    ├── code_generation_agent_studio_examples.json
    ├── langgraph_studio_input_examples.json
    └── repl_data_analysis_agent_studio_examples.json
```

### Phase 3: 코드 리팩토링

#### 3.1 각 파일 리팩토링 완료 항목
- [x] sys.path 조작 코드 제거 → `from examples._utils import PROJECT_ROOT` 로 대체
- [x] 출력 코드 리팩토링 → `display` 유틸리티 사용
- [x] 메인 함수 패턴 통일 → `@run_example` 데코레이터 사용
- [x] 에러 핸들링 표준화
- [x] 독스트링 정리

---

## 작업 체크리스트

- [x] Phase 1: 기반 구조
  - [x] `_utils/` 디렉토리 생성
  - [x] `paths.py` 작성
  - [x] `display.py` 작성
  - [x] `runner.py` 작성
  - [x] `__init__.py` 파일들 생성

- [x] Phase 2: 파일 정리
  - [x] 카테고리 디렉토리 생성 (patterns/, agents/, data_analysis/, tools/, studio/)
  - [x] 파일 이동 및 리네이밍
  - [x] JSON 파일 studio/ 디렉토리로 이동

- [x] Phase 3: 코드 리팩토링
  - [x] `patterns/` 예제 리팩토링 (3개 파일)
  - [x] `agents/` 예제 리팩토링 (3개 파일)
  - [x] `data_analysis/` 예제 리팩토링 (1개 파일)
  - [x] `tools/` 예제 리팩토링 (2개 파일)

---

## 사용 방법

### 예제 실행

```bash
# patterns 예제
python -m examples.patterns.parallel_demo
python -m examples.patterns.chaining_demo
python -m examples.patterns.checkpointer_demo

# agents 예제
python -m examples.agents.cursor_style_demo
python -m examples.agents.mcp_agent_demo
python -m examples.agents.deepagent_subagents_demo

# data_analysis 예제
python -m examples.data_analysis.csv_basic_demo

# tools 예제
python -m examples.tools.brave_search_demo
python -m examples.tools.structured_output_demo
```

### 새 예제 작성 가이드

```python
"""새 예제 파일 템플릿"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_success,
    print_error,
    run_example,
    check_agent_ready,
)

from src.agents.your_agent import YourAgent


@run_example("예제 이름")
def main():
    """예제 실행"""
    agent = YourAgent()

    if not check_agent_ready(agent):
        return

    # 예제 로직
    print_section("테스트 실행")
    # ...


if __name__ == "__main__":
    main()
```

---

*Completed: 2026-02-04*
