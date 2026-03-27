"""
CSV Data Analysis Agent 디버깅 테스트

csv_data_analysis_agent의 각 로직을 단계별로 검증하여 문제 지점을 찾습니다.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 환경변수 로드
load_dotenv()

import pytest
from src.utils.paths import get_data_directory, get_project_root
from src.tools.csv_tools import read_csv_metadata_tool
from src.agents.sub_agents.csv_data_analysis_agent.agent import (
    _convert_host_paths_to_docker_paths,
    _add_csv_filepath_variables,
)


class TestCSVAgentDebugging:
    """CSV Agent 디버깅 테스트 클래스"""
    
    @pytest.fixture
    def test_csv_file(self):
        """테스트용 CSV 파일 생성"""
        data_dir = get_data_directory()
        test_csv = data_dir / "test_debug.csv"
        
        # 테스트 데이터 생성
        import pandas as pd
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'score': [85, 90, 88]
        })
        df.to_csv(test_csv, index=False)
        
        yield test_csv
        
        # 정리
        if test_csv.exists():
            test_csv.unlink()
    
    def test_1_read_csv_metadata(self, test_csv_file):
        """테스트 1: CSV 메타데이터 읽기"""
        print("\n" + "="*70)
        print("테스트 1: CSV 메타데이터 읽기")
        print("="*70)
        
        try:
            # read_csv_metadata_tool 직접 호출
            result = read_csv_metadata_tool.invoke({"filepath": str(test_csv_file)})
            
            print(f"✅ CSV 메타데이터 읽기 성공")
            print(f"   파일: {test_csv_file}")
            print(f"   결과 길이: {len(result)} 문자")
            print(f"   결과 미리보기:\n{result[:200]}...")
            
            # 검증
            assert "CSV 파일 메타데이터" in result or "파일 정보" in result
            assert "컬럼" in result or "column" in result.lower()
            
            return True
            
        except Exception as e:
            print(f"❌ CSV 메타데이터 읽기 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_2_path_conversion_host_to_docker(self, test_csv_file):
        """테스트 2: 호스트 경로를 도커 경로로 변환"""
        print("\n" + "="*70)
        print("테스트 2: 호스트 경로를 도커 경로로 변환")
        print("="*70)
        
        test_cases = [
            {
                "name": "절대 경로 패턴",
                "code": f'df = pd.read_csv("{test_csv_file}")',
                "expected": "/workspace/data/test_debug.csv"
            },
            {
                "name": "상대 경로 패턴",
                "code": 'df = pd.read_csv("data/test_debug.csv")',
                "expected": "/workspace/data/test_debug.csv"
            },
            {
                "name": "변수 할당 패턴",
                "code": f'filepath = "{test_csv_file}"',
                "expected": "/workspace/data/test_debug.csv"
            },
        ]
        
        all_passed = True
        
        for case in test_cases:
            print(f"\n📝 테스트 케이스: {case['name']}")
            print(f"   입력 코드: {case['code']}")
            
            try:
                result = _convert_host_paths_to_docker_paths(
                    case['code'],
                    str(test_csv_file),
                    []
                )
                
                print(f"   변환 결과: {result}")
                
                # 검증
                if case['expected'] in result:
                    print(f"   ✅ 변환 성공: {case['expected']} 포함")
                else:
                    print(f"   ❌ 변환 실패: {case['expected']} 미포함")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed
    
    def test_3_filename_pattern_replacement(self, test_csv_file):
        """테스트 3: 파일명만 사용하는 패턴 변환"""
        print("\n" + "="*70)
        print("테스트 3: 파일명만 사용하는 패턴 변환")
        print("="*70)
        
        test_cases = [
            {
                "name": "파일명만 사용 (단일 따옴표)",
                "code": "df = pd.read_csv('test_debug.csv')",
                "expected": "filepath"
            },
            {
                "name": "파일명만 사용 (이중 따옴표)",
                "code": 'df = pd.read_csv("test_debug.csv")',
                "expected": "filepath"
            },
            {
                "name": "파일명 + 파라미터",
                "code": 'df = pd.read_csv("test_debug.csv", encoding="utf-8")',
                "expected": "filepath"
            },
            {
                "name": "여러 파일명 사용",
                "code": """
