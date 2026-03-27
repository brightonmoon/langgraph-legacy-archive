# Agentic AI - 모듈화된 LangChain & LangGraph Agent 시스템

**생성 일시**: 2025-01-27 14:30:00  
**버전**: 3.0.0  
**라이선스**: MIT

LangChain과 LangGraph를 사용한 모듈화된 Agent 시스템입니다. 다양한 Agent 아키텍처와 모델을 제공합니다.

---

## 🚀 주요 특징

- **모듈화된 아키텍처**: 확장 가능하고 유지보수가 쉬운 구조
- **다양한 Agent 타입**: Basic, LangGraph, MCP, Tools, Coding 등 9가지 Agent
- **Ollama 모델 지원**: 로컬 및 클라우드 모델 지원
- **팩토리 패턴**: Agent 생성 및 관리
- **실시간 쿼리 입력**: CLI 인터페이스 제공
- **도구 통합**: 계산기, 날씨, 웹 검색 도구 지원
- **MCP 지원**: Model Context Protocol 통합

---

## 📁 프로젝트 구조

```
src/
├── agents/                              # Agent 모듈
│   ├── base.py                          # 기본 Agent 인터페이스
│   ├── basic_agent.py                   # 기본 LangChain Agent
│   ├── langgraph_agent.py               # LangGraph StateGraph Agent
│   ├── langgraph_agent_tools.py         # LangGraph Agent with Tools
│   ├── langgraph_agent_mcp.py          # LangGraph MCP Agent
│   ├── langgraph_agent_tools_middleware.py # LangGraph Agent with Tools Middleware
│   ├── langgraph_agent_chaining.py     # LangGraph Chaining Agent
│   ├── langgraph_agent_parallel.py    # LangGraph Parallel Agent
│   ├── coding_agent.py                 # Coding Agent
│   ├── multiple_workers_coding_agent.py # Multiple Workers Coding Agent
│   ├── factory.py                       # Agent 팩토리
│   └── middleware/                      # 미들웨어 모듈
├── models/                              # 모델 모듈
│   └── ollama_model.py                  # Ollama 모델 설정
├── tools/                               # 도구 모듈
│   ├── base.py                          # 기본 도구 인터페이스
│   ├── calculator.py                    # 계산기 도구
│   ├── brave_search.py                  # 웹 검색 도구
│   └── factory.py                       # 도구 팩토리
└── mcp/                                 # MCP 모듈
    ├── client/                          # MCP 클라이언트
    ├── config/                          # MCP 설정
    └── servers/                         # MCP 서버
```

---

## 🛠️ 설치 및 설정

### 1. 환경 설정

```bash
# 가상환경 활성화
source /home/doyamoon/agentic_ai/.venv/bin/activate

# 필요한 패키지 설치
pip install langchain langchain-community langgraph python-dotenv pyyaml requests pytz
```

### 2. 환경변수 설정

```bash
# 환경변수 파일 생성
cp env_example.txt .env

# .env 파일 편집
nano .env
```

`.env` 파일 내용:
```env
OLLAMA_API_KEY=your_actual_ollama_api_key
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=""
BRAVE_API_KEY=your_brave_search_api_key  # 선택사항: 웹 검색 기능 사용 시
KMA_API_KEY=your_kma_api_key             # 선택사항: 날씨 기능 사용 시
```

---

## 🎯 사용법

### 1. CLI 인터페이스 (권장)

```bash
# 가상환경 활성화
source /home/doyamoon/agentic_ai/.venv/bin/activate

# CLI 실행
uv run cli.py
```

### 2. 직접 Agent 사용

```python
from src.agents.factory import AgentFactory

# Agent 생성
agent = AgentFactory.create_agent("langgraph_tools")

# 쿼리 실행
response = agent.generate_response("오늘 날씨가 어때?")
print(response)
```

---

## 📊 Agent 타입

### 1. Basic Agent
- **구조**: 단순 클래스 기반
- **특징**: 빠른 응답, 간단한 구조
- **사용 사례**: 기본적인 질문-답변

### 2. LangGraph Agent
- **구조**: StateGraph 기반
- **특징**: 상태 관리, 노드 기반
- **플로우**: `START → input_processor → llm_call → response_formatter → END`

### 3. LangGraph Tools Agent
- **구조**: StateGraph + Tools
- **특징**: 도구 통합, 확장 가능
- **도구**: 계산기, 날씨, 웹 검색

### 4. LangGraph MCP Agent
- **구조**: StateGraph + MCP
- **특징**: MCP 서버 통합
- **기능**: 동적 도구 로딩

