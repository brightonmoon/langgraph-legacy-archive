#!/usr/bin/env python3
"""
주식 자료조사 및 보고서 에이전트 테스트

OrchestratorAgent와 WorkerFactory를 사용하여 주식 자료조사 및 보고서 작성 에이전트를 테스트합니다.

아키텍처:
1. OrchestratorAgent (상위 계층)
   - 작업 분석: 주식 조사 요청을 분석하고 필요한 기능 파악
   - Worker 선택: Planning + Filesystem + SubAgent 필요 → deepagent Worker 자동 선택
   - 결과 통합: Worker의 조사 결과를 종합하여 최종 보고서 생성

2. Worker (하위 계층)
   - deepagent Worker: Planning, Filesystem, SubAgent 기능 자동 포함
   - brave_search_tool: 웹 검색 기능 제공
   - 자동 작업 분해 및 계획 수립
   - 파일 시스템을 통한 중간 결과 저장 및 보고서 작성

사용 방법:
1. OrchestratorAgent 생성
2. 주식 조사 요청 전달
3. OrchestratorAgent가 자동으로:
   - 작업 분석 → Planning + Filesystem + SubAgent 필요 감지
   - deepagent Worker 생성 (brave_search_tool 포함)
   - Worker에게 작업 위임
   - 결과 통합 및 최종 보고서 생성
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

from src.agents import OrchestratorAgent
from src.tools.factory import ToolFactory


def test_stock_research_agent():
    """주식 자료조사 및 보고서 에이전트 테스트"""
    print("=" * 70)
    print("📊 주식 자료조사 및 보고서 에이전트 테스트")
    print("=" * 70)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 환경 설정 확인
    print("🔍 환경 설정 확인 중...")
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("❌ OLLAMA_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
    
    brave_key = os.environ.get("BRAVE_API_KEY")
    if not brave_key:
        print("⚠️  BRAVE_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   웹 검색 기능이 제한될 수 있습니다.")
    else:
        print(f"✅ BRAVE_API_KEY 확인됨: {brave_key[:10]}...")
    
    print(f"✅ OLLAMA_API_KEY 확인됨: {api_key[:10]}...\n")
    
    # 2. OrchestratorAgent 생성
    print("🏗️  OrchestratorAgent 생성 중...")
    try:
        orchestrator = OrchestratorAgent(
            orchestrator_model="ollama:gpt-oss:120b-cloud"
        )
        
        if not orchestrator.is_ready():
            print("❌ OrchestratorAgent 초기화 실패")
            return False
        
        print("✅ OrchestratorAgent 생성 완료\n")
        
        # OrchestratorAgent 정보 출력
        info = orchestrator.get_info()
        print("📋 OrchestratorAgent 정보:")
        print(f"   타입: {info['type']}")
        print(f"   모델: {info['model']}")
        print(f"   아키텍처: {info['architecture']}")
        print(f"   기능: {', '.join(info['features'])}")
        print(f"   노드: {', '.join(info['nodes'])}")
        print()
        
    except Exception as e:
        print(f"❌ OrchestratorAgent 생성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 테스트 쿼리 실행
    test_queries = [
        "애플(AAPL) 주식에 대한 최신 자료를 조사하고 투자 보고서를 작성해줘",
        # "테슬라(TSLA)의 최근 실적과 주가 동향을 분석하여 보고서로 작성해줘"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print("-" * 70)
        print(f"테스트 {i}/{len(test_queries)}: {query}")
        print("-" * 70)
        
        try:
            # OrchestratorAgent 실행
            print("\n🚀 OrchestratorAgent 실행 중...\n")
            
            response = orchestrator.generate_response(query)
            
            print("\n" + "=" * 70)
            print("📝 최종 응답:")
            print("=" * 70)
            print(response)
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ 실행 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
    
    print("✅ 모든 테스트 완료!")
    return True


def explain_architecture():
    """아키텍처 설명"""
    print("\n" + "=" * 70)
    print("📚 OrchestratorAgent + WorkerFactory 아키텍처 설명")
    print("=" * 70)
    
    print("""
1. OrchestratorAgent (상위 계층)
   └─ 역할: 작업 분석, Worker 선택, 결과 통합
   └─ 노드:
      - analyze_task: 작업 분석 (복잡도, 필요 기능 파악)
      - determine_worker_requirements: Worker 요구사항 결정
      - route_to_worker: 적절한 Worker 생성 및 작업 위임
      - synthesize_results: Worker 결과 종합

2. Worker 선택 로직
   └─ 복잡한 워크플로우 패턴 → LangGraph 직접 사용
   └─ Planning + Filesystem + SubAgent 모두 필요 → create_deep_agent()
   └─ 기본 → LangGraph 직접 사용

3. 주식 자료조사 및 보고서 작성의 경우:
   └─ 작업 분석 결과:
      - requires_planning: true (보고서 구조 계획 필요)
      - requires_filesystem: true (중간 데이터 및 보고서 저장 필요)
      - requires_subagent: true/false (선택적, 특정 주식 분석 위임 가능)
   
   └─ Worker 선택:
      → Planning + Filesystem + SubAgent 모두 필요 → deepagent Worker 선택
      
   └─ deepagent Worker의 자동 기능:
      - write_todos: 작업 분해 및 계획 수립
      - ls, read_file, write_file, edit_file: 파일 시스템 관리
      - task: 서브에이전트 생성 (필요시)

4. 도구 전달
   └─ brave_search_tool을 Worker에 전달하여 웹 검색 기능 제공
   └─ WorkerFactory.create_worker()의 tools 파라미터로 전달

5. 실행 흐름:
   OrchestratorAgent.generate_response(query)
   → analyze_task: 작업 분석
   → determine_worker_requirements: Worker 요구사항 결정
   → route_to_worker: Worker 생성 및 작업 위임
      → WorkerFactory.create_worker(
            worker_type="deepagent",
            model="ollama:qwen2.5-coder:latest",
            tools=[brave_search_tool],
            needs_planning=True,
            needs_filesystem=True,
            needs_subagent=True
         )
      → create_deep_agent()로 Worker 생성
      → Worker.invoke() 실행
   → synthesize_results: 결과 통합
   → 최종 응답 반환
    """)
    
    print("=" * 70)


if __name__ == "__main__":
    # 아키텍처 설명
    explain_architecture()
    
    # 테스트 실행
    print("\n\n")
    success = test_stock_research_agent()
    
    if success:
        print("\n✅ 테스트 성공!")
        sys.exit(0)
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1)