df1 = pd.read_csv('test_debug.csv')
df2 = pd.read_csv('test_debug.csv')
""",
                "expected": "filepath"
            },
        ]
        
        all_passed = True
        
        for case in test_cases:
            print(f"\n📝 테스트 케이스: {case['name']}")
            print(f"   입력 코드:\n{case['code']}")
            
            try:
                # execute_code_node의 파일명 패턴 처리 로직 시뮬레이션
                csv_file_name = test_csv_file.name
                docker_path = f"/workspace/data/{csv_file_name}"
                
                code_to_execute = case['code']
                
                # 파일명만 사용하는 패턴 처리
                if re.search(rf'["\']{re.escape(csv_file_name)}["\']', code_to_execute):
                    # pd.read_csv("파일명") 패턴 교체
                    code_to_execute = re.sub(
                        rf'pd\.read_csv\(["\']{re.escape(csv_file_name)}["\']\)',
                        'pd.read_csv(filepath)',
                        code_to_execute
                    )
                    # pd.read_csv("파일명", ...) 패턴 교체
                    code_to_execute = re.sub(
                        rf'pd\.read_csv\(["\']{re.escape(csv_file_name)}["\']\s*,\s*',
                        'pd.read_csv(filepath, ',
                        code_to_execute
                    )
                
                # filepath 변수 추가
                if 'filepath' not in code_to_execute or not re.search(r'filepath\s*=', code_to_execute):
                    import_pattern = r'(import\s+\w+[^\n]*\n)'
                    if re.search(import_pattern, code_to_execute):
                        last_import_match = list(re.finditer(import_pattern, code_to_execute))[-1]
                        insert_pos = last_import_match.end()
                        code_to_execute = code_to_execute[:insert_pos] + f'filepath = "{docker_path}"\n' + code_to_execute[insert_pos:]
                    else:
                        code_to_execute = f'filepath = "{docker_path}"\n\n' + code_to_execute
                
                print(f"   변환 결과:\n{code_to_execute}")
                
                # 검증
                if case['expected'] in code_to_execute and docker_path in code_to_execute:
                    print(f"   ✅ 변환 성공: filepath 변수 및 도커 경로 포함")
                else:
                    print(f"   ❌ 변환 실패: filepath 변수 또는 도커 경로 미포함")
                    print(f"      filepath 포함: {case['expected'] in code_to_execute}")
                    print(f"      도커 경로 포함: {docker_path in code_to_execute}")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed
    
    def test_4_docker_volume_mounting(self, test_csv_file):
        """테스트 4: 도커 볼륨 마운트 확인"""
        print("\n" + "="*70)
        print("테스트 4: 도커 볼륨 마운트 확인")
        print("="*70)
        
        try:
            from src.tools.code_execution.executors.docker_executor import DockerExecutor
            from src.tools.code_execution.base import ExecutionConfig, ExecutionEnvironment
            
            executor = DockerExecutor()
            
            # 테스트용 코드 파일 생성
            test_code_file = Path("/tmp/test_debug_code.py")
            test_code_file.write_text("print('Hello World')")
            
            try:
                # 볼륨 마운트 준비
                config = ExecutionConfig(
                    environment=ExecutionEnvironment.DOCKER,
                    input_files=[str(test_csv_file)],
                    timeout=30
                )
                
                volumes = executor._prepare_volumes(test_code_file, config)
                
                print(f"✅ 볼륨 마운트 준비 완료")
                print(f"   코드 파일: {test_code_file}")
                print(f"   CSV 파일: {test_csv_file}")
                print(f"\n   마운트 정보:")
                for host_path, mount_info in volumes.items():
                    print(f"      {host_path} -> {mount_info['bind']} ({mount_info['mode']})")
                
                # 검증
                assert str(test_code_file.parent) in volumes
                assert volumes[str(test_code_file.parent)]['bind'] == "/workspace/code"
                
                # CSV 파일이 다른 디렉토리에 있으면 별도 마운트 확인
                csv_parent = str(test_csv_file.parent)
                if csv_parent != str(test_code_file.parent):
                    assert csv_parent in volumes
                    assert "/workspace/data" in volumes[csv_parent]['bind']
                    print(f"   ✅ CSV 파일 디렉토리 마운트 확인: {volumes[csv_parent]['bind']}")
                
                return True
                
            finally:
                if test_code_file.exists():
                    test_code_file.unlink()
                    
        except Exception as e:
            print(f"❌ 도커 볼륨 마운트 확인 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_5_code_execution_path_conversion(self, test_csv_file):
        """테스트 5: 코드 실행 시 경로 변환 전체 흐름"""
        print("\n" + "="*70)
        print("테스트 5: 코드 실행 시 경로 변환 전체 흐름")
        print("="*70)
        
        # 실제 생성될 수 있는 코드 예시들
        test_codes = [
            {
                "name": "파일명만 사용",
                "code": """
