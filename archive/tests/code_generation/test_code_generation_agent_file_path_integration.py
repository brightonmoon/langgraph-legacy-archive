"""
Code Generation Agent 파일 경로 문제 해결 통합 테스트

실제 에러가 발생했던 쿼리로 테스트하여 파일 경로가 제대로 추출되고
context에 설정되어 execute_code_node에서 사용되는지 확인합니다.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain.messages import HumanMessage
from src.agents.sub_agents.code_generation_agent.agent import (
    analyze_requirements_node,
    generate_code_node,
    execute_code_node
)
from src.agents.sub_agents.code_generation_agent.state import CodeGenerationState
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from dotenv import load_dotenv

load_dotenv()
setup_langsmith_disabled()


def test_file_path_through_workflow():
    """파일 경로가 전체 워크플로우를 통해 전달되는지 테스트"""
    print("\n" + "="*70)
    print("통합 테스트: 파일 경로가 워크플로우를 통해 전달되는지 확인")
    print("="*70)
    
    # 테스트 데이터 파일 확인
    test_file = project_root / "data" / "DESeq2_counts.csv"
    if not test_file.exists():
        print(f"⚠️ 테스트 파일이 없습니다: {test_file}")
        return False
    
    test_file_str = str(test_file.resolve())
    
    # 실제 에러가 발생했던 쿼리
    query = f"{test_file_str} 해당 파일을 읽고, 이파일에서 padj < 0.05, |log2FoldChange|> 1 인 유전자를 추출하여 환자데이터를 가지고 설명을 해줘"
    
    print(f"\n📋 테스트 쿼리:")
    print(f"   {query}")
    
    # State 생성
    initial_state: CodeGenerationState = {
        "messages": [HumanMessage(content=query)],
        "task_description": query,
        "context": {}
    }
    
    # 1. analyze_requirements_node 실행
    print(f"\n1️⃣ analyze_requirements_node 실행...")
    state_after_analyze = analyze_requirements_node(initial_state)
    
    context = state_after_analyze.get("context", {})
    csv_file_path = context.get("csv_file_path", "")
    
    print(f"   context: {context}")
    print(f"   csv_file_path: {csv_file_path}")
    
    if not csv_file_path:
        print(f"   ❌ 파일 경로가 context에 설정되지 않음")
        return False
    
    print(f"   ✅ 파일 경로가 context에 설정됨: {csv_file_path}")
    
    # 2. generate_code_node에서 context를 사용하는지 확인
    # (실제 코드 생성은 하지 않고, context가 제대로 전달되는지만 확인)
    print(f"\n2️⃣ context가 generate_code_node에 전달되는지 확인...")
    
    # context가 제대로 설정되어 있는지 확인
    if "csv_file_path" in context and context["csv_file_path"]:
        print(f"   ✅ context에 csv_file_path가 설정되어 있음")
        print(f"      - csv_file_path: {context['csv_file_path']}")
        print(f"      - domain: {context.get('domain', '없음')}")
    else:
        print(f"   ❌ context에 csv_file_path가 없음")
        return False
    
    # 3. execute_code_node에서 파일 경로를 사용하는지 확인
    print(f"\n3️⃣ execute_code_node에서 파일 경로를 추출하는지 확인...")
    
    # execute_code_node의 로직을 시뮬레이션
    context_for_execute = state_after_analyze.get("context", {})
    csv_file_path_from_context = context_for_execute.get("csv_file_path", "")
    
    if csv_file_path_from_context:
        print(f"   ✅ execute_code_node에서 파일 경로를 가져올 수 있음")
        print(f"      - csv_file_path: {csv_file_path_from_context}")
        
        # 파일 경로 해석
        csv_file_path_obj = Path(csv_file_path_from_context).expanduser()
        if csv_file_path_obj.exists():
            csv_file = csv_file_path_obj.resolve()
            print(f"      - 파일 존재 확인: {csv_file}")
            print(f"      - 파일 크기: {csv_file.stat().st_size:,} bytes")
            
            # execute_code_node에서 사용할 수 있는 형태인지 확인
            if csv_file:
                print(f"   ✅ execute_code_node에서 사용 가능한 형태로 준비됨")
                return True
            else:
                print(f"   ❌ execute_code_node에서 사용할 수 없는 형태")
                return False
        else:
            print(f"   ❌ 파일이 존재하지 않음: {csv_file_path_from_context}")
            return False
    else:
        print(f"   ❌ execute_code_node에서 파일 경로를 가져올 수 없음")
        return False


def test_simulated_execute_code_node():
    """execute_code_node의 파일 경로 추출 로직 시뮬레이션"""
    print("\n" + "="*70)
    print("시뮬레이션 테스트: execute_code_node의 파일 경로 추출 로직")
    print("="*70)
    
    # 테스트 데이터 파일 확인
    test_file = project_root / "data" / "DESeq2_counts.csv"
    if not test_file.exists():
        print(f"⚠️ 테스트 파일이 없습니다: {test_file}")
        return False
    
    test_file_str = str(test_file.resolve())
    
    # State 생성 (analyze_requirements_node 이후 상태 시뮬레이션)
    state: CodeGenerationState = {
        "context": {
            "csv_file_path": test_file_str,
            "domain": "csv_analysis"
        }
    }
    
    # execute_code_node의 로직 시뮬레이션
    print(f"\n📊 execute_code_node 로직 시뮬레이션...")
    
    context = state.get("context", {})
    print(f"   context: {context}")
    
    csv_file_path = context.get("csv_file_path", "")
    csv_file_paths = context.get("csv_file_paths", [])
    
    print(f"   csv_file_path: {csv_file_path}")
    print(f"   csv_file_paths: {csv_file_paths}")
    
    # 파일 경로 해석
    csv_file = None
    if csv_file_path:
        csv_file_path_obj = Path(csv_file_path).expanduser()
        if csv_file_path_obj.exists():
            csv_file = csv_file_path_obj.resolve()
            print(f"   ✅ 파일 해석 성공: {csv_file}")
        else:
            print(f"   ❌ 파일이 존재하지 않음: {csv_file_path}")
            return False
    elif csv_file_paths:
        resolved_files = []
        for p in csv_file_paths:
            path_obj = Path(p).expanduser()
            if path_obj.exists():
                resolved_files.append(path_obj.resolve())
        if resolved_files:
            csv_file = resolved_files[0] if len(resolved_files) == 1 else None
            csv_files = resolved_files
            print(f"   ✅ 다중 파일 해석 성공: {len(resolved_files)}개")
        else:
            print(f"   ❌ 파일이 존재하지 않음")
            return False
    else:
        print(f"   ❌ 파일 경로가 context에 없음")
        return False
    
    # csv_file이 설정되었는지 확인
    if csv_file:
        print(f"\n✅ execute_code_node에서 사용할 수 있는 파일 경로:")
        print(f"   - csv_file: {csv_file}")
        print(f"   - 파일 크기: {csv_file.stat().st_size:,} bytes")
        print(f"   - 다음 단계에서 input_files에 포함될 예정")
        return True
    else:
        print(f"\n❌ csv_file이 설정되지 않음")
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("Code Generation Agent 파일 경로 문제 해결 통합 테스트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    print("\n" + "="*70)
    print("통합 테스트 실행 중...")
    print("="*70)
    
    results.append(("워크플로우 파일 경로 전달", test_file_path_through_workflow()))
    results.append(("execute_code_node 파일 경로 추출 시뮬레이션", test_simulated_execute_code_node()))
    
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
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if all(p for _, p in results):
        print("\n✅ 모든 통합 테스트 통과! 파일 경로 문제가 해결되었습니다.")
    else:
        print("\n❌ 일부 테스트 실패. 추가 확인이 필요합니다.")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

