#!/usr/bin/env python3
"""
Orchestrator-Worker 패턴 테스트 스크립트

DeepAgent를 CompiledSubAgent로 사용하는 Orchestrator-Worker 패턴을 테스트합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator_worker import OrchestratorWorkerAgent


def test_orchestrator_worker():
    """Orchestrator-Worker 패턴 테스트"""
    print("=" * 60)
    print("Orchestrator-Worker 패턴 테스트")
    print("=" * 60)
    
    try:
        # 에이전트 생성
        print("\n1. 에이전트 생성 중...")
        print("   Orchestrator: gpt-oss:120b-cloud (Cloud - 작업 분해 및 관리)")
        print("   Worker: qwen2.5-coder:latest (로컬 Ollama - 실제 작업 수행)")
        
        agent = OrchestratorWorkerAgent(
            orchestrator_model="gpt-oss:120b-cloud",  # 상위 Orchestrator는 Cloud 모델
            worker_model="qwen2.5-coder:latest",      # 하위 Worker는 로컬 Ollama 모델
            use_ollama=True
        )
        
        # 에이전트 정보 출력
        print("\n2. 에이전트 정보:")
        info = agent.get_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
        
        # 테스트 쿼리 실행
        print("\n3. 테스트 쿼리 실행:")
        query = "웹 애플리케이션 개발을 위한 계획을 세우고, 각 단계별로 필요한 작업을 수행해주세요."
        print(f"   쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return False
        
        # 결과 출력
        print("\n4. 실행 결과:")
        print("-" * 60)
        
        if result.get("task_description"):
            print(f"\n📋 작업 분석:\n{result['task_description']}\n")
        
        if result.get("worker_results"):
            print(f"\n👥 Worker 결과 ({len(result['worker_results'])}개):")
            for worker_name, worker_result in result['worker_results'].items():
                print(f"\n   {worker_name}:")
                print(f"   {worker_result['result'][:200]}...")
        
        if result.get("final_result"):
            print(f"\n✨ 최종 통합 결과:\n{result['final_result']}\n")
        
        print(f"\n📊 통계:")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}회")
        print(f"   상태: {result.get('status', 'unknown')}")
        
        print("-" * 60)
        print("✅ 테스트 완료!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_orchestrator_worker()
    sys.exit(0 if success else 1)