import pandas as pd
df = pd.read_csv('test_debug.csv')
print(df.head())
"""
            },
            {
                "name": "절대 경로 사용",
                "code": f"""
import pandas as pd
df = pd.read_csv("{test_csv_file}")
print(df.head())
"""
            },
            {
                "name": "변수 사용 후 파일명",
                "code": """
import pandas as pd
filepath = "test_debug.csv"
df = pd.read_csv(filepath)
print(df.head())
"""
            },
        ]
        
        all_passed = True
        
        for test_case in test_codes:
            print(f"\n📝 테스트 케이스: {test_case['name']}")
            print(f"   원본 코드:\n{test_case['code']}")
            
            try:
                # 1단계: 호스트 경로를 도커 경로로 변환
                code_step1 = _convert_host_paths_to_docker_paths(
                    test_case['code'],
                    str(test_csv_file),
                    []
                )
                print(f"\n   1단계 (호스트->도커 변환):\n{code_step1}")
                
                # 2단계: 파일명 패턴 처리 및 filepath 변수 추가
                csv_file_name = test_csv_file.name
                docker_path = f"/workspace/data/{csv_file_name}"
                code_step2 = code_step1
                
                # 변수 할당에서 파일명만 있는 경우도 도커 경로로 변환 (먼저 처리)
                code_step2 = re.sub(
                    rf'(filepath(?:_\d+)?)\s*=\s*["\']{re.escape(csv_file_name)}["\']',
                    rf'\1 = "{docker_path}"',
                    code_step2
                )
                
                # 파일명만 사용하는 패턴 처리
                if re.search(rf'["\']{re.escape(csv_file_name)}["\']', code_step2):
                    code_step2 = re.sub(
                        rf'pd\.read_csv\(["\']{re.escape(csv_file_name)}["\']\)',
                        'pd.read_csv(filepath)',
                        code_step2
                    )
                    code_step2 = re.sub(
                        rf'pd\.read_csv\(["\']{re.escape(csv_file_name)}["\']\s*,\s*',
                        'pd.read_csv(filepath, ',
                        code_step2
                    )
                
                # 도커 경로 패턴도 filepath 변수로 교체
                docker_path_exact = re.escape(docker_path)
                if re.search(docker_path_exact, code_step2):
                    code_step2 = re.sub(
                        rf'pd\.read_csv\(["\']{docker_path_exact}["\']\)',
                        'pd.read_csv(filepath)',
                        code_step2
                    )
                    code_step2 = re.sub(
                        rf'pd\.read_csv\(["\']{docker_path_exact}["\']\s*,\s*',
                        'pd.read_csv(filepath, ',
                        code_step2
                    )
                
                # filepath 변수 추가
                if 'filepath' not in code_step2 or not re.search(r'filepath\s*=', code_step2):
                    import_pattern = r'(import\s+\w+[^\n]*\n)'
                    if re.search(import_pattern, code_step2):
                        last_import_match = list(re.finditer(import_pattern, code_step2))[-1]
                        insert_pos = last_import_match.end()
                        code_step2 = code_step2[:insert_pos] + f'filepath = "{docker_path}"\n' + code_step2[insert_pos:]
                    else:
                        code_step2 = f'filepath = "{docker_path}"\n\n' + code_step2
                
                print(f"\n   2단계 (파일명 패턴 처리):\n{code_step2}")
                
                # 검증
                has_filepath = 'filepath' in code_step2 and re.search(r'filepath\s*=', code_step2)
                has_docker_path = docker_path in code_step2
                uses_filepath_var = 'pd.read_csv(filepath)' in code_step2
                
                print(f"\n   검증 결과:")
                print(f"      filepath 변수 정의: {has_filepath}")
                print(f"      도커 경로 포함: {has_docker_path}")
                print(f"      filepath 변수 사용: {uses_filepath_var}")
                
                if has_filepath and has_docker_path and uses_filepath_var:
                    print(f"   ✅ 전체 흐름 성공")
                else:
                    print(f"   ❌ 전체 흐름 실패")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed
    
    def test_6_actual_generated_code_pattern(self):
        """테스트 6: 실제 생성된 코드 패턴 테스트"""
        print("\n" + "="*70)
        print("테스트 6: 실제 생성된 코드 패턴 테스트")
        print("="*70)
        
        # 실제로 생성될 수 있는 코드 패턴들
        actual_code_patterns = [
            {
                "name": "analysis_20251121_155101.py 패턴",
                "code": """
