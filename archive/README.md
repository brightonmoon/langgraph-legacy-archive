# Archive 디렉토리

이 디렉토리는 프로젝트에서 더 이상 활발히 사용하지 않지만, 참고 가치가 있는 코드를 보관합니다.

> **배경**: `agentic_ai` 프로젝트는 Langchain/Langgraph 기반으로 Agent 시스템을 구현하다가,
> 프레임워크의 복잡성과 한계(State 관리, Sub-agent 의존성, async/sync 충돌 등)로 인해
> 개발이 중단되었습니다. 이 아카이브는 당시의 실험 코드를 보존합니다.

## 📁 아카이브된 디렉토리

### deepagent/
- **이동일**: 2025-01-27
- **용도**: LangChain Deep Agents 컨셉 증명용 코드
- **상태**: 아카이브됨 (활성 사용 안 함)
- **참고**: `tests/examples/deepagent_subagents_example.py`에서 참조 가능 (langchain의 deepagents 패키지 사용)

**주요 내용**:
- DeepAgents 라이브러리 구현 예제
- Subagent 패턴 실험 코드
- CSV 멀티 에이전트 플로우 예제
- Plan Persistence (Offload Context) 구현

**참고 문서**: `archive/deepagent/README.md`

---

### tests/ (테스트 코드 아카이브)

- **이동일**: 2025-01-27
- **용도**: 참고 가치가 있는 테스트 코드 보관
- **상태**: 아카이브됨 (활성 테스트에서 제외)

#### 아카이브된 테스트 카테고리

**agents/** (3개 파일)
- `test_stock_research_simple.py` - OrchestratorAgent + WorkerFactory 아키텍처 설명
- `test_stock_research_detailed.py` - 상세한 아키텍처 설명 및 사용법
- `test_chaining.py` - LangGraph Agent Chaining 패턴 예제

**pdf_parsing/** (3개 파일)
- `test_docling_comparison.py` - Docling과 다른 PDF 파서 비교 분석
- `test_pdf_parser_comparison.py` - 다양한 PDF 파서 비교
- `test_contextual_chunking.py` - 다양한 청킹 전략 비교 및 분석

**csv_agent/** (1개 파일)
- `test_csv_agent_debugging.py` - 디버깅 패턴 및 문제 해결 방법

**code_execution/** (1개 파일)
- `test_code_execution_refactoring.py` - 리팩토링 과정 및 패턴

**code_generation/** (2개 파일)
- `test_code_generation_agent_integration.py` - 통합 테스트 시나리오
- `test_code_generation_agent_execution.py` - 복잡한 실행 테스트

**총 아카이브 파일 수**: 28개 (1차: 10개, 2차: 18개)

**1차 아카이브 (2025-01-27)**:
- 컨셉 증명 및 아키텍처 설명 포함
- 비교 분석 결과 (참고 가치)
- 디버깅 및 고급 패턴 예제
- 복잡한 통합 테스트 시나리오

**2차 아카이브 (2025-01-27)**:
- 복잡한 패턴 및 아키텍처 (Multiple Workers, REPL, Factory 등)
- 고급 기능 및 통합 테스트 (파일 경로 처리, 세션 관리 등)
- Docker 복잡한 시나리오 (마운트, 샌드박스, 프롬프트 엔지니어링)
- 고급 기능 테스트 (Docling 고급, Office 문서, 토큰 추적, RAG 패턴)

#### 2차 아카이브 상세 (18개 파일)

**agents/** (5개)
- `test_python_repl_agent.py` - Python REPL Agent 패턴
- `test_repl_data_analysis_agent.py` - REPL 기반 하이브리드 스키마 데이터 분석
- `test_multiple_workers_coding_agent.py` - Multiple Workers 패턴
- `test_multiple_workers_coding_agent_factory.py` - Factory 패턴
- `test_stock_research_agent.py` - OrchestratorAgent + WorkerFactory 사용 예제

**code_generation/** (2개)
- `test_code_generation_agent_file_path_extraction.py` - 파일 경로 추출 기능
- `test_code_generation_agent_file_path_integration.py` - 파일 경로 통합 테스트

**csv_agent/** (1개)
- `test_csv_data_analysis_agent_workflow.py` - CSV 분석 워크플로우

**code_execution/** (2개)
- `test_code_execution_tooling.py` - 코드 실행 도구화
- `test_ipython_session_executor.py` - IPython 세션 Executor

**docker/** (4개)
- `test_docker_mount_scenarios.py` - Docker 마운트 시나리오
- `test_docker_file_path_handling.py` - Docker 파일 경로 처리
- `test_prompt_engineering_docker_paths.py` - 프롬프트 엔지니어링
- `test_shelltool_docker_sandbox.py` - ShellTool Docker 샌드박스

**pdf_parsing/** (1개)
- `test_docling_advanced.py` - Docling 고급 기능

**utils/** (2개)
- `test_office_document_output.py` - Office 문서 출력
- `test_token_usage_tracking.py` - 토큰 사용량 추적

**rag/** (1개)
- `test_rag_agent_pdf_lookup.py` - RAG PDF 룩업

---

## 📝 아카이브 정책

이 디렉토리의 파일들은:
- ✅ 참고용으로 보관
- ✅ Git 히스토리 보존
- ⚠️ 활성 개발에서 제외
- ⚠️ 필요시 복구 가능

---

**최종 업데이트**: 2025-01-27