### 5. LangGraph Tools Middleware Agent
- **구조**: StateGraph + Tools + Middleware
- **특징**: 미들웨어 패턴 적용
- **기능**: 도구 사용 통계 및 모니터링

### 6. LangGraph Chaining Agent
- **구조**: StateGraph Chaining
- **특징**: 체인 연결
- **사용 사례**: 복잡한 워크플로우

### 7. LangGraph Parallel Agent
- **구조**: StateGraph Parallel
- **특징**: 병렬 처리
- **사용 사례**: 다중 작업 처리

### 8. Coding Agent
- **구조**: Orchestrator-Worker 패턴
- **Orchestrator**: gpt-oss:120b-cloud (작업 분석)
- **Worker**: qwen2.5-coder:latest (코딩 작업)

### 9. Multiple Workers Coding Agent
- **구조**: Orchestrator-Multiple Workers
- **Orchestrator**: gpt-oss:120b-cloud (품질 평가)
- **Workers**: qwen2.5-coder:latest, codegemma:latest (병렬 생성)

---

## 🔧 모듈 구조

### Agent 모듈 (`src/agents/`)

#### BaseAgent (추상 클래스)
```python
class BaseAgent(ABC):
    @abstractmethod
    def generate_response(self, query: str) -> str:
        """쿼리에 대한 응답 생성"""
        
    @abstractmethod
    def is_ready(self) -> bool:
        """Agent가 준비되었는지 확인"""
        
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Agent 정보 반환"""
```

#### AgentFactory
```python
class AgentFactory:
    @classmethod
    def create_agent(cls, agent_type: str, model_name: str = None) -> BaseAgent:
        """지정된 타입의 Agent 생성"""
        
    @classmethod
    def get_available_agents(cls) -> list:
        """사용 가능한 Agent 타입 목록 반환"""
```

### 도구 모듈 (`src/tools/`)

#### BaseTool (추상 클래스)
```python
class BaseTool(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Tool 이름 반환"""
        
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Tool 실행"""
```

#### Calculator Tool
- **기능**: 기본적인 수학 연산 수행
- **지원 연산**: 사칙연산(+, -, *, /), 거듭제곱(**)

#### Brave Search Tool
- **기능**: Brave Search API를 사용한 웹 검색
- **특징**: 최신 정보 조회, 상위 5개 결과 제공

### 모델 모듈 (`src/models/`)

#### Ollama Model
```python
def create_ollama_model(model_name: str = "gpt-oss:120b-cloud"):
    """Ollama 모델 생성"""
```

### MCP 모듈 (`src/mcp/`)

#### MCP Client Manager
- MCP 서버 연결
- 동적 도구 로딩
- 설정 파일 관리 (`mcp_config.json`)

---

## 📊 Agent 비교

| Agent 타입 | 구조 | 상태 관리 | 확장성 | 도구 지원 | 사용 사례 |
|----------|------|---------|-------|----------|----------|
| Basic | 단순 클래스 | 기본적 | 제한적 | ❌ | 기본 질문-답변 |
| LangGraph | StateGraph 노드 | 고급 | 높음 | ❌ | 복잡한 워크플로우 |
| LangGraph Tools | StateGraph + Tools | 고급 | 매우 높음 | ✅ | 도구 활용 작업 |
| LangGraph MCP | StateGraph + MCP | 고급 | 매우 높음 | ✅ | 동적 도구 로딩 |
| LangGraph Middleware | StateGraph + Middleware | 고급 | 매우 높음 | ✅ | 모니터링이 필요한 작업 |
| LangGraph Chaining | StateGraph Chaining | 고급 | 매우 높음 | ❌ | 체인 연결 |
| LangGraph Parallel | StateGraph Parallel | 고급 | 매우 높음 | ❌ | 다중 작업 처리 |
| Coding | Orchestrator-Worker | 고급 | 높음 | ❌ | 코딩 작업 |
| Multiple Workers Coding | Orchestrator-Multiple Workers | 고급 | 매우 높음 | ❌ | 복잡한 코딩 작업 |

---

## 💻 CLI 사용법

### 메뉴 옵션
1. **Basic Agent**: 기본 LangChain Agent
2. **LangGraph Agent**: LangGraph StateGraph Agent
3. **LangGraph Tools Agent**: Tools를 사용하는 Agent
4. **LangGraph MCP Agent**: MCP 통합 Agent
5. **LangGraph Tools Middleware Agent**: Middleware가 적용된 Agent
6. **Coding Agent**: 코딩 작업 전용 Agent
7. **Multiple Workers Coding Agent**: 다중 Worker 코딩 Agent
8. **Agent 정보**: 모든 Agent의 상세 정보
9. **종료**: 프로그램 종료

