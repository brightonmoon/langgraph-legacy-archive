"""
Code Generation Agent 파일 경로 추출 기능 테스트

Query에서 파일 경로를 추출하고 context에 설정하는 기능을 테스트합니다.
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
    _extract_file_paths_from_query,
    _extract_natural_language_query_from_messages
)
from src.agents.sub_agents.code_generation_agent.state import CodeGenerationState


def test_extract_file_paths_from_query():
    """파일 경로 추출 함수 테스트"""
    print("\n" + "="*70)
    print("테스트 1: 파일 경로 추출 함수 테스트")
    print("="*70)
    
    # 테스트 데이터 파일 확인
    test_file = project_root / "data" / "DESeq2_counts.csv"
    if not test_file.exists():
        print(f"⚠️ 테스트 파일이 없습니다: {test_file}")
        print("   테스트 파일을 생성하거나 다른 파일을 사용하세요.")
        return False
    
    test_cases = [
        {
            "query": f"/home/doyamoon/agentic_ai/data/DESeq2_counts.csv 해당 파일을 읽고 분석해줘",
            "expected_count": 1,
            "description": "절대 경로 포함 쿼리"
        },
        {
            "query": f"data/DESeq2_counts.csv 파일을 읽어서 분석해줘",
            "expected_count": 1,
            "description": "상대 경로 포함 쿼리"
        },
        {
            "query": f"DESeq2_counts.csv 파일에서 padj < 0.05인 유전자를 추출해줘",
            "expected_count": 1,
            "description": "파일명만 포함 쿼리"
        },
        {
            "query": "파일을 읽어서 분석해줘",
            "expected_count": 0,
            "description": "파일 경로 없는 쿼리"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n테스트 케이스 {i}: {test_case['description']}")
        print(f"  Query: {test_case['query'][:60]}...")
        
        extracted_paths = _extract_file_paths_from_query(test_case['query'])
        print(f"  추출된 경로 수: {len(extracted_paths)}")
        for path in extracted_paths:
            print(f"    - {path}")
        
        success = len(extracted_paths) >= test_case['expected_count']
        results.append((test_case['description'], success))
        
        if success:
            print(f"  ✅ 통과")
        else:
            print(f"  ❌ 실패 (예상: {test_case['expected_count']}개 이상, 실제: {len(extracted_paths)}개)")
    
    all_passed = all(success for _, success in results)
    return all_passed


def test_analyze_requirements_node_with_file_path():
    """analyze_requirements_node에서 파일 경로 추출 테스트"""
    print("\n" + "="*70)
    print("테스트 2: analyze_requirements_node 파일 경로 추출 테스트")
    print("="*70)
    
    # 테스트 데이터 파일 확인
    test_file = project_root / "data" / "DESeq2_counts.csv"
    if not test_file.exists():
        print(f"⚠️ 테스트 파일이 없습니다: {test_file}")
        print("   테스트 파일을 생성하거나 다른 파일을 사용하세요.")
        return False
    
    test_file_str = str(test_file.resolve())
    
    # 테스트 쿼리
    query = f"{test_file_str} 해당 파일을 읽고, 이파일에서 padj < 0.05, |log2FoldChange|> 1 인 유전자를 추출하여 환자데이터를 가지고 설명을 해줘"
    
    print(f"\n📋 테스트 쿼리:")
    print(f"   {query[:80]}...")
    
    # State 생성
    initial_state: CodeGenerationState = {
        "messages": [HumanMessage(content=query)],
        "task_description": query,
        "context": {}
    }
    
    print(f"\n📊 초기 State:")
    print(f"   context: {initial_state.get('context', {})}")
    
    # analyze_requirements_node 실행
    print(f"\n🚀 analyze_requirements_node 실행 중...")
    result_state = analyze_requirements_node(initial_state)
    
    print(f"\n📊 결과 State:")
    print(f"   status: {result_state.get('status')}")
    context = result_state.get("context", {})
    print(f"   context: {context}")
    
    # 파일 경로가 context에 설정되었는지 확인
    csv_file_path = context.get("csv_file_path", "")
    csv_file_paths = context.get("csv_file_paths", [])
    domain = context.get("domain", "")
    
    print(f"\n✅ 검증:")
    print(f"   csv_file_path: {csv_file_path}")
    print(f"   csv_file_paths: {csv_file_paths}")
    print(f"   domain: {domain}")
    
    # 검증
    success = False
    if csv_file_path:
        if Path(csv_file_path).exists():
            print(f"   ✅ 단일 파일 경로 추출 성공: {csv_file_path}")
            success = True
        else:
            print(f"   ❌ 파일 경로는 추출되었지만 파일이 존재하지 않음: {csv_file_path}")
    elif csv_file_paths:
        existing = [p for p in csv_file_paths if Path(p).exists()]
        if existing:
            print(f"   ✅ 다중 파일 경로 추출 성공: {len(existing)}개")
            success = True
        else:
            print(f"   ❌ 파일 경로는 추출되었지만 파일이 존재하지 않음")
    else:
        print(f"   ❌ 파일 경로 추출 실패")
    
    if domain == "csv_analysis":
        print(f"   ✅ 도메인이 자동으로 설정됨: {domain}")
    else:
        print(f"   ⚠️ 도메인이 설정되지 않음 (예상: csv_analysis)")
    
    return success


def test_extract_natural_language_query_from_messages():
    """메시지에서 자연어 쿼리 추출 테스트"""
    print("\n" + "="*70)
    print("테스트 3: 메시지에서 자연어 쿼리 추출 테스트")
    print("="*70)
    
    test_cases = [
        {
            "messages": [HumanMessage(content="파일을 읽어서 분석해줘")],
            "expected": "파일을 읽어서 분석해줘",
            "description": "단일 HumanMessage"
        },
        {
            "messages": [
                HumanMessage(content="첫 번째 메시지"),
                HumanMessage(content="두 번째 메시지 (최신)")
            ],
            "expected": "두 번째 메시지 (최신)",
            "description": "여러 HumanMessage (최신 메시지 추출)"
        },
        {
            "messages": [
                {"role": "user", "content": "딕셔너리 형식 메시지"}
            ],
            "expected": "딕셔너리 형식 메시지",
            "description": "딕셔너리 형식 메시지"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n테스트 케이스 {i}: {test_case['description']}")
        
        extracted = _extract_natural_language_query_from_messages(test_case['messages'])
        print(f"  추출된 쿼리: {extracted}")
        
        success = extracted == test_case['expected']
        results.append((test_case['description'], success))
        
        if success:
            print(f"  ✅ 통과")
        else:
            print(f"  ❌ 실패 (예상: '{test_case['expected']}', 실제: '{extracted}')")
    
    all_passed = all(success for _, success in results)
    return all_passed


def test_full_workflow():
    """전체 워크플로우 테스트"""
    print("\n" + "="*70)
    print("테스트 4: 전체 워크플로우 테스트 (파일 경로 추출 -> context 설정)")
    print("="*70)
    
    # 테스트 데이터 파일 확인
    test_file = project_root / "data" / "DESeq2_counts.csv"
    if not test_file.exists():
        print(f"⚠️ 테스트 파일이 없습니다: {test_file}")
        print("   테스트 파일을 생성하거나 다른 파일을 사용하세요.")
        return False
    
    test_file_str = str(test_file.resolve())
    
    # 실제 에러가 발생한 쿼리와 동일한 형식
    query = f"{test_file_str} 해당 파일을 읽고, 이파일에서 padj < 0.05, |log2FoldChange|> 1 인 유전자를 추출하여 환자데이터를 가지고 설명을 해줘"
    
    print(f"\n📋 테스트 쿼리:")
    print(f"   {query}")
    
    # State 생성 (실제 사용과 동일한 형식)
    initial_state: CodeGenerationState = {
        "messages": [HumanMessage(content=query)],
        "task_description": query,
        "context": {}
    }
    
    # 1. analyze_requirements_node 실행
    print(f"\n1️⃣ analyze_requirements_node 실행...")
    result_state = analyze_requirements_node(initial_state)
    
    context = result_state.get("context", {})
    csv_file_path = context.get("csv_file_path", "")
    csv_file_paths = context.get("csv_file_paths", [])
    
    # 파일 경로가 추출되었는지 확인
    if not csv_file_path and not csv_file_paths:
        print(f"   ❌ 파일 경로 추출 실패")
        return False
    
    print(f"   ✅ 파일 경로 추출 성공")
    if csv_file_path:
        print(f"      - 단일 파일: {csv_file_path}")
    if csv_file_paths:
        print(f"      - 다중 파일: {len(csv_file_paths)}개")
    
    # 2. context에 파일 경로가 제대로 설정되었는지 확인
    print(f"\n2️⃣ context 검증...")
    print(f"   context: {context}")
    
    # 3. 도메인이 설정되었는지 확인
    domain = context.get("domain", "")
    if domain == "csv_analysis":
        print(f"   ✅ 도메인 설정: {domain}")
    else:
        print(f"   ⚠️ 도메인 미설정: {domain}")
    
    # 4. 파일이 실제로 존재하는지 확인
    print(f"\n3️⃣ 파일 존재 확인...")
    if csv_file_path:
        path_obj = Path(csv_file_path)
        if path_obj.exists():
            print(f"   ✅ 파일 존재: {csv_file_path}")
            print(f"      파일 크기: {path_obj.stat().st_size:,} bytes")
        else:
            print(f"   ❌ 파일 없음: {csv_file_path}")
            return False
    
    print(f"\n✅ 전체 워크플로우 테스트 통과!")
    return True


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("Code Generation Agent 파일 경로 추출 기능 테스트 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    print("\n" + "="*70)
    print("테스트 실행 중...")
    print("="*70)
    
    results.append(("메시지에서 자연어 쿼리 추출", test_extract_natural_language_query_from_messages()))
    results.append(("파일 경로 추출 함수", test_extract_file_paths_from_query()))
    results.append(("analyze_requirements_node 파일 경로 추출", test_analyze_requirements_node_with_file_path()))
    results.append(("전체 워크플로우", test_full_workflow()))
    
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
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

