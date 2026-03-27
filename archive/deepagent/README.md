# DeepAgent 라이브러리 구현

LangChain의 `deepagents` 패키지를 사용하여 복잡한 멀티 스텝 작업을 처리하는 고급 에이전트를 구현합니다.

## 📋 개요

이 디렉토리는 `deepagents` 라이브러리를 사용하는 독립적인 구현입니다. `src/agents/deep_agent.py`와 달리 LangGraph를 직접 사용하지 않고, `deepagents` 패키지의 추상화된 API를 사용합니다.

## 🎯 주요 특징

### DeepAgents 라이브러리의 자동 제공 기능

1. **Planning (작업 분해)**
   - `write_todos` 도구: 복잡한 작업을 하위 작업으로 자동 분해
   - 작업 진행 상황 추적
   - **Plan Persistence (Offload Context)**: 
     - `save_plan`: Plan을 MD 파일로 저장 (세션 간 공유)
     - `load_plan`: MD 파일에서 plan 로드 (이전 세션 계속)
     - `format_plan`: write_todos 결과를 마크다운 형식으로 변환
     - Manus, Anthropic 등에서 사용하는 offload context 패턴 구현

2. **File System (파일 시스템)**
   - `ls`: 디렉토리 목록 조회
   - `read_file`: 파일 읽기
   - `write_file`: 파일 쓰기
   - `edit_file`: 파일 편집
   - LangGraph Store를 통한 자동 컨텍스트 관리

3. **CSV 멀티 에이전트 플로우**
   - 큰 CSV 파일(30개 컬럼, 18000개 행 이상) 효율적 분석
   - 토큰 제한을 고려한 청크 단위 처리
   - CSV 분석 subagent (qwen-coder) + 보고서 작성 subagent
   - 메인 에이전트 (gpt-oss)가 작업 조율

4. **Subagents (서브에이전트)**
   - `task` 도구: 특정 작업을 수행하는 서브에이전트 생성
   - 컨텍스트 격리 및 병렬 실행 지원

5. **Middleware Architecture**
   - 자동 컨텍스트 관리
   - 대화 요약 및 최적화
   - Guardrails 및 보안 기능

## 🚀 빠른 시작

### 1. 환경 설정

`.env` 파일에 필요한 API 키를 설정하세요:

```bash
# Ollama 사용 시
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_MODEL_NAME=gpt-oss:120b-cloud

# 또는 Anthropic 사용 시
ANTHROPIC_API_KEY=your_anthropic_api_key

# 또는 OpenAI 사용 시
OPENAI_API_KEY=your_openai_api_key

# 인터넷 검색 도구 사용 시 (선택사항)
BRAVE_API_KEY=your_brave_api_key
```

### 2. 기본 실행

```bash
# 대화형 모드
uv run deepagent/run.py

# 특정 쿼리 실행
uv run deepagent/run.py --query "LangGraph란 무엇인가요?"

# Ollama 모델 사용 안 함 (기본 Claude 사용)
uv run deepagent/run.py --no-ollama

# 인터넷 검색 도구 포함
uv run deepagent/run.py --with-search
```

### 3. 테스트 실행

```bash
uv run deepagent/test.py
```

## 📁 파일 구조

```
deepagent/
├── __init__.py          # 패키지 초기화
├── agent.py            # DeepAgentLibrary 클래스 (메인 구현)
├── tools.py            # 커스텀 도구들 (CSV 도구 포함)
├── csv_multi_agent.py  # CSV 멀티 에이전트 플로우
├── run.py              # 실행 스크립트
├── test.py             # 테스트 스크립트
└── README.md           # 이 문서
```

## 💻 사용 예제

### 예제 1: 기본 사용

```python
from deepagent.agent import DeepAgentLibrary

# 에이전트 생성
agent = DeepAgentLibrary(use_ollama=True)

# 쿼리 실행
result = agent.invoke("웹 애플리케이션 개발 계획을 세워주세요.")

# 대화형 모드
agent.chat()
```

### 예제 2: 커스텀 도구 포함

```python
from deepagent.agent import DeepAgentLibrary
from deepagent.tools import create_brave_search_tool

# 검색 도구 생성
search_tool = create_brave_search_tool()

# 에이전트 생성 (검색 도구 포함)
agent = DeepAgentLibrary(
    tools=[search_tool] if search_tool else None,
    system_prompt="당신은 전문 연구원입니다."
)

# 연구 쿼리 실행
result = agent.invoke("최신 AI 트렌드에 대해 조사해주세요.")
```

### 예제 3: 특정 모델 사용

```python
from deepagent.agent import DeepAgentLibrary

# Claude 모델 사용
agent = DeepAgentLibrary(
    model="anthropic:claude-sonnet-4-5-20250929",
    use_ollama=False
)

# 또는 Ollama 모델 지정
agent = DeepAgentLibrary(
    model="ollama:gpt-oss:120b-cloud",
    use_ollama=True
)
```

