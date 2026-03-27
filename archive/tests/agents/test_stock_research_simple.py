#!/usr/bin/env python3
"""
주식 자료조사 및 보고서 에이전트 간단한 테스트

OrchestratorAgent와 WorkerFactory 사용법을 설명하고 간단히 테스트합니다.

사용 전 환경 설정:
1. .env 파일에 다음 환경변수 설정:
   - OLLAMA_API_KEY=your_ollama_api_key
   - BRAVE_API_KEY=your_brave_api_key (선택적, 웹 검색용)

실행 방법:
    source .venv/bin/activate
    uv run test_stock_research_simple.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 직접 import (의존성 문제 회피)
from src.agents import OrchestratorAgent
from src.agents.worker import WorkerFactory


def print_usage_explanation():
    """사용법 설명 출력"""
    print("\n" + "=" * 70)
    print("📚 OrchestratorAgent + WorkerFactory 사용법")
    print("=" * 70)
    
    print("""
## 🏗️ 아키텍처 개요

OrchestratorAgent (상위 계층)
    ↓
    작업 분석 → Worker 선택 → 결과 통합
    ↓
WorkerFactory (Worker 생성)
    ↓
    적절한 Worker 생성 (deepagent 또는 LangGraph 직접)
    ↓
    Worker 실행 (도구 포함: brave_search 등)


## 📝 사용 예시 코드

### 방법 1: OrchestratorAgent 직접 사용 (권장)

```python
from src.agents import OrchestratorAgent

# 1. OrchestratorAgent 생성
orchestrator = OrchestratorAgent(
    orchestrator_model="ollama:gpt-oss:120b-cloud"
)

# 2. 주식 조사 요청 실행
query = "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘"
response = orchestrator.generate_response(query)

# OrchestratorAgent가 자동으로:
# 1. 작업 분석 → Planning + Filesystem + SubAgent 필요 감지
# 2. Worker 선택 → deepagent Worker 선택
# 3. 도구 선택 → brave_search_tool 추가
# 4. Worker 실행 → deepagent Worker가 조사 및 보고서 작성
# 5. 결과 통합 → 최종 보고서 생성
print(response)
```


### 방법 2: WorkerFactory 직접 사용 (고급)

```python
from src.agents import WorkerFactory
from src.tools.brave_search import brave_search_tool

# 1. WorkerFactory 생성
worker_factory = WorkerFactory()

# 2. 주식 조사용 deepagent Worker 생성
worker = worker_factory.create_worker(
    worker_type="deepagent",  # 또는 "auto"로 자동 선택
    model="ollama:qwen2.5-coder:latest",
    tools=[brave_search_tool],  # 웹 검색 도구 전달
    needs_planning=True,        # 작업 분해 필요
    needs_filesystem=True,      # 파일 저장 필요
    needs_subagent=True         # 서브에이전트 사용 가능
)

# 3. Worker 실행
result = worker.invoke({
    "messages": [{"role": "user", "content": "애플 주식 조사"}],
    "task": "애플 주식 조사"
})
```


## 🔄 자동 Worker 선택 로직

OrchestratorAgent가 작업을 분석하면:

1. **복잡한 워크플로우 패턴 감지** (예: "병렬", "평가-최적화")
   → LangGraph 직접 사용 Worker 선택

2. **Planning + Filesystem + SubAgent 모두 필요**
   → deepagent Worker 선택 (create_deep_agent())
   → 자동 포함 기능:
      - write_todos: 작업 분해
      - ls, read_file, write_file, edit_file: 파일 관리
      - task: 서브에이전트 생성

3. **기본 경우**
   → LangGraph 직접 사용 Worker 선택


## 📊 주식 자료조사 시나리오

요청: "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘"

1. OrchestratorAgent.analyze_task()
   → 복잡도: "high"
   → requires_planning: true (보고서 구조 계획)
   → requires_filesystem: true (중간 데이터 및 보고서 저장)
   → requires_subagent: true (특정 주식 분석 위임 가능)

2. OrchestratorAgent.determine_worker_requirements()
   → worker_type: "deepagent" (Planning + Filesystem + SubAgent 모두 필요)
   → worker_model: "ollama:qwen2.5-coder:latest"

3. OrchestratorAgent.route_to_worker()
   → 작업에 "주식", "조사" 키워드 포함 → brave_search_tool 자동 추가
   → WorkerFactory.create_worker(..., tools=[brave_search_tool])
   → create_deep_agent()로 Worker 생성
   → Worker 실행

4. deepagent Worker 실행
   → write_todos: 조사 계획 수립
      - 1단계: 애플 주식 최신 정보 검색
      - 2단계: 재무 정보 분석
      - 3단계: 투자 보고서 작성
   → brave_search: 웹 검색으로 정보 수집
   → 파일 시스템: 중간 결과 저장
   → 보고서 작성 및 저장

5. OrchestratorAgent.synthesize_results()
   → Worker 결과 종합
   → 최종 보고서 생성
   → 사용자에게 반환
    """)
    
    print("=" * 70)


def test_simple():
    """간단한 테스트 실행"""
    print("\n" + "=" * 70)
    print("🧪 간단한 테스트 실행")
    print("=" * 70)
    
    # 환경 확인
    print("\n1️⃣ 환경 확인...")
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("⚠️  OLLAMA_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   테스트를 건너뜁니다.")
        return False
    
    print(f"✅ OLLAMA_API_KEY 확인됨: {api_key[:10]}...")
    
    brave_key = os.environ.get("BRAVE_API_KEY")
    if brave_key:
        print(f"✅ BRAVE_API_KEY 확인됨: {brave_key[:10]}...")
    else:
        print("⚠️  BRAVE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   웹 검색 기능이 제한될 수 있습니다.")
    
    # OrchestratorAgent 생성
    print("\n2️⃣ OrchestratorAgent 생성...")
    try:
        orchestrator = OrchestratorAgent(
            orchestrator_model="ollama:gpt-oss:120b-cloud"
        )
        
        if not orchestrator.is_ready():
            print("❌ OrchestratorAgent 초기화 실패")
            return False
        
        print("✅ OrchestratorAgent 생성 완료")
        
        # 정보 출력
        info = orchestrator.get_info()
        print(f"   타입: {info['type']}")
        print(f"   모델: {info['model']}")
        print(f"   노드: {', '.join(info['nodes'])}")
        
    except Exception as e:
        print(f"❌ OrchestratorAgent 생성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 간단한 테스트 쿼리
    print("\n3️⃣ 테스트 쿼리 실행...")
    test_query = "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘"
    print(f"   쿼리: {test_query}\n")
    
    try:
        print("🚀 OrchestratorAgent 실행 중...\n")
        response = orchestrator.generate_response(test_query)
        
        print("\n" + "=" * 70)
        print("📝 최종 응답:")
        print("=" * 70)
        print(response[:2000] if len(response) > 2000 else response)  # 처음 2000자만 출력
        if len(response) > 2000:
            print(f"\n... (응답이 길어서 처음 2000자만 표시했습니다. 전체 길이: {len(response)}자)")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 주식 자료조사 및 보고서 에이전트 테스트")
    print("=" * 70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 사용법 설명
    print_usage_explanation()
    
    # 테스트 실행
    print("\n\n")
    success = test_simple()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 테스트 완료!")
    else:
        print("⚠️  테스트가 건너뛰어졌거나 실패했습니다.")
        print("   환경변수 설정 후 다시 시도해주세요.")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

