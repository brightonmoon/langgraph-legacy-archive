"""
Python REPL Agent 테스트

LangChain의 Python REPL 도구를 사용하는 에이전트를 테스트합니다.
OSS 모델에서도 정상 동작하는지 확인합니다.

⚠️ 중요 발견:
- codegemma:latest는 tool calling을 지원하지 않습니다
- tool calling을 지원하는 모델(예: gpt-oss:120b-cloud)이 필요합니다

테스트 스키마:
1. 간단한 수학 계산 (1+1, 2*3 등)
2. 변수 할당 및 사용
3. 리스트/딕셔너리 조작
4. 함수 정의 및 호출
5. 에러 처리 (잘못된 코드 실행)
6. 복잡한 계산
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.study.python_repl_agent import create_python_repl_agent


def test_simple_calculation():
    """테스트 1: 간단한 수학 계산"""
    print("\n" + "="*70)
    print("테스트 1: 간단한 수학 계산")
    print("="*70)
    print("⚠️ 참고: codegemma:latest는 tool calling을 지원하지 않을 수 있습니다.")
    print("   tool calling을 지원하는 모델로 테스트합니다: ollama:gpt-oss:120b-cloud")
    print("="*70)
    
    # Tool calling을 지원하는 모델 사용
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "1 + 1을 계산해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_variable_assignment():
    """테스트 2: 변수 할당 및 사용"""
    print("\n" + "="*70)
    print("테스트 2: 변수 할당 및 사용")
    print("="*70)
    
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "x = 10, y = 20으로 설정하고 x + y를 계산해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_list_operations():
    """테스트 3: 리스트/딕셔너리 조작"""
    print("\n" + "="*70)
    print("테스트 3: 리스트/딕셔너리 조작")
    print("="*70)
    
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "리스트 [1, 2, 3, 4, 5]의 합을 계산해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_function_definition():
    """테스트 4: 함수 정의 및 호출"""
    print("\n" + "="*70)
    print("테스트 4: 함수 정의 및 호출")
    print("="*70)
    
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "두 수를 더하는 함수 add(a, b)를 정의하고 add(5, 3)을 호출해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """테스트 5: 에러 처리 (잘못된 코드 실행)"""
    print("\n" + "="*70)
    print("테스트 5: 에러 처리")
    print("="*70)
    
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "print(undefined_variable)를 실행해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        # 에러가 발생해도 에이전트가 처리할 수 있어야 함
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_calculation():
    """테스트 6: 복잡한 계산"""
    print("\n" + "="*70)
    print("테스트 6: 복잡한 계산")
    print("="*70)
    
    agent = create_python_repl_agent(model="ollama:gpt-oss:120b-cloud")
    
    initial_state = {
        "messages": [],
        "query": "1부터 100까지의 합을 계산해주세요",
        "llm_calls": 0,
        "tool_calls_count": 0
    }
    
    try:
        result = agent.invoke(initial_state)
        print(f"\n✅ 실행 결과:")
        print(f"   응답: {result.get('model_response', 'N/A')}")
        print(f"   LLM 호출 횟수: {result.get('llm_calls', 0)}")
        print(f"   Tool 호출 횟수: {result.get('tool_calls_count', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("Python REPL Agent 테스트 시작")
    print("="*70)
    print("목적: LangGraph에서 Python REPL 기능 동작 확인")
    print("특히 OSS 모델에서도 정상 동작하는지 확인")
    print("")
    print("⚠️ 중요 발견:")
    print("   - codegemma:latest는 tool calling을 지원하지 않습니다")
    print("   - tool calling을 지원하는 모델(예: gpt-oss:120b-cloud)로 테스트합니다")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    results.append(("간단한 수학 계산", test_simple_calculation()))
    results.append(("변수 할당 및 사용", test_variable_assignment()))
    results.append(("리스트/딕셔너리 조작", test_list_operations()))
    results.append(("함수 정의 및 호출", test_function_definition()))
    results.append(("에러 처리", test_error_handling()))
    results.append(("복잡한 계산", test_complex_calculation()))
    
    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