### 예제 4: Plan 저장/로드 (Offload Context)

```python
from deepagent.agent import DeepAgentLibrary

# 에이전트 생성
agent = DeepAgentLibrary()

# 복잡한 작업 계획 및 저장
query = """
복잡한 웹 애플리케이션 개발 작업을 계획하고 plan.md 파일로 저장하세요.
1. write_todos 도구로 작업을 분해하세요
2. format_plan 도구로 마크다운 형식으로 변환하세요
3. save_plan 도구로 plan.md 파일로 저장하세요
"""
result = agent.invoke(query)

# 이전 세션의 plan 계속하기
query2 = """
plan.md 파일을 불러와서 작업을 계속하세요.
1. load_plan 도구로 plan.md 파일을 읽으세요
2. 읽은 plan을 바탕으로 작업을 진행하세요
"""
result2 = agent.invoke(query2)
```

**Plan Persistence의 장점:**
- 세션 간 plan 공유 가능
- 컨텍스트 오프로드로 토큰 제한 회피
- Plan을 사람이 읽기 쉬운 형식으로 저장
- Git 등으로 버전 관리 가능

### 예제 5: CSV 멀티 에이전트 플로우

```python
from deepagent.csv_multi_agent import create_csv_analysis_agent

# CSV 분석 멀티 에이전트 생성
agent = create_csv_analysis_agent(
    main_model="ollama:gpt-oss:120b-cloud",  # 메인 에이전트
    csv_analyzer_model="ollama:qwen2.5-coder:latest"  # CSV 분석 subagent
)

# 큰 CSV 파일 분석 요청
result = agent.invoke({
    "messages": [{"role": "user", "content": "tests/DESeq2_counts.csv 파일을 분석해주세요"}]
})
```

**플로우:**
1. 메인 에이전트 (gpt-oss) → 작업 분석 및 위임
2. CSV 분석 subagent (qwen-coder) → 큰 파일을 토큰 제한 고려하여 필터/추출
3. 보고서 작성 subagent → 분석 결과 취합 및 보고서 작성
4. 메인 에이전트 → 최종 결과를 사용자에게 전달

## 🔍 현재 구현 vs DeepAgents 라이브러리 비교

### 현재 구현 (`src/agents/deep_agent.py`)
- **방식**: LangGraph 직접 사용
- **코드량**: ~400줄
- **복잡도**: 높음 (노드, 엣지 직접 구성)
- **유지보수**: 직접 관리 필요

### DeepAgents 라이브러리 (`deepagent/`)
- **방식**: `create_deep_agent()` 함수 사용
- **코드량**: ~150줄
- **복잡도**: 낮음 (추상화된 API)
- **유지보수**: 라이브러리 업데이트 자동 적용

## 🛠️ 고급 설정

### 커스텀 시스템 프롬프트

```python
agent = DeepAgentLibrary(
    system_prompt="""당신은 전문 소프트웨어 아키텍트입니다.
    복잡한 시스템 설계 작업을 수행할 수 있습니다."""
)
```

### 커스텀 도구 추가

```python
from langchain.tools import tool

@tool("custom_tool")
def my_custom_tool(query: str) -> str:
    """커스텀 도구 설명"""
    return "결과"

agent = DeepAgentLibrary(tools=[my_custom_tool])
```

## 📝 참고 자료

- [DeepAgents 문서](https://docs.langchain.com/oss/python/deepagents/quickstart)
- [DeepAgents 커스터마이징](https://docs.langchain.com/oss/python/deepagents/customization)
- [LangChain Middleware](https://docs.langchain.com/oss/python/langchain/middleware)

## ⚠️ 주의사항

1. **API 키 필수**: 최소 하나의 API 키가 설정되어 있어야 합니다.
2. **Ollama 사용 시**: `OLLAMA_API_KEY`와 `OLLAMA_MODEL_NAME` 설정 필요
3. **검색 도구 사용 시**: `BRAVE_API_KEY` 설정 필요 (선택사항)

## 🐛 문제 해결

### 모델 초기화 실패
```
❌ API 키가 설정되지 않았습니다.
```
→ `.env` 파일에 적절한 API 키를 설정하세요.

### 검색 도구 사용 불가
```
⚠️  BRAVE_API_KEY가 설정되지 않았습니다.
```
→ 검색 기능이 필요하지 않으면 `--with-search` 옵션을 제거하세요.

## 📚 다음 단계

1. **서브에이전트 활용**: `task` 도구를 사용하여 복잡한 작업 분담
2. **파일 시스템 활용**: 파일 읽기/쓰기를 통한 컨텍스트 관리
3. **Middleware 커스터마이징**: 고급 컨텍스트 엔지니어링

