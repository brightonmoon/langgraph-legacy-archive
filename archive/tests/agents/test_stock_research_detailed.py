#!/usr/bin/env python3
"""
주식 자료조사 및 보고서 에이전트 상세 테스트

OrchestratorAgent와 WorkerFactory 사용법을 단계별로 설명하며 테스트합니다.
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

# 직접 import하여 의존성 문제 회피
from src.agents import OrchestratorAgent
from src.agents.worker import WorkerFactory


def explain_step_by_step():
    """단계별 사용법 설명"""
    print("\n" + "=" * 70)
    print("📚 OrchestratorAgent + WorkerFactory 사용법 (단계별 설명)")
    print("=" * 70)
    
    print("""
## 1. OrchestratorAgent 생성

OrchestratorAgent는 하이브리드 아키텍처의 상위 계층으로, 다음 역할을 수행합니다:

```python
from src.agents import OrchestratorAgent

orchestrator = OrchestratorAgent(
    orchestrator_model="ollama:gpt-oss:120b-cloud"  # Orchestrator용 모델
)
```

**OrchestratorAgent의 역할:**
- 작업 분석: 요청을 분석하고 필요한 기능 파악
- Worker 선택: 작업 복잡도에 따라 적절한 Worker 자동 선택
- 결과 통합: Worker의 결과를 종합하여 최종 응답 생성


## 2. 작업 분석 단계 (자동)

OrchestratorAgent가 요청을 분석하면:

```
사용자 요청: "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘"
                    ↓
        OrchestratorAgent.analyze_task()
                    ↓
        작업 분석 결과:
        {
            "complexity": "high",
            "requires_planning": true,      # 보고서 구조 계획 필요
            "requires_filesystem": true,    # 중간 데이터 및 보고서 저장 필요
            "requires_subagent": true,      # 특정 주식 분석을 서브에이전트에게 위임 가능
            "workflow_pattern": null       # 특별한 워크플로우 패턴 없음
        }
```


## 3. Worker 선택 단계 (자동)

OrchestratorAgent.determine_worker_requirements()가 분석 결과를 바탕으로 Worker 선택:

```
작업 분석 결과 분석
    ↓
Planning + Filesystem + SubAgent 모두 필요 → deepagent Worker 선택
    ↓
Worker 요구사항 결정:
{
    "worker_type": "deepagent",           # create_deep_agent() 사용
    "worker_model": "ollama:qwen2.5-coder:latest",  # Worker용 모델
    "needs_planning": true,
    "needs_filesystem": true,
    "needs_subagent": true
}
```


## 4. Worker 생성 및 실행 단계 (자동)

OrchestratorAgent.route_to_worker()가 Worker를 생성하고 작업 위임:

```
WorkerFactory.create_worker(
    worker_type="deepagent",
    model="ollama:qwen2.5-coder:latest",
    tools=[brave_search_tool],  # 작업 분석 기반으로 도구 자동 선택
    needs_planning=True,
    needs_filesystem=True,
    needs_subagent=True
)
    ↓
create_deep_agent() 호출
    ↓
deepagent Worker 생성 (자동으로 다음 기능 포함):
- write_todos: 작업 분해 및 계획 수립
- ls, read_file, write_file, edit_file: 파일 시스템 관리
- task: 서브에이전트 생성
- brave_search: 웹 검색 (전달된 도구)
    ↓
Worker.invoke() 실행
    ↓
작업 수행:
1. write_todos로 조사 계획 수립
2. brave_search로 주식 정보 검색
3. 파일 시스템에 중간 결과 저장
4. 보고서 작성 및 저장
    ↓
결과 반환
```


## 5. 결과 통합 단계 (자동)

OrchestratorAgent.synthesize_results()가 Worker 결과를 종합:

```
Worker 결과 수신
    ↓
복잡도가 높으면 LLM으로 결과 통합
    ↓
최종 보고서 생성
    ↓
사용자에게 반환
```


## 6. 직접 WorkerFactory 사용 (고급)

필요시 OrchestratorAgent 없이 직접 WorkerFactory를 사용할 수도 있습니다:

