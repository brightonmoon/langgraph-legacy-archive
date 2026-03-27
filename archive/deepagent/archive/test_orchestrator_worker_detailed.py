#!/usr/bin/env python3
"""
Orchestrator-Worker 패턴 개선된 테스트 스크립트

DeepAgent의 내부 동작을 상세히 추적하고 상태를 확인할 수 있도록 개선.
"""

import sys
import os
import json

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator_worker import OrchestratorWorkerAgent


def analyze_deepagent_result(worker_result, worker_name):
    """DeepAgent Worker 결과 상세 분석"""
    print(f"\n   📊 {worker_name} 상세 분석:")
    print("   " + "=" * 50)
    
    messages = worker_result.get("messages", [])
    print(f"   총 메시지 수: {len(messages)}")
    
    # 메시지별 분석
    for i, msg in enumerate(messages):
        print(f"\n   메시지 {i+1}:")
        
        # 메시지 타입 확인
        if hasattr(msg, 'type'):
            print(f"     타입: {msg.type}")
        elif isinstance(msg, dict):
            print(f"     Role: {msg.get('role', 'unknown')}")
        
        # Content 확인
        if hasattr(msg, 'content'):
            content = msg.content
        elif isinstance(msg, dict):
            content = msg.get('content', '')
        else:
            content = str(msg)
        
        print(f"     Content: {content[:150]}..." if len(content) > 150 else f"     Content: {content}")
        
        # Tool calls 확인
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"     🔧 Tool 호출: {len(msg.tool_calls)}개")
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get('name', 'unknown') if isinstance(tool_call, dict) else getattr(tool_call, 'name', 'unknown')
                print(f"       - {tool_name}")
    
    print("   " + "=" * 50)


def test_orchestrator_worker():
    """Orchestrator-Worker 패턴 테스트 (개선된 버전)"""
    print("=" * 60)
    print("Orchestrator-Worker 패턴 테스트 (상세 추적 버전)")
    print("=" * 60)
    
    try:
        # 에이전트 생성
        print("\n1. 에이전트 생성 중...")
        print("   Orchestrator: gpt-oss:120b-cloud (Cloud - 작업 분해 및 관리)")
        print("   Worker: qwen2.5-coder:latest (로컬 Ollama - 실제 작업 수행)")
        
        agent = OrchestratorWorkerAgent(
            orchestrator_model="gpt-oss:120b-cloud",
            worker_model="qwen2.5-coder:latest",
            use_ollama=True
        )
        
        # 에이전트 정보 출력
        print("\n2. 에이전트 정보:")
        info = agent.get_info()
        for key, value in info.items():
            if key == "features":
                print(f"   {key}:")
                for feature in value:
                    print(f"     - {feature}")
            else:
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
        print("=" * 60)
        
        # 4-1. 작업 분석 결과
        if result.get("task_description"):
            print(f"\n📋 작업 분석 결과:")
            print(f"{result['task_description']}\n")
        
        # 4-2. 분해된 작업들
        if result.get("subtasks"):
            print(f"\n📝 분해된 작업 목록 ({len(result['subtasks'])}개):")
            for subtask in result['subtasks']:
                print(f"   [{subtask.get('id', '?')}] {subtask.get('task', '작업명 없음')}")
                print(f"      설명: {subtask.get('description', '설명 없음')[:100]}...")
        
        # 4-3. Worker 결과 (상세 분석)
        if result.get("worker_results"):
            print(f"\n👥 Worker 결과 상세 분석 ({len(result['worker_results'])}개):")
            for worker_name, worker_result in result['worker_results'].items():
                print(f"\n   {worker_name}:")
                print(f"   작업: {worker_result.get('subtask', {}).get('task', '알 수 없음')}")
                print(f"   결과: {worker_result.get('result', '')[:200]}...")
                
                # DeepAgent 내부 상태 분석 (가능한 경우)
                # 참고: worker_result는 딕셔너리지만, 
                # 실제 DeepAgent의 worker_result는 invoke() 반환값이므로
                # messages를 직접 확인하려면 delegate_to_worker를 수정해야 함
        
        # 4-4. 최종 통합 결과
        if result.get("final_result"):
            print(f"\n✨ 최종 통합 결과:")
            print(f"{result['final_result']}\n")
        
        # 4-5. 통계
        print(f"\n📊 실행 통계:")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}회")
        print(f"   상태: {result.get('status', 'unknown')}")
        print(f"   분해된 작업 수: {len(result.get('subtasks', []))}개")
        print(f"   Worker 실행 수: {len(result.get('worker_results', {}))}개")
        
        # 4-6. 상태 JSON 저장 (선택사항)
        save_state = input("\n💾 상태를 JSON 파일로 저장하시겠습니까? (y/n): ").strip().lower()
        if save_state == 'y':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"orchestrator_worker_state_{timestamp}.json"
            
            # JSON 직렬화 가능한 형태로 변환
            json_state = {
                "user_query": result.get("user_query"),
                "task_description": result.get("task_description"),
                "subtasks": result.get("subtasks"),
                "worker_results": {
                    name: {
                        "subtask": res.get("subtask"),
                        "result": res.get("result")[:1000]  # 길이 제한
                    }
                    for name, res in result.get("worker_results", {}).items()
                },
                "final_result": result.get("final_result"),
                "llm_calls": result.get("llm_calls"),
                "status": result.get("status")
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_state, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ 상태가 {filename}에 저장되었습니다.")
        
        print("\n" + "=" * 60)
        print("✅ 테스트 완료!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    from datetime import datetime
    success = test_orchestrator_worker()
    sys.exit(0 if success else 1)







