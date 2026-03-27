#!/usr/bin/env python3
"""
토큰 사용량 추적 기능 테스트

TokenUsageTracker 유틸리티 및 Agent 통합 테스트
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 환경변수 로드
load_dotenv()

from src.utils.token_usage_tracker import TokenUsageTracker
from src.agents.study.langgraph_agent_tools import LangGraphAgentTools
from langchain.messages import AIMessage


def test_token_usage_tracker_initialization():
    """TokenUsageTracker 초기화 테스트"""
    print("\n" + "=" * 60)
    print("🧪 TokenUsageTracker 초기화 테스트")
    print("=" * 60)
    
    try:
        tracker = TokenUsageTracker()
        assert tracker is not None, "Tracker가 생성되어야 합니다"
        assert tracker.usage_metadata_callback is not None, "Callback이 초기화되어야 합니다"
        
        callback = tracker.get_callback()
        assert callback is not None, "Callback이 반환되어야 합니다"
        
        print("✅ TokenUsageTracker 초기화 성공")
        return True
    except Exception as e:
        print(f"❌ 초기화 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_token_usage_extraction():
    """토큰 정보 추출 테스트"""
    print("\n" + "=" * 60)
    print("🧪 토큰 정보 추출 테스트")
    print("=" * 60)
    
    try:
        tracker = TokenUsageTracker()
        
        # Mock AIMessage with usage_metadata
        mock_message = AIMessage(
            content="Test response",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30
            }
        )
        
        usage = tracker.extract_from_message(mock_message)
        assert usage is not None, "토큰 정보가 추출되어야 합니다"
        assert usage["input_tokens"] == 10, "입력 토큰 수가 정확해야 합니다"
        assert usage["output_tokens"] == 20, "출력 토큰 수가 정확해야 합니다"
        assert usage["total_tokens"] == 30, "총 토큰 수가 정확해야 합니다"
        
        print("✅ 토큰 정보 추출 성공")
        print(f"   입력 토큰: {usage['input_tokens']}")
        print(f"   출력 토큰: {usage['output_tokens']}")
        print(f"   총 토큰: {usage['total_tokens']}")
        return True
    except Exception as e:
        print(f"❌ 추출 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_token_usage_aggregation():
    """토큰 사용량 집계 테스트"""
    print("\n" + "=" * 60)
    print("🧪 토큰 사용량 집계 테스트")
    print("=" * 60)
    
    try:
        tracker = TokenUsageTracker()
        
        # 초기 상태
        current_state = {
            "total": {
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300
            },
            "by_model": {
                "test-model": {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "total_tokens": 300,
                    "call_count": 1
                }
            }
        }
        
        # 새로운 사용량
        new_usage = {
            "input_tokens": 50,
            "output_tokens": 75,
            "total_tokens": 125
        }
        
        # 집계
        updated_state = tracker.aggregate_usage(
            current_state,
            new_usage,
            model_name="test-model"
        )
        
        # 검증
        assert updated_state["total"]["input_tokens"] == 150, "총 입력 토큰이 집계되어야 합니다"
        assert updated_state["total"]["output_tokens"] == 275, "총 출력 토큰이 집계되어야 합니다"
        assert updated_state["total"]["total_tokens"] == 425, "총 토큰이 집계되어야 합니다"
        assert updated_state["by_model"]["test-model"]["call_count"] == 2, "호출 횟수가 증가해야 합니다"
        
        print("✅ 토큰 사용량 집계 성공")
        print(f"   총 입력 토큰: {updated_state['total']['input_tokens']}")
        print(f"   총 출력 토큰: {updated_state['total']['output_tokens']}")
        print(f"   총 토큰: {updated_state['total']['total_tokens']}")
        print(f"   모델별 호출 횟수: {updated_state['by_model']['test-model']['call_count']}")
        return True
    except Exception as e:
        print(f"❌ 집계 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_token_usage_summary():
    """토큰 사용량 요약 테스트"""
    print("\n" + "=" * 60)
    print("🧪 토큰 사용량 요약 테스트")
    print("=" * 60)
    
    try:
        tracker = TokenUsageTracker()
        
        token_usage = {
            "total": {
                "input_tokens": 150,
                "output_tokens": 275,
                "total_tokens": 425
            },
            "by_model": {
                "test-model": {
                    "input_tokens": 150,
                    "output_tokens": 275,
                    "total_tokens": 425,
                    "call_count": 2
                }
            }
        }
        
        summary = tracker.get_summary(token_usage)
        assert summary is not None, "요약이 생성되어야 합니다"
        assert "총: 425" in summary, "총 토큰 수가 포함되어야 합니다"
        assert "입력: 150" in summary, "입력 토큰 수가 포함되어야 합니다"
        assert "출력: 275" in summary, "출력 토큰 수가 포함되어야 합니다"
        
        print("✅ 토큰 사용량 요약 성공")
        print(f"\n📊 요약:\n{summary}")
        return True
    except Exception as e:
        print(f"❌ 요약 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_token_tracking():
    """Agent 통합 토큰 추적 테스트"""
    print("\n" + "=" * 60)
    print("🧪 Agent 통합 토큰 추적 테스트")
    print("=" * 60)
    
    try:
        # Agent 생성
        print("\n1️⃣ Agent 생성 중...")
        agent = LangGraphAgentTools()
        
        if not agent.is_ready():
            print("❌ Agent 초기화 실패")
            return False
        
        print("✅ Agent 준비 완료!")
        
        # 간단한 쿼리로 테스트
        print("\n2️⃣ 토큰 추적 테스트...")
        test_query = "안녕하세요"
        print(f"   요청: {test_query}")
        
        print("\n3️⃣ 응답 생성 중...")
        response = agent.generate_response(test_query)
        
        print("\n4️⃣ 결과 확인:")
        print(response)
        
        # State에서 토큰 사용량 확인
        print("\n5️⃣ State에서 토큰 사용량 확인...")
        # generate_response는 문자열만 반환하므로, 그래프를 직접 호출하여 State 확인
        initial_state = {
            "messages": [],
            "user_query": test_query,
            "model_response": "",
            "tool_calls": [],
            "tool_results": [],
            "llm_calls": 0,
            "tool_calls_count": 0,
            "token_usage": {
                "total": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                },
                "by_model": {}
            }
        }
        
        # Checkpointer가 있으면 thread_id 제공
        if agent.checkpointer:
            config = {"configurable": {"thread_id": "test-token-tracking"}}
            result = agent.graph.invoke(initial_state, config)
        else:
            result = agent.graph.invoke(initial_state)
        token_usage = result.get("token_usage", {})
        
        if token_usage:
            print("✅ 토큰 사용량이 State에 저장되었습니다!")
            print(f"   총 토큰: {token_usage.get('total', {}).get('total_tokens', 0)}")
            print(f"   입력 토큰: {token_usage.get('total', {}).get('input_tokens', 0)}")
            print(f"   출력 토큰: {token_usage.get('total', {}).get('output_tokens', 0)}")
            
            # 모델별 통계 확인
            by_model = token_usage.get("by_model", {})
            if by_model:
                print(f"\n   모델별 통계:")
                for model_name, usage in by_model.items():
                    print(f"     • {model_name}: {usage.get('total_tokens', 0)} 토큰 (호출: {usage.get('call_count', 0)}회)")
        else:
            print("⚠️ 토큰 사용량 정보가 없습니다 (모델이 토큰 정보를 제공하지 않을 수 있음)")
        
        print("\n✅ Agent 통합 테스트 완료!")
        return True
    except Exception as e:
        print(f"❌ Agent 통합 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_calls_aggregation():
    """여러 호출에 대한 토큰 집계 테스트"""
    print("\n" + "=" * 60)
    print("🧪 여러 호출 토큰 집계 테스트")
    print("=" * 60)
    
    try:
        agent = LangGraphAgentTools()
        
        if not agent.is_ready():
            print("❌ Agent 초기화 실패")
            return False
        
        print("✅ Agent 준비 완료!")
        
        # 여러 번 호출하여 집계 확인
        queries = ["안녕하세요", "반갑습니다", "고마워요"]
        total_token_usage = None
        
        for i, query in enumerate(queries, 1):
            print(f"\n{i}️⃣ 호출 {i}: {query}")
            
            initial_state = {
                "messages": [],
                "user_query": query,
                "model_response": "",
                "tool_calls": [],
                "tool_results": [],
                "llm_calls": 0,
                "tool_calls_count": 0,
                "token_usage": total_token_usage or {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0
                    },
                    "by_model": {}
                }
            }
            
            # Checkpointer가 있으면 thread_id 제공
            if agent.checkpointer:
                config = {"configurable": {"thread_id": f"test-multiple-calls-{i}"}}
                result = agent.graph.invoke(initial_state, config)
            else:
                result = agent.graph.invoke(initial_state)
            total_token_usage = result.get("token_usage", {})
            
            if total_token_usage:
                total = total_token_usage.get("total", {})
                print(f"   누적 토큰: {total.get('total_tokens', 0)}")
        
        if total_token_usage:
            print(f"\n✅ 최종 집계 결과:")
            total = total_token_usage.get("total", {})
            print(f"   총 입력 토큰: {total.get('input_tokens', 0)}")
            print(f"   총 출력 토큰: {total.get('output_tokens', 0)}")
            print(f"   총 토큰: {total.get('total_tokens', 0)}")
            
            by_model = total_token_usage.get("by_model", {})
            if by_model:
                print(f"\n   모델별 통계:")
                for model_name, usage in by_model.items():
                    print(f"     • {model_name}: {usage.get('total_tokens', 0)} 토큰 (호출: {usage.get('call_count', 0)}회)")
        
        print("\n✅ 여러 호출 집계 테스트 완료!")
        return True
    except Exception as e:
        print(f"❌ 여러 호출 집계 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("🚀 토큰 사용량 추적 기능 테스트 시작")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 단위 테스트
    results.append(("TokenUsageTracker 초기화", test_token_usage_tracker_initialization()))
    results.append(("토큰 정보 추출", test_token_usage_extraction()))
    results.append(("토큰 사용량 집계", test_token_usage_aggregation()))
    results.append(("토큰 사용량 요약", test_token_usage_summary()))
    
    # 통합 테스트
    results.append(("Agent 통합 토큰 추적", test_agent_token_tracking()))
    results.append(("여러 호출 토큰 집계", test_multiple_calls_aggregation()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {test_name}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

