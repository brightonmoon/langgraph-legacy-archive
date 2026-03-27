# 병렬 검색 에이전트 (Parallel Search Agent)

Tavily와 Brave Search를 병렬로 사용하여 검색 결과를 취합하고 보고서를 작성하는 에이전트입니다.

## 📋 개요

이 에이전트는 LangChain Deep Agents의 subagent 기능을 활용하여 두 개의 검색 엔진(Tavily와 Brave Search)을 병렬로 사용합니다. 각 검색 엔진은 독립적인 서브에이전트로 동작하며, 메인 에이전트가 결과를 취합하여 종합 보고서를 작성합니다.

### 주요 특징

- **병렬 검색**: Tavily와 Brave Search가 동시에 검색 수행
- **결과 취합**: 두 검색 엔진의 결과를 종합 분석
- **컨텍스트 격리**: 각 서브에이전트가 독립적으로 동작하여 컨텍스트 보호
- **구조화된 보고서**: 검색 결과를 바탕으로 전문적인 보고서 작성

## 🚀 빠른 시작

### 1. 환경 설정

`.env` 파일에 필요한 API 키를 설정하세요:

```bash
# 필수: 검색 API 키 (최소 하나는 필요)
TAVILY_API_KEY=your_tavily_api_key
BRAVE_API_KEY=your_brave_api_key

# 선택: 모델 API 키 (없으면 자동 결정)
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
OLLAMA_API_KEY=your_ollama_api_key
```

### 2. 실행

#### LangGraph dev를 통한 테스트 (권장)

```bash
# LangGraph dev 실행
langgraph dev

# 또는
uv run langgraph dev
```

LangGraph Studio에서:
1. `parallel_search_agent` 그래프 선택
2. 테스트 쿼리 입력 예시:
   - "최신 AI 트렌드에 대해 조사해주세요."
   - "LangChain과 LangGraph의 차이점을 비교해주세요."
   - "양자 컴퓨팅의 최신 동향을 알려주세요."

#### 직접 실행 (선택사항)

```bash
# 대화형 모드
uv run parallel_search_agent/run.py

# 특정 쿼리 실행
uv run parallel_search_agent/run.py --query "최신 AI 트렌드"

# 특정 모델 지정
uv run parallel_search_agent/run.py --model "anthropic:claude-sonnet-4-5-20250929" --query "양자 컴퓨팅"
```

## 📁 파일 구조

```
parallel_search_agent/
├── __init__.py          # 패키지 초기화 및 export
├── agent.py            # ParallelSearchAgent 클래스 (메인 에이전트)
├── tools.py            # 검색 도구들 (Tavily, Brave Search)
├── subagents.py        # 검색 서브에이전트 정의
├── run.py              # 실행 스크립트 (선택사항)
└── README.md           # 이 문서
```

**참고**: 테스트는 LangGraph dev를 통해 수행합니다 (`langgraph.json`에 등록됨).

## 💻 사용 예제

### 예제 1: 기본 사용

```python
from parallel_search_agent import ParallelSearchAgent

# 에이전트 생성
agent = ParallelSearchAgent()

# 검색 쿼리 실행
result = agent.invoke("최신 AI 트렌드에 대해 조사해주세요.")

# 대화형 모드
agent.chat()
```

### 예제 2: 특정 모델 사용

```python
from parallel_search_agent import ParallelSearchAgent

# Claude 모델 사용
agent = ParallelSearchAgent(
    model="anthropic:claude-sonnet-4-5-20250929"
)

# 검색 실행
result = agent.invoke("양자 컴퓨팅의 최신 동향")
```

### 예제 3: 커스텀 시스템 프롬프트

```python
from parallel_search_agent import ParallelSearchAgent

agent = ParallelSearchAgent(
    model="anthropic:claude-sonnet-4-5-20250929",
    system_prompt="""당신은 기술 트렌드 분석 전문가입니다.
    
검색 결과를 바탕으로 기술 트렌드 분석 보고서를 작성하세요.
- 기술 분류
- 트렌드 분석
- 향후 전망"""
)

result = agent.invoke("머신러닝 최신 동향")
```

## 🔍 작동 원리

### 1. 병렬 검색 프로세스

```
사용자 쿼리
    ↓
메인 에이전트 (ParallelSearchAgent)
    ↓
    ├─→ Tavily 서브에이전트 (tavily-searcher)
    │   └─→ Tavily Search API 호출
    │
    └─→ Brave Search 서브에이전트 (brave-searcher)
        └─→ Brave Search API 호출
    ↓
검색 결과 취합
    ↓
종합 분석 및 보고서 작성
    ↓
최종 결과 반환
```

### 2. 서브에이전트 역할

