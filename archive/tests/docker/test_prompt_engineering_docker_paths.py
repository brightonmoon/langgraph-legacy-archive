"""
Prompt Engineering으로 Docker 경로 인식 테스트

프롬프트 개선 후 LLM이 Docker 경로를 올바르게 생성하는지 테스트합니다.
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
    test_data_dir = Path("tests/test_data_prompt")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 테스트용 CSV 파일 생성
    test_csv = test_data_dir / "test_data.csv"
    
    # 간단한 테스트 데이터
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "value": [10, 20, 30, 40, 50]
    })
    
    df.to_csv(test_csv, index=False)
    
    return test_data_dir, test_csv


def test_prompt_with_docker_path_single_file():
    """테스트 1: 프롬프트에 Docker 경로 정보 포함 (단일 파일)"""
    print("\n" + "="*70)
    print("테스트 1: 프롬프트에 Docker 경로 정보 포함 (단일 파일)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv = setup_test_data()
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "CSV 파일을 읽어서 데이터의 행 수와 열 수를 출력하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽고, 행 수와 열 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_path": str(test_csv),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {test_csv}")
    print(f"  예상 Docker 경로: /workspace/data/test_data.csv")
    print(f"  프롬프트에 Docker 경로 정보 포함 여부 확인")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        generated_code = result.get('generated_code', '')
        generated_code_file = result.get('generated_code_file', '')
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        # 생성된 코드 확인
        if generated_code_file:
            print(f"\n  📄 생성된 코드 파일: {generated_code_file}")
            try:
                code_content = Path(generated_code_file).read_text(encoding='utf-8')
                print(f"  📝 생성된 코드 (filepath 관련 부분):")
                for line in code_content.split('\n'):
                    if 'filepath' in line.lower() or 'read_csv' in line.lower():
                        print(f"      {line}")
                
                # Docker 경로 사용 여부 확인
                has_docker_path = '/workspace/' in code_content
                has_local_path = any(pattern in code_content for pattern in [
                    'workspace/', './', '/home/', test_csv.name
                ])
                
                if has_docker_path and not has_local_path:
                    print(f"\n  ✅ Docker 경로 사용 확인: 프롬프트가 효과적입니다!")
                elif has_docker_path and has_local_path:
                    print(f"\n  ⚠️ Docker 경로와 로컬 경로 혼용: 부분 성공")
                else:
                    print(f"\n  ❌ 로컬 경로 사용: 프롬프트 개선 필요")
            except Exception as e:
                print(f"  ⚠️ 코드 파일 읽기 실패: {e}")
        
        if execution_result and len(execution_errors) == 0:
            print(f"\n  ✅ 실행 성공")
            if '행' in execution_result or 'row' in execution_result.lower() or '5' in execution_result:
                print(f"  ✅ 데이터 읽기 성공")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"\n  ❌ 실행 실패")
            print(f"  📊 실행 결과:")
            print(f"  {execution_result[:300] if execution_result else '없음'}")
            print(f"\n  ❌ 실행 오류:")
            for err in execution_errors:
                print(f"    - {err}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_with_docker_path_multiple_files():
    """테스트 2: 프롬프트에 Docker 경로 정보 포함 (여러 파일)"""
    print("\n" + "="*70)
    print("테스트 2: 프롬프트에 Docker 경로 정보 포함 (여러 파일)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv = setup_test_data()
    
    # 두 번째 파일 생성
    test_csv_2 = test_data_dir / "test_data_2.csv"
    df2 = pd.DataFrame({
        "id": [1, 2, 3],
        "count": [100, 200, 300]
    })
    df2.to_csv(test_csv_2, index=False)
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    initial_state = {
        "messages": [],
        "task_description": "두 개의 CSV 파일을 읽어서 각각의 행 수를 출력하세요.",
        "requirements": "pandas를 사용하여 두 CSV 파일을 읽고, 각각의 행 수를 print()로 출력하세요.",
        "context": {
            "domain": "csv_analysis",
            "csv_file_paths": [str(test_csv), str(test_csv_2)],
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일 1: {test_csv}")
    print(f"  CSV 파일 2: {test_csv_2}")
    print(f"  예상 Docker 경로: /workspace/data/test_data.csv, /workspace/data/test_data_2.csv")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        generated_code = result.get('generated_code', '')
        generated_code_file = result.get('generated_code_file', '')
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        # 생성된 코드 확인
        if generated_code_file:
            print(f"\n  📄 생성된 코드 파일: {generated_code_file}")
            try:
                code_content = Path(generated_code_file).read_text(encoding='utf-8')
                print(f"  📝 생성된 코드 (filepath 관련 부분):")
                for line in code_content.split('\n'):
                    if 'filepath' in line.lower() or 'read_csv' in line.lower():
                        print(f"      {line}")
                
                # Docker 경로 사용 여부 확인
                has_docker_path = '/workspace/' in code_content
                has_multiple_filepaths = 'filepath_2' in code_content or 'filepath2' in code_content.lower()
                
                if has_docker_path and has_multiple_filepaths:
                    print(f"\n  ✅ Docker 경로 및 여러 파일 변수 사용 확인!")
                elif has_docker_path:
                    print(f"\n  ⚠️ Docker 경로는 사용했지만 여러 파일 변수 미사용")
                else:
                    print(f"\n  ❌ Docker 경로 미사용: 프롬프트 개선 필요")
            except Exception as e:
                print(f"  ⚠️ 코드 파일 읽기 실패: {e}")
        
        if execution_result and len(execution_errors) == 0:
            print(f"\n  ✅ 실행 성공")
            print(f"\n  실행 결과 미리보기:")
            print(f"  {execution_result[:200]}...")
            return True
        else:
            print(f"\n  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_without_docker_path_info():
    """테스트 3: Docker 경로 정보 없이 생성 (비교용)"""
    print("\n" + "="*70)
    print("테스트 3: Docker 경로 정보 없이 생성 (비교용)")
    print("="*70)
    
    # 테스트 데이터 준비
    test_data_dir, test_csv = setup_test_data()
    
    agent = create_code_generation_agent(
        orchestrator_model="ollama:gpt-oss:120b-cloud",
        worker_model="ollama:codegemma:latest",
        enable_planning=False,
        enable_filesystem_tools=True,
        enable_execution=True
    )
    
    # Docker 경로 정보 없이 context 제공 (로컬 경로만)
    initial_state = {
        "messages": [],
        "task_description": "CSV 파일을 읽어서 데이터를 출력하세요.",
        "requirements": "pandas를 사용하여 CSV를 읽으세요.",
        "context": {
            "domain": "csv_analysis",
            # docker_file_path 정보 없음 (로컬 경로만)
            "csv_file_path": str(test_csv),
            "docker_image": "csv-sandbox:test"
        },
        "max_iterations": 3
    }
    
    print(f"\n📋 입력:")
    print(f"  CSV 파일: {test_csv}")
    print(f"  Docker 경로 정보: 없음 (프롬프트만으로 처리)")
    print(f"  목적: 프롬프트만으로 Docker 경로를 올바르게 생성하는지 확인")
    
    try:
        print("\n🚀 에이전트 실행 시작...")
        result = agent.invoke(initial_state, config={"recursion_limit": 15})
        
        print("\n✅ 결과:")
        generated_code = result.get('generated_code', '')
        generated_code_file = result.get('generated_code_file', '')
        execution_result = result.get('execution_result', '')
        execution_errors = result.get('execution_errors', [])
        
        # 생성된 코드 확인
        if generated_code_file:
            print(f"\n  📄 생성된 코드 파일: {generated_code_file}")
            try:
                code_content = Path(generated_code_file).read_text(encoding='utf-8')
                print(f"  📝 생성된 코드 (filepath 관련 부분):")
                for line in code_content.split('\n'):
                    if 'filepath' in line.lower() or 'read_csv' in line.lower():
                        print(f"      {line}")
                
                # 경로 사용 패턴 확인
                has_docker_path = '/workspace/' in code_content
                has_local_path = any(pattern in code_content for pattern in [
                    'workspace/', './', '/home/', test_csv.name
                ])
                
                if has_docker_path and not has_local_path:
                    print(f"\n  ✅ 프롬프트만으로 Docker 경로 올바르게 생성!")
                elif has_docker_path and has_local_path:
                    print(f"\n  ⚠️ Docker 경로와 로컬 경로 혼용")
                else:
                    print(f"\n  ❌ 로컬 경로 사용: 프롬프트 개선 필요")
            except Exception as e:
                print(f"  ⚠️ 코드 파일 읽기 실패: {e}")
        
        if execution_result and len(execution_errors) == 0:
            print(f"\n  ✅ 실행 성공")
            return True
        else:
            print(f"\n  ❌ 실행 실패")
            for err in execution_errors:
                print(f"    - {err}")
            return False
            
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("Prompt Engineering Docker 경로 인식 테스트 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    # 테스트 실행
    print("\n" + "="*70)
    print("테스트 실행 중...")
    print("="*70)
    
    results.append(("Docker 경로 정보 포함 (단일 파일)", test_prompt_with_docker_path_single_file()))
    results.append(("Docker 경로 정보 포함 (여러 파일)", test_prompt_with_docker_path_multiple_files()))
    results.append(("프롬프트만으로 처리 (비교용)", test_prompt_without_docker_path_info()))
    
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

