# Tests 디렉토리

이 디렉토리는 모든 테스트, 예제 코드, 유틸리티 스크립트를 포함합니다.

## 📁 디렉토리 구조

```
tests/
├── agents/                    # Agent 관련 테스트
│   ├── test_coding_agent.py
│   ├── test_multiple_workers_coding_agent.py
│   ├── test_multiple_workers_coding_agent_factory.py
│   ├── test_stock_research_agent.py
│   ├── test_stock_research_simple.py
│   ├── test_stock_research_detailed.py
│   ├── test_python_repl_agent.py
│   ├── test_repl_data_analysis_agent.py
│   └── test_chaining.py
├── code_generation/           # Code Generation Agent 테스트
│   ├── test_code_generation_agent_execution.py
│   ├── test_code_generation_agent_file_path_extraction.py
│   ├── test_code_generation_agent_file_path_integration.py
│   └── test_code_generation_agent_integration.py
├── csv_agent/                 # CSV Data Analysis Agent 테스트
│   ├── test_csv_agent_debugging.py
│   ├── test_csv_agent_ipython.py
│   ├── test_csv_agent_planning_tool.py
│   ├── test_csv_data_analysis_agent.py
│   └── test_csv_data_analysis_agent_workflow.py
├── csv_analysis/              # CSV 분석 테스트 (신규)
│   ├── test_simple_csv_agent.py
│   └── test_simple_csv_agent_planning.py
├── code_execution/            # Code Execution 관련 테스트
│   ├── test_code_execution_refactoring.py
│   ├── test_code_execution_tooling.py
│   ├── test_ipython_executor.py
│   └── test_ipython_session_executor.py
├── docker/                    # Docker 관련 테스트
│   ├── test_docker_file_path_handling.py
│   ├── test_docker_mount_scenarios.py
│   ├── test_docker_sdk_direct.py
│   ├── test_shelltool_docker_sandbox.py
│   ├── test_shelltool_docker_sandbox_simple.py
│   ├── test_prompt_engineering_docker_paths.py
│   └── Dockerfile.sandbox
├── pdf_parsing/               # PDF 파싱 테스트 (신규)
│   ├── test_docling_basic.py
│   ├── test_docling_advanced.py
│   ├── test_docling_comparison.py
│   ├── test_pdf_parser_comparison.py
│   ├── test_poster_pdf_parser.py
│   ├── test_omicsai_pdf_comparison.py
│   ├── test_unstructured_strategies.py
│   ├── test_mineru_cli.py
│   └── test_contextual_chunking.py
├── rag/                       # RAG 관련 테스트 (신규)
│   ├── test_rag_agent.py
│   ├── test_rag_agent_csv_lookup.py
│   └── test_rag_agent_pdf_lookup.py
├── utils/                     # 유틸리티 테스트
│   ├── test_token_usage_tracking.py
│   ├── test_office_document_output.py
│   ├── test_deseq2_analysis.py
│   └── test_mcp.py
├── examples/                  # 예제 코드
│   ├── *_example.py          # 사용 예시 코드
│   └── *_test.py             # 테스트 목적 예제
├── scripts/                   # 유틸리티 스크립트
│   └── *.py                  # 프로젝트 관리/테스트 유틸리티
├── tutorials/                 # 튜토리얼 (신규)
│   └── 01-QuickStart-LangGraph-Tutorial.ipynb
├── docs/                      # 문서 (신규)
│   ├── setup/                # 설정 가이드
│   ├── analysis/             # 분석 결과
│   └── recommendations/      # 권장사항
├── test_data/                 # 테스트 데이터
├── test_output/               # 테스트 출력
│   ├── code_generation_output/  # 코드 생성 출력
│   ├── office_output/          # Office 문서 출력
│   ├── embeddings/             # 임베딩 출력
│   ├── mineru_comparison/      # Mineru 비교 출력
│   └── results/                # 일반 결과
├── reports/                    # 리포트
└── README.md                   # 이 파일
```

## 🧪 테스트 실행

### pytest 사용

```bash
# 모든 테스트 실행
uv run pytest tests/

# 특정 카테고리의 테스트 실행
uv run pytest tests/agents/
uv run pytest tests/code_generation/
uv run pytest tests/csv_agent/
uv run pytest tests/csv_analysis/
uv run pytest tests/code_execution/
uv run pytest tests/docker/
uv run pytest tests/pdf_parsing/
uv run pytest tests/rag/
uv run pytest tests/utils/

# 특정 테스트 파일 실행
uv run pytest tests/agents/test_coding_agent.py

# 특정 패턴 테스트 실행
uv run pytest tests/agents/test_*_agent.py
```

### 직접 실행

```bash
# 테스트 파일 직접 실행
uv run python tests/agents/test_coding_agent.py

# 예제 코드 실행
uv run python tests/examples/coding_agent_example.py

# 스크립트 실행
uv run python tests/scripts/check_langfuse_status.py
```

## 📝 파일 분류

### 테스트 파일 (`test_*.py`)

#### agents/
- Agent 기능 테스트
- 다양한 Agent 타입 및 패턴 테스트
- pytest로 실행 가능한 구조

#### code_generation/
- Code Generation Agent 관련 테스트
- 파일 경로 처리, 실행, 통합 테스트

#### csv_agent/
- CSV 데이터 분석 Agent 테스트
- 디버깅, IPython 통합, 계획 도구 테스트

#### code_execution/
- 코드 실행 관련 테스트
- IPython executor, 코드 실행 도구 테스트

#### docker/
- Docker 환경 관련 테스트
- 파일 경로 처리, 마운트 시나리오, 샌드박스 테스트

#### utils/
- 유틸리티 기능 테스트
- 토큰 사용량 추적, 문서 출력, 분석 도구 테스트

#### pdf_parsing/
- PDF 파싱 관련 테스트
- Docling, PDF 파서 비교, 포스터 파싱, Mineru CLI 테스트

#### rag/
- RAG (Retrieval-Augmented Generation) 관련 테스트
- RAG Agent, CSV/PDF 룩업 테스트

#### csv_analysis/
- CSV 데이터 분석 테스트
- 간단한 CSV Agent 및 계획 도구 테스트

### 예제 코드 (`examples/`)
- 사용 예시 및 데모 코드
- 독립 실행 가능한 완전한 예제
- 파일명: `{feature}_example.py` 또는 `example_{feature}.py`

### 유틸리티 스크립트 (`scripts/`)
- 프로젝트 관리 도구
- 문서 생성/관리 스크립트
- 시스템 상태 확인 스크립트

### 문서 (`docs/`)
- `setup/`: 설정 가이드 문서
- `analysis/`: 분석 결과 문서
- `recommendations/`: 권장사항 문서

### 튜토리얼 (`tutorials/`)
- Jupyter 노트북 튜토리얼
- LangGraph 등 프레임워크 학습 자료

## 🔍 코드 생성 규칙

**⚠️ 중요**: 새로운 테스트, 예제, 스크립트는 반드시 `tests/` 디렉토리 내에서만 생성하세요.

자세한 규칙은 `.cursor/rules/test-and-code-generation-location.mdc`를 참조하세요.

## 📌 Import 경로 주의사항

테스트 파일이 하위 디렉토리에 있을 경우, 프로젝트 루트 경로를 올바르게 설정해야 합니다:

```python
# 하위 디렉토리 (예: tests/agents/)에서 사용
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 또는
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
```