#### Tavily 서브에이전트 (`tavily-searcher`)
- **역할**: AI 검색 엔진을 사용한 질문 중심 검색
- **특징**: 답변 중심의 검색 결과 제공
- **최적화**: 질문 형식의 쿼리에 최적화

#### Brave Search 서브에이전트 (`brave-searcher`)
- **역할**: 프라이버시 중심의 일반 웹 검색
- **특징**: 일반적인 웹 검색 결과 제공
- **최적화**: 최신 뉴스 및 웹사이트 검색에 최적화

### 3. 메인 에이전트 역할

- **병렬 위임**: 두 서브에이전트에게 동시에 검색 작업 위임
- **결과 취합**: 두 검색 엔진의 결과를 종합 분석
- **중복 제거**: 중복 정보 제거 및 핵심 정보 추출
- **보고서 작성**: 구조화된 종합 보고서 작성

## 📊 보고서 구조

메인 에이전트가 작성하는 보고서는 다음 구조를 따릅니다:

1. **요약 (Executive Summary)**
   - 2-3 문단의 종합 요약

2. **주요 발견사항**
   - 불릿 포인트 형식의 핵심 정보

3. **상세 분석**
   - 각 검색 엔진의 결과 비교
   - 종합 분석 및 인사이트

4. **결론 및 권장사항**
   - 종합 결론 및 향후 조사 방향

5. **출처**
   - Tavily와 Brave Search 결과의 URL 목록

## ⚙️ 설정 옵션

### 모델 선택

```python
# Claude 사용
agent = ParallelSearchAgent(model="anthropic:claude-sonnet-4-5-20250929")

# OpenAI 사용
agent = ParallelSearchAgent(model="openai:gpt-4o")

# Ollama 사용
agent = ParallelSearchAgent(model="ollama:gpt-oss:120b-cloud")

# 자동 결정 (환경변수 기반)
agent = ParallelSearchAgent()  # Ollama → Claude → OpenAI 순서로 자동 선택
```

### 커스텀 시스템 프롬프트

```python
agent = ParallelSearchAgent(
    system_prompt="""당신은 특정 도메인의 전문가입니다.
    
검색 결과를 바탕으로 도메인 특화 분석을 수행하세요."""
)
```

## 🔧 고급 사용

### 서브에이전트 직접 생성

```python
from parallel_search_agent import (
    ParallelSearchAgent,
    create_tavily_search_subagent,
    create_brave_search_subagent
)

# 커스텀 서브에이전트 생성
tavily_subagent = create_tavily_search_subagent(
    model="openai:gpt-4o"  # 서브에이전트용 모델 지정
)

brave_subagent = create_brave_search_subagent(
    model="openai:gpt-4o"
)

# DeepAgentLibrary에 직접 전달 (고급 사용)
from deepagent.agent import DeepAgentLibrary

agent = DeepAgentLibrary(
    model="anthropic:claude-sonnet-4-5-20250929",
    subagents=[tavily_subagent, brave_subagent]
)
```

## ⚠️ 주의사항

1. **API 키 필수**: `TAVILY_API_KEY`와 `BRAVE_API_KEY` 중 최소 하나는 설정되어 있어야 합니다.
2. **모델 API 키**: 모델을 사용하기 위한 API 키도 필요합니다 (ANTHROPIC_API_KEY, OPENAI_API_KEY, 또는 OLLAMA_API_KEY).
3. **검색 비용**: 각 검색 API는 사용량에 따라 비용이 발생할 수 있습니다.
4. **응답 시간**: 병렬 검색이므로 두 검색 엔진의 응답을 모두 기다려야 합니다.

## 🐛 문제 해결

### 서브에이전트 생성 실패

```
⚠️ Tavily 검색 서브에이전트 생성 실패 (TAVILY_API_KEY 확인 필요)
```

**해결책**: `.env` 파일에 `TAVILY_API_KEY`를 설정하세요.

### 검색 결과 없음

**원인**: 검색 쿼리가 너무 구체적이거나 검색 결과가 없을 수 있습니다.

**해결책**: 
- 더 일반적인 키워드로 검색
- 검색 쿼리를 질문 형식으로 변경

### 모델 초기화 실패

```
❌ API 키가 설정되지 않았습니다.
```

**해결책**: `.env` 파일에 모델 API 키를 설정하세요.

## 📚 참고 자료

- [LangChain Deep Agents 문서](https://docs.langchain.com/oss/python/deepagents)
- [LangChain Deep Agents Subagents](https://docs.langchain.com/oss/python/deepagents/subagents)
- [Tavily Search API](https://tavily.com/)
- [Brave Search API](https://brave.com/search/api/)

## 📝 라이선스

이 프로젝트는 프로젝트 루트의 라이선스를 따릅니다.