filepath = "/workspace/data/DESeq2_counts.csv"
filepath_2 = "/workspace/data/sampleInfo.csv"
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 데이터 불러오기
deseq2_counts = pd.read_csv('DESeq2_counts.csv')
sample_info = pd.read_csv('sampleInfo.csv')
"""
            },
            {
                "name": "파일명만 사용하는 패턴",
                "code": """
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())
"""
            },
        ]
        
        all_passed = True
        
        for test_case in actual_code_patterns:
            print(f"\n📝 테스트 케이스: {test_case['name']}")
            print(f"   원본 코드:\n{test_case['code']}")
            
            try:
                # 파일명 추출
                csv_files = []
                for match in re.finditer(r"pd\.read_csv\(['\"]([^'\"]+)['\"]\)", test_case['code']):
                    csv_files.append(match.group(1))
                
                if not csv_files:
                    print("   ⚠️ CSV 파일명을 찾을 수 없습니다.")
                    continue
                
                print(f"   발견된 CSV 파일: {csv_files}")
                
                # 각 파일에 대해 처리
                for csv_file_name in csv_files:
                    if csv_file_name.endswith('.csv'):
                        docker_path = f"/workspace/data/{csv_file_name}"
                        
                        # 파일명 패턴 교체
                        test_case['code'] = re.sub(
                            rf"pd\.read_csv\(['\"]{re.escape(csv_file_name)}['\"]\)",
                            'pd.read_csv(filepath)',
                            test_case['code']
                        )
                        
                        # filepath 변수 확인 및 추가
                        if 'filepath' not in test_case['code'] or not re.search(r'filepath\s*=', test_case['code']):
                            import_pattern = r'(import\s+\w+[^\n]*\n)'
                            if re.search(import_pattern, test_case['code']):
                                last_import_match = list(re.finditer(import_pattern, test_case['code']))[-1]
                                insert_pos = last_import_match.end()
                                test_case['code'] = test_case['code'][:insert_pos] + f'filepath = "{docker_path}"\n' + test_case['code'][insert_pos:]
                            else:
                                test_case['code'] = f'filepath = "{docker_path}"\n\n' + test_case['code']
                
                print(f"\n   변환된 코드:\n{test_case['code']}")
                
                # 검증
                has_filepath = 'filepath' in test_case['code'] and re.search(r'filepath\s*=', test_case['code'])
                uses_filepath = 'pd.read_csv(filepath)' in test_case['code']
                no_hardcoded = not re.search(r"pd\.read_csv\(['\"][^'\"]+\.csv['\"]\)", test_case['code'])
                
                print(f"\n   검증 결과:")
                print(f"      filepath 변수 정의: {has_filepath}")
                print(f"      filepath 변수 사용: {uses_filepath}")
                print(f"      하드코딩된 경로 없음: {no_hardcoded}")
                
                if has_filepath and uses_filepath and no_hardcoded:
                    print(f"   ✅ 패턴 처리 성공")
                else:
                    print(f"   ❌ 패턴 처리 실패")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed


def run_all_tests():
    """모든 테스트 실행"""
    print("="*70)
    print("CSV Data Analysis Agent 디버깅 테스트 시작")
    print("="*70)
    
    test_instance = TestCSVAgentDebugging()
    test_csv_file = None
    
    try:
        # 테스트용 CSV 파일 생성
        data_dir = get_data_directory()
        test_csv_file = data_dir / "test_debug.csv"
        
        import pandas as pd
        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'score': [85, 90, 88]
        })
        df.to_csv(test_csv_file, index=False)
        
        # 각 테스트 실행
        results = {}
        
        results['test_1'] = test_instance.test_1_read_csv_metadata(test_csv_file)
        results['test_2'] = test_instance.test_2_path_conversion_host_to_docker(test_csv_file)
        results['test_3'] = test_instance.test_3_filename_pattern_replacement(test_csv_file)
        results['test_4'] = test_instance.test_4_docker_volume_mounting(test_csv_file)
        results['test_5'] = test_instance.test_5_code_execution_path_conversion(test_csv_file)
        results['test_6'] = test_instance.test_6_actual_generated_code_pattern()
        
        # 결과 요약
        print("\n" + "="*70)
        print("테스트 결과 요약")
        print("="*70)
        
        for test_name, result in results.items():
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_name}: {status}")
        
        total_passed = sum(results.values())
        total_tests = len(results)
        
        print(f"\n총 {total_tests}개 테스트 중 {total_passed}개 통과")
        
        if total_passed == total_tests:
            print("🎉 모든 테스트 통과!")
        else:
            print(f"⚠️ {total_tests - total_passed}개 테스트 실패")
        
        return total_passed == total_tests
        
    finally:
        # 정리
        if test_csv_file and test_csv_file.exists():
            test_csv_file.unlink()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

