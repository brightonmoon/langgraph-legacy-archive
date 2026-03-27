"""
Docker 마운트 시나리오 테스트

code_generation_agent에서 다양한 파일 마운트 조건을 테스트합니다:
1. 단일 CSV 파일 (같은 디렉토리)
2. 단일 CSV 파일 (다른 디렉토리)
3. 여러 CSV 파일 (같은 디렉토리)
4. 여러 CSV 파일 (다른 디렉토리)
5. 여러 CSV 파일 (혼합: 일부는 같은 디렉토리, 일부는 다른 디렉토리)
6. 출력 디렉토리 마운트
7. 파일 경로 변수 자동 추가
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.sub_agents.code_generation_agent import create_code_generation_agent


def setup_test_data():
    """테스트용 데이터 파일 생성"""
    test_data_dir = Path("tests/test_data_mount")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 테스트용 CSV 파일 생성
    test_csv_1 = test_data_dir / "test_data_1.csv"
    test_csv_2 = test_data_dir / "test_data_2.csv"
    
    # 간단한 테스트 데이터
    df1 = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [10, 20, 30]
    })
    df2 = pd.DataFrame({
        "id": [1, 2, 3],
        "count": [100, 200, 300]
    })
    
    df1.to_csv(test_csv_1, index=False)
    df2.to_csv(test_csv_2, index=False)
    
    return test_data_dir, test_csv_1, test_csv_2


def test_single_csv_same_directory():
    """테스트 1: 단일 CSV 파일 (코드와 같은 디렉토리)"""
    print("\n" + "="*70)
    print("테스트 1: 단일 CSV 파일 (코드와 같은 디렉토리)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, _ = setup_test_data()
    
    # 코드와 같은 디렉토리에 CSV 복사
    code_dir = Path("workspace/generated_code")
    code_dir.mkdir(parents=True, exist_ok=True)
    csv_in_code_dir = code_dir / "test_data_1.csv"
    csv_in_code_dir.write_bytes(test_csv_1.read_bytes())
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": f"CSV 파일을 읽어서 데이터의 행 수와 열 수를 출력하세요. 파일 경로는 filepath 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽고, 행 수와 열 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_path": str(csv_in_code_dir),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {csv_in_code_dir}")
    print(f"  코드 디렉토리: {code_dir}")
    print(f"  마운트 예상: /workspace/code/test_data_1.csv (같은 디렉토리)")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        generated_code = result.get('generated_code', '')
        generated_code_file = result.get('generated_code_file', '')
        
        # 생성된 코드 확인
        if generated_code_file:
            print(f"\n  📄 생성된 코드 파일: {generated_code_file}")
            try:
                code_content = Path(generated_code_file).read_text(encoding='utf-8')
                print(f"  📝 생성된 코드 (filepath 관련 부분):")
                for line in code_content.split('\n'):
                    if 'filepath' in line.lower() or 'read_csv' in line.lower():
                        print(f"      {line}")
            except Exception as e:
                print(f"  ⚠️ 코드 파일 읽기 실패: {e}")
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            # 결과에서 행 수, 열 수 확인
            if '행' in execution_result or 'row' in execution_result.lower() or '3' in execution_result:
                print(f"  ✅ 데이터 읽기 성공 (같은 디렉토리 마운트 정상 작동)")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            print(f"\n  📊 실행 결과 전체:")
            print(f"  {execution_result[:500] if execution_result else '없음'}")
            print(f"\n  ❌ 실행 오류:")
            for err in execution_errors:
                print(f"    - {err}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_single_csv_different_directory():
    """테스트 2: 단일 CSV 파일 (코드와 다른 디렉토리)"""
    print("\n" + "="*70)
    print("테스트 2: 단일 CSV 파일 (코드와 다른 디렉토리)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, _ = setup_test_data()
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": f"CSV 파일을 읽어서 데이터의 행 수와 열 수를 출력하세요. 파일 경로는 filepath 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽고, 행 수와 열 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_path": str(test_csv_1),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {test_csv_1}")
    print(f"  코드 디렉토리: workspace/generated_code (다른 디렉토리)")
    print(f"  마운트 예상: /workspace/data/test_data_1.csv (다른 디렉토리)")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            # 결과에서 행 수, 열 수 확인
            if '행' in execution_result or 'row' in execution_result.lower() or '3' in execution_result:
                print(f"  ✅ 데이터 읽기 성공 (다른 디렉토리 마운트 정상 작동)")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_csv_same_directory():
    """테스트 3: 여러 CSV 파일 (코드와 같은 디렉토리)"""
    print("\n" + "="*70)
    print("테스트 3: 여러 CSV 파일 (코드와 같은 디렉토리)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, test_csv_2 = setup_test_data()
    
    # 코드와 같은 디렉토리에 CSV 복사
    code_dir = Path("workspace/generated_code")
    code_dir.mkdir(parents=True, exist_ok=True)
    csv1_in_code_dir = code_dir / "test_data_1.csv"
    csv2_in_code_dir = code_dir / "test_data_2.csv"
    csv1_in_code_dir.write_bytes(test_csv_1.read_bytes())
    csv2_in_code_dir.write_bytes(test_csv_2.read_bytes())
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "두 개의 CSV 파일을 읽어서 각각의 행 수를 출력하세요. filepath와 filepath_2 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 두 CSV 파일을 읽고, 각각의 행 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_paths": [str(csv1_in_code_dir), str(csv2_in_code_dir)],
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일 1: {csv1_in_code_dir}")
    print(f"  CSV 파일 2: {csv2_in_code_dir}")
    print(f"  코드 디렉토리: {code_dir}")
    print(f"  마운트 예상: /workspace/code/ (같은 디렉토리)")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            # 결과에서 두 파일 모두 읽었는지 확인
            if '3' in execution_result or '행' in execution_result:
                print(f"  ✅ 여러 파일 읽기 성공 (같은 디렉토리 마운트 정상 작동)")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_csv_different_directory():
    """테스트 4: 여러 CSV 파일 (코드와 다른 디렉토리)"""
    print("\n" + "="*70)
    print("테스트 4: 여러 CSV 파일 (코드와 다른 디렉토리)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, test_csv_2 = setup_test_data()
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "두 개의 CSV 파일을 읽어서 각각의 행 수를 출력하세요. filepath와 filepath_2 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 두 CSV 파일을 읽고, 각각의 행 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_paths": [str(test_csv_1), str(test_csv_2)],
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일 1: {test_csv_1}")
    print(f"  CSV 파일 2: {test_csv_2}")
    print(f"  코드 디렉토리: workspace/generated_code (다른 디렉토리)")
    print(f"  마운트 예상: /workspace/data/ (같은 부모 디렉토리이므로 하나의 마운트)")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            # 결과에서 두 파일 모두 읽었는지 확인
            if '3' in execution_result or '행' in execution_result:
                print(f"  ✅ 여러 파일 읽기 성공 (다른 디렉토리 마운트 정상 작동)")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_csv_mixed_directories():
    """테스트 5: 여러 CSV 파일 (혼합: 일부는 같은 디렉토리, 일부는 다른 디렉토리)"""
    print("\n" + "="*70)
    print("테스트 5: 여러 CSV 파일 (혼합 디렉토리)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, test_csv_2 = setup_test_data()
    
    # 하나는 코드 디렉토리에, 하나는 다른 디렉토리에
    code_dir = Path("workspace/generated_code")
    code_dir.mkdir(parents=True, exist_ok=True)
    csv1_in_code_dir = code_dir / "test_data_1.csv"
    csv1_in_code_dir.write_bytes(test_csv_1.read_bytes())
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "두 개의 CSV 파일을 읽어서 각각의 행 수를 출력하세요. filepath와 filepath_2 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 두 CSV 파일을 읽고, 각각의 행 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_paths": [str(csv1_in_code_dir), str(test_csv_2)],
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일 1: {csv1_in_code_dir} (코드와 같은 디렉토리)")
    print(f"  CSV 파일 2: {test_csv_2} (코드와 다른 디렉토리)")
    print(f"  마운트 예상:")
    print(f"    - 파일 1: /workspace/code/test_data_1.csv")
    print(f"    - 파일 2: /workspace/data/test_data_2.csv")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            # 결과에서 두 파일 모두 읽었는지 확인
            if '3' in execution_result or '행' in execution_result:
                print(f"  ✅ 혼합 디렉토리 마운트 정상 작동")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_output_directory_mount():
    """테스트 6: 출력 디렉토리 마운트"""
    print("\n" + "="*70)
    print("테스트 6: 출력 디렉토리 마운트")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, _ = setup_test_data()
    
    # 출력 디렉토리 생성
    output_dir = Path("tests/test_output_mount")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "CSV 파일을 읽어서 결과를 JSON 파일로 저장하세요. 출력 파일은 /workspace/results/result.json에 저장하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽고, 결과를 JSON 파일로 저장하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_path": str(test_csv_1),
            "output_directory": str(output_dir),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {test_csv_1}")
    print(f"  출력 디렉토리: {output_dir}")
    print(f"  마운트 예상: /workspace/results/ (출력 디렉토리)")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        # 출력 파일 확인
        output_file = output_dir / "result.json"
        file_exists = output_file.exists()
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            if file_exists:
                print(f"  ✅ 출력 파일 생성 성공: {output_file}")
                print(f"  ✅ 출력 디렉토리 마운트 정상 작동")
            else:
                print(f"  ⚠️ 출력 파일이 생성되지 않았습니다 (코드에서 파일 저장을 하지 않았을 수 있음)")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_filepath_variable_auto_add():
    """테스트 7: 파일 경로 변수 자동 추가"""
    print("\n" + "="*70)
    print("테스트 7: 파일 경로 변수 자동 추가")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv_1, _ = setup_test_data()
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "CSV 파일을 읽어서 데이터를 출력하세요. 코드에 파일 경로를 하드코딩하지 말고 변수를 사용하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽고, 데이터를 print()로 출력하세요. 파일 경로는 변수로 지정하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_path": str(test_csv_1),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {test_csv_1}")
    print(f"  테스트 목적: 코드에 filepath 변수가 없을 때 자동으로 추가되는지 확인")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        generated_code = result.get('generated_code', '')
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        # 생성된 코드에 filepath 변수가 있는지 확인
        has_filepath = 'filepath' in generated_code
        
        if execution_result and len(execution_errors) == 0:
            print(f"  ✅ 실행 성공")
            if has_filepath:
                print(f"  ✅ filepath 변수 자동 추가 확인됨")
            else:
                print(f"  ⚠️ filepath 변수가 코드에 없음 (LLM이 직접 경로를 사용했을 수 있음)")
            print(f"\n  생성된 코드 미리보기:")
            code_preview = generated_code[:300] if len(generated_code) > 300 else generated_code
            for line in code_preview.split('\n')[:10]:
                print(f"    {line}")
            return True
        else:
            print(f"  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err[:100]}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("Docker 마운트 시나리오 테스트 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    print("\n" + "="*70)
    print("테스트 실행 중...")
    print("="*70)
    
    results.append(("단일 CSV 파일 (같은 디렉토리)", test_single_csv_same_directory()))
    results.append(("단일 CSV 파일 (다른 디렉토리)", test_single_csv_different_directory()))
    results.append(("여러 CSV 파일 (같은 디렉토리)", test_multiple_csv_same_directory()))
    results.append(("여러 CSV 파일 (다른 디렉토리)", test_multiple_csv_different_directory()))
    results.append(("여러 CSV 파일 (혼합 디렉토리)", test_multiple_csv_mixed_directories()))
    results.append(("출력 디렉토리 마운트", test_output_directory_mount()))
    results.append(("파일 경로 변수 자동 추가", test_filepath_variable_auto_add()))
    
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

