"""
코딩 에이전트 통합 테스트

Planning Tool과 Filesystem Tool 통합 테스트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.sub_agents.code_generation_agent import create_code_generation_agent


def test_planning_tool():
    """Planning Tool 통합 테스트"""
    print("\n" + "="*70)
    print("테스트 1: Planning Tool 통합")
    print("="*70)
    
    agent = create_code_generation_agent(
        enable_planning=True,
        enable_filesystem_tools=False
    )
    
    # 테스트 입력
    initial_state = {
        "messages": [],
        "task_description": "간단한 계산기 함수 만들기",
        "requirements": "",
        "context": {"domain": "general"}
    }
    
    print("\n📋 입력:")
    print(f"  작업: {initial_state['task_description']}")
    
    try:
        result = agent.invoke(initial_state)
        
        print("\n✅ 결과:")
        print(f"  상태: {result.get('status', 'N/A')}")
        print(f"  Planning 결과: {result.get('planning_result', 'N/A')[:200] if result.get('planning_result') else 'N/A'}...")
        print(f"  하위 작업 수: {len(result.get('planning_todos', []))}")
        
        if result.get('planning_todos'):
            print("\n  하위 작업 목록:")
            for i, todo in enumerate(result.get('planning_todos', [])[:5], 1):
                print(f"    {i}. {todo.get('task', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_filesystem_tool():
    """Filesystem Tool 통합 테스트"""
    print("\n" + "="*70)
    print("테스트 2: Filesystem Tool 통합")
    print("="*70)
    
    agent = create_code_generation_agent(
        enable_planning=False,
        enable_filesystem_tools=True
    )
    
    # 테스트 입력
    test_filepath = "tests/test_output/test_calculator.py"
    initial_state = {
        "messages": [],
        "task_description": "간단한 계산기 함수 만들기",
        "requirements": "덧셈, 뺄셈, 곱셈, 나눗셈 함수 생성",
        "context": {"domain": "general"},
        "target_filepath": test_filepath
    }
    
    print("\n📋 입력:")
    print(f"  작업: {initial_state['task_description']}")
    print(f"  목표 파일 경로: {test_filepath}")
    
    try:
        result = agent.invoke(initial_state)
        
        print("\n✅ 결과:")
        print(f"  상태: {result.get('status', 'N/A')}")
        print(f"  생성된 코드 길이: {len(result.get('generated_code', ''))} 문자")
        print(f"  생성된 파일: {result.get('generated_code_file', 'N/A')}")
        print(f"  생성된 파일 목록: {result.get('files_created', [])}")
        
        # 파일이 실제로 생성되었는지 확인
        if result.get('files_created'):
            for filepath in result.get('files_created', []):
                if Path(filepath).exists():
                    print(f"  ✅ 파일 존재 확인: {filepath}")
                else:
                    print(f"  ⚠️ 파일 없음: {filepath}")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_integration():
    """전체 통합 테스트 (Planning + Filesystem)"""
    print("\n" + "="*70)
    print("테스트 3: 전체 통합 테스트 (Planning + Filesystem)")
    print("="*70)
    
    agent = create_code_generation_agent(
        enable_planning=True,
        enable_filesystem_tools=True
    )
    
    # 테스트 입력
    test_filepath = "tests/test_output/test_full_integration.py"
    initial_state = {
        "messages": [],
        "task_description": "간단한 웹 서버 만들기",
        "requirements": "Flask를 사용하여 Hello World API 엔드포인트 생성",
        "context": {"domain": "web_development"},
        "target_filepath": test_filepath
    }
    
    print("\n📋 입력:")
    print(f"  작업: {initial_state['task_description']}")
    print(f"  요구사항: {initial_state['requirements']}")
    print(f"  도메인: {initial_state['context']['domain']}")
    print(f"  목표 파일 경로: {test_filepath}")
    
    try:
        result = agent.invoke(initial_state)
        
        print("\n✅ 결과:")
        print(f"  상태: {result.get('status', 'N/A')}")
        
        # Planning 결과
        if result.get('planning_result'):
            print(f"\n  📋 Planning 결과:")
            print(f"    하위 작업 수: {len(result.get('planning_todos', []))}")
            if result.get('planning_todos'):
                for i, todo in enumerate(result.get('planning_todos', [])[:3], 1):
                    print(f"    {i}. {todo.get('task', 'N/A')}")
        
        # 코드 생성 결과
        print(f"\n  💻 코드 생성 결과:")
        print(f"    생성된 코드 길이: {len(result.get('generated_code', ''))} 문자")
        print(f"    생성된 파일: {result.get('generated_code_file', 'N/A')}")
        
        # Filesystem 결과
        if result.get('files_created'):
            print(f"\n  📁 Filesystem 결과:")
            for filepath in result.get('files_created', []):
                exists = Path(filepath).exists()
                print(f"    {'✅' if exists else '❌'} {filepath}")
        
        # 코드 미리보기
        if result.get('generated_code'):
            code_preview = result.get('generated_code', '')[:300]
            print(f"\n  📝 코드 미리보기:")
            print(f"    {code_preview}...")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("코딩 에이전트 통합 테스트 시작")
    print("="*70)
    
    # 테스트 디렉토리 생성
    test_output_dir = Path("tests/test_output")
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # 테스트 실행
    results.append(("Planning Tool", test_planning_tool()))
    results.append(("Filesystem Tool", test_filesystem_tool()))
    results.append(("전체 통합", test_full_integration()))
    
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