```python
from src.agents import WorkerFactory
from src.tools.factory import ToolFactory

worker_factory = WorkerFactory()

# 주식 조사용 Worker 생성
worker = worker_factory.create_worker(
    worker_type="deepagent",  # 또는 "auto"로 자동 선택
    model="ollama:qwen2.5-coder:latest",
    tools=[ToolFactory.get_all_tools()[2]],  # brave_search_tool
    needs_planning=True,
    needs_filesystem=True,
    needs_subagent=True
)

# Worker 실행
result = worker.invoke({
    "messages": [{"role": "user", "content": "애플 주식 조사"}],
    "task": "애플 주식 조사"
})
```
    """)
    
    print("=" * 70)


def test_orchestrator_agent():
    """OrchestratorAgent 직접 테스트"""
    print("\n" + "=" * 70)
    print("🧪 OrchestratorAgent 직접 테스트")
    print("=" * 70)
    
    # OrchestratorAgent 생성
    print("\n1️⃣ OrchestratorAgent 생성 중...")
    orchestrator = OrchestratorAgent(orchestrator_model="ollama:gpt-oss:120b-cloud")
    
    if not orchestrator.is_ready():
        print("❌ OrchestratorAgent 초기화 실패")
        return False
    
    print("✅ OrchestratorAgent 생성 완료")
    
    # 정보 출력
    info = orchestrator.get_info()
    print(f"\n📋 OrchestratorAgent 정보:")
    print(f"   타입: {info['type']}")
    print(f"   모델: {info['model']}")
    print(f"   노드: {', '.join(info['nodes'])}")
    
    # 테스트 쿼리
    test_query = "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘"
    
    print(f"\n2️⃣ 테스트 쿼리 실행:")
    print(f"   {test_query}\n")
    
    try:
        response = orchestrator.generate_response(test_query)
        
        print("\n" + "=" * 70)
        print("📝 최종 응답:")
        print("=" * 70)
        print(response)
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_worker_factory_directly():
    """WorkerFactory 직접 사용 테스트"""
    print("\n" + "=" * 70)
    print("🧪 WorkerFactory 직접 사용 테스트")
    print("=" * 70)
    
    print("\n1️⃣ WorkerFactory 생성 중...")
    worker_factory = WorkerFactory()
    print("✅ WorkerFactory 생성 완료")
    
    print("\n2️⃣ 주식 조사용 deepagent Worker 생성 중...")
    
    # 도구 준비
    try:
        from src.tools.factory import ToolFactory
        all_tools = ToolFactory.get_all_tools()
        brave_search = None
        for tool in all_tools:
            if tool.name == "brave_search":
                brave_search = tool
                break
    except ImportError as e:
        # ToolFactory import 실패 시 직접 import
        from src.tools.brave_search import brave_search_tool
        brave_search = brave_search_tool
    
    if not brave_search:
        print("❌ brave_search_tool을 찾을 수 없습니다.")
        return False
    
    print(f"✅ brave_search_tool 준비 완료")
    
    try:
        # deepagent Worker 생성
        worker = worker_factory.create_worker(
            worker_type="deepagent",
            model="ollama:qwen2.5-coder:latest",
            tools=[brave_search],
            needs_planning=True,
            needs_filesystem=True,
            needs_subagent=True
        )
        
        print("✅ Worker 생성 완료")
        print(f"   Worker 타입: deepagent (create_deep_agent)")
        print(f"   포함된 도구: brave_search")
        print(f"   자동 기능: Planning, Filesystem, SubAgent")
        
        # Worker 실행
        print("\n3️⃣ Worker 실행 중...")
        test_query = "애플(AAPL) 주식의 최근 실적을 간단히 조사해줘"
        
        result = worker.invoke({
            "messages": [{"role": "user", "content": test_query}],
            "task": test_query
        })
        
        print("\n" + "=" * 70)
        print("📝 Worker 실행 결과:")
        print("=" * 70)
        
        # 결과 포맷팅
        if isinstance(result, dict):
            if "messages" in result:
                messages = result["messages"]
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        print(last_message.content)
                    else:
                        print(str(last_message))
                else:
                    print(str(result))
            else:
                print(str(result))
        else:
            print(str(result))
        
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Worker 생성 또는 실행 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 주식 자료조사 및 보고서 에이전트 상세 테스트")
    print("=" * 70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 환경 확인
    print("\n🔍 환경 확인 중...")
    if not os.environ.get("OLLAMA_API_KEY"):
        print("❌ OLLAMA_API_KEY 환경변수가 설정되지 않았습니다.")
        return 1
    
    if not os.environ.get("BRAVE_API_KEY"):
        print("⚠️  BRAVE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   웹 검색 기능이 제한될 수 있습니다.")
    
    print("✅ 환경 확인 완료\n")
    
    # 1. 사용법 설명
    explain_step_by_step()
    
    # 2. OrchestratorAgent 테스트
    print("\n\n" + "=" * 70)
    print("테스트 1: OrchestratorAgent 직접 사용")
    print("=" * 70)
    success1 = test_orchestrator_agent()
    
    # 3. WorkerFactory 직접 사용 테스트
    print("\n\n" + "=" * 70)
    print("테스트 2: WorkerFactory 직접 사용")
    print("=" * 70)
    success2 = test_worker_factory_directly()
    
    # 결과 요약
    print("\n\n" + "=" * 70)
    print("📊 테스트 결과 요약")
    print("=" * 70)
    print(f"테스트 1 (OrchestratorAgent): {'✅ 성공' if success1 else '❌ 실패'}")
    print(f"테스트 2 (WorkerFactory 직접): {'✅ 성공' if success2 else '❌ 실패'}")
    print("=" * 70)
    
    if success1 or success2:
        print("\n✅ 일부 테스트가 성공했습니다.")
        return 0
    else:
        print("\n❌ 모든 테스트가 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