### 예시 실행
```
🚀 Agentic AI CLI
========================================
1. Basic Agent 사용
2. LangGraph Agent 사용
3. LangGraph Tools Agent 사용
4. LangGraph MCP Agent 사용
5. LangGraph Tools Middleware Agent 사용
6. Coding Agent 사용
7. Multiple Workers Coding Agent 사용
8. Agent 정보
9. 종료
----------------------------------------
선택하세요 (1-9): 3

🔧 LANGGRAPH_TOOLS Agent 테스트
----------------------------------------
✅ LANGGRAPH_TOOLS Agent 준비 완료!
   모델: gpt-oss:120b-cloud
   아키텍처: StateGraph 기반
   기능: tool_calling, reasoning, acting

💬 대화형 모드 시작
💡 '/help' 입력시 도구 설명을 볼 수 있습니다.
----------------------------------------
```

---

## 🧪 테스트

### 모듈 테스트
```bash
# 가상환경 활성화
source /home/doyamoon/agentic_ai/.venv/bin/activate

# 테스트 실행
uv run tests/test_chaining.py
uv run tests/test_coding_agent.py
```

### 테스트 파일
- `tests/test_chaining.py` - Chaining Agent 테스트
- `tests/test_coding_agent.py` - Coding Agent 테스트
- `tests/test_mcp.py` - MCP Agent 테스트
- `tests/test_multiple_workers_coding_agent.py` - Multiple Workers Agent 테스트

---

## 🔍 문제 해결

### 일반적인 오류

1. **"OLLAMA_API_KEY가 설정되지 않았습니다"**
   - `.env` 파일이 존재하는지 확인
   - API 키가 올바르게 설정되었는지 확인

2. **"모델 초기화 중 오류 발생"**
   - Ollama 서비스가 실행 중인지 확인
   - 모델명이 올바른지 확인
   - 네트워크 연결 상태 확인

3. **"그래프 빌드 중 오류 발생"**
   - LangGraph 패키지가 올바르게 설치되었는지 확인
   - 모델이 정상적으로 초기화되었는지 확인

4. **"MCP 서버 연결 실패"**
   - `mcp_config.json` 파일 확인
   - MCP 서버 상태 확인

---

## 📈 확장 가능성

### 새로운 Agent 추가
1. `src/agents/` 디렉토리에 새 Agent 클래스 생성
2. `BaseAgent`를 상속받아 구현
3. `AgentFactory`에 새 Agent 타입 등록

### 새로운 모델 추가
1. `src/models/` 디렉토리에 새 모델 설정 파일 생성
2. 모델 초기화 함수 구현
3. Agent에서 새 모델 사용

### 새로운 도구 추가
1. `src/tools/` 디렉토리에 새 도구 클래스 생성
2. `BaseTool`를 상속받아 구현
3. `ToolFactory`에 새 도구 등록

### 기능 추가
- **메모리 기능**: 대화 기록 저장
- **웹 인터페이스**: Flask/FastAPI 통합
- **스트리밍**: 실시간 응답 스트리밍
- **배포**: Docker 및 클라우드 배포

---

## 📝 개발 일지

- **2025-01-27**: 기본 LangChain Agent 구현
- **2025-01-27**: LangGraph StateGraph Agent 구현
- **2025-01-27**: Tools 통합 Agent 구현
- **2025-01-27**: MCP Agent 구현
- **2025-01-27**: Coding Agent 구현 (Orchestrator-Worker)
- **2025-01-27**: Multiple Workers Coding Agent 구현
- **2025-01-27**: Middleware 패턴 적용
- **2025-01-27**: 프로젝트 구조 리팩토링
- **2025-01-27**: 문서 통합 및 정리

---

## 🎯 다음 단계

1. **추가 도구**: 더 많은 LangChain Tools 통합
2. **메모리 시스템**: 대화 기록 및 컨텍스트 관리
3. **웹 인터페이스**: 사용자 친화적인 웹 UI
4. **배포**: Docker 및 클라우드 배포
5. **모니터링**: 성능 및 사용량 모니터링

---

**개발자**: AI Assistant  
**프로젝트**: Agentic AI - 모듈화된 LangChain & LangGraph Agent 시스템  
**버전**: 3.0.0  
**라이선스**: MIT
