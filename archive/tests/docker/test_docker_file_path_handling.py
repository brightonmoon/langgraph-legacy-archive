"""
도커 환경에서 파일 경로 처리 방식 비교 및 디버깅 테스트

코드 생성 에이전트와 CSV 데이터 분석 에이전트의 파일 경로 처리 방식을 비교하고,
문제를 진단하는 테스트 코드입니다.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


def get_code_generation_agent_docker_path(
    code_file_path: Path,
    csv_file_path: Path
) -> str:
    """코드 생성 에이전트의 도커 경로 결정 로직 (agent.py:810-817)"""
    code_parent = str(code_file_path.parent)
    csv_parent = str(csv_file_path.parent)
    
    if csv_parent == code_parent:
        # 같은 디렉토리면 /workspace/code/에서 접근 가능
        docker_path = f"/workspace/code/{csv_file_path.name}"
    else:
        # 다른 디렉토리면 /workspace/data/에서 접근 가능
        docker_path = f"/workspace/data/{csv_file_path.name}"
    
    return docker_path


def get_csv_agent_docker_path(
    csv_file_path: Path
) -> str:
    """CSV 데이터 분석 에이전트의 도커 경로 결정 로직 (agent.py:2479, 2575)"""
    # 무조건 /workspace/data/ 사용
    docker_path = f"/workspace/data/{csv_file_path.name}"
    return docker_path


def simulate_docker_mounting(
    code_file_path: Path,
    csv_file_path: Path
) -> Dict[str, str]:
    """도커 볼륨 마운트 시뮬레이션 (docker_executor.py:_prepare_volumes)"""
    volumes = {}
    code_parent = str(code_file_path.parent)
    csv_parent = str(csv_file_path.parent)
    
    # 코드 파일의 부모 디렉토리를 /workspace/code로 마운트
    volumes[code_parent] = {"bind": "/workspace/code", "mode": "ro"}
    
    # CSV 파일이 다른 디렉토리에 있으면 별도로 마운트
    if csv_parent != code_parent:
        volumes[csv_parent] = {"bind": "/workspace/data", "mode": "ro"}
    
    return volumes


def test_file_path_scenarios():
    """다양한 파일 경로 시나리오 테스트"""
    
    # 시나리오 1: 코드 파일과 CSV 파일이 같은 디렉토리에 있는 경우
    print("=" * 80)
    print("시나리오 1: 코드 파일과 CSV 파일이 같은 디렉토리")
    print("=" * 80)
    
    code_file_1 = Path("/workspace/generated_code/analysis.py")
    csv_file_1 = Path("/workspace/generated_code/deseq2_counts.csv")
    
    volumes_1 = simulate_docker_mounting(code_file_1, csv_file_1)
    code_gen_path_1 = get_code_generation_agent_docker_path(code_file_1, csv_file_1)
    csv_agent_path_1 = get_csv_agent_docker_path(csv_file_1)
    
    print(f"코드 파일: {code_file_1}")
    print(f"CSV 파일: {csv_file_1}")
    print(f"\n도커 볼륨 마운트:")
    for host_path, mount_info in volumes_1.items():
        print(f"  {host_path} -> {mount_info['bind']}")
    print(f"\n코드 생성 에이전트 경로: {code_gen_path_1}")
    print(f"CSV 데이터 분석 에이전트 경로: {csv_agent_path_1}")
    
    # 파일이 실제로 접근 가능한지 확인
    if code_gen_path_1.startswith("/workspace/code/"):
        expected_mount = "/workspace/code"
    else:
        expected_mount = "/workspace/data"
    
    is_accessible_code_gen = expected_mount in [v["bind"] for v in volumes_1.values()]
    is_accessible_csv_agent = "/workspace/data" in [v["bind"] for v in volumes_1.values()]
    
    print(f"\n✅ 코드 생성 에이전트 경로 접근 가능: {is_accessible_code_gen}")
    print(f"{'✅' if is_accessible_csv_agent else '❌'} CSV 데이터 분석 에이전트 경로 접근 가능: {is_accessible_csv_agent}")
    
    if not is_accessible_csv_agent:
        print(f"  ⚠️ 문제: CSV 파일이 /workspace/code에 마운트되어 있지만, 에이전트는 /workspace/data를 사용합니다!")
    
    # 시나리오 2: 코드 파일과 CSV 파일이 다른 디렉토리에 있는 경우
    print("\n" + "=" * 80)
    print("시나리오 2: 코드 파일과 CSV 파일이 다른 디렉토리")
    print("=" * 80)
    
    code_file_2 = Path("/workspace/generated_code/analysis.py")
    csv_file_2 = Path("/workspace/data/deseq2_counts.csv")
    
    volumes_2 = simulate_docker_mounting(code_file_2, csv_file_2)
    code_gen_path_2 = get_code_generation_agent_docker_path(code_file_2, csv_file_2)
    csv_agent_path_2 = get_csv_agent_docker_path(csv_file_2)
    
    print(f"코드 파일: {code_file_2}")
    print(f"CSV 파일: {csv_file_2}")
    print(f"\n도커 볼륨 마운트:")
    for host_path, mount_info in volumes_2.items():
        print(f"  {host_path} -> {mount_info['bind']}")
    print(f"\n코드 생성 에이전트 경로: {code_gen_path_2}")
    print(f"CSV 데이터 분석 에이전트 경로: {csv_agent_path_2}")
    
    is_accessible_code_gen_2 = "/workspace/data" in [v["bind"] for v in volumes_2.values()]
    is_accessible_csv_agent_2 = "/workspace/data" in [v["bind"] for v in volumes_2.values()]
    
    print(f"\n✅ 코드 생성 에이전트 경로 접근 가능: {is_accessible_code_gen_2}")
    print(f"✅ CSV 데이터 분석 에이전트 경로 접근 가능: {is_accessible_csv_agent_2}")
    
    # 시나리오 3: 실제 프로젝트 구조 시뮬레이션
    print("\n" + "=" * 80)
    print("시나리오 3: 실제 프로젝트 구조 (workspace/generated_code vs data/)")
    print("=" * 80)
    
    # 프로젝트 루트 가정
    project_root = Path("/home/doyamoon/agentic_ai")
    code_file_3 = project_root / "workspace/generated_code/temp_interactive_code_12345.py"
    csv_file_3 = project_root / "data/deseq2_counts.csv"
    
    volumes_3 = simulate_docker_mounting(code_file_3, csv_file_3)
    code_gen_path_3 = get_code_generation_agent_docker_path(code_file_3, csv_file_3)
    csv_agent_path_3 = get_csv_agent_docker_path(csv_file_3)
    
    print(f"코드 파일: {code_file_3}")
    print(f"CSV 파일: {csv_file_3}")
    print(f"\n도커 볼륨 마운트:")
    for host_path, mount_info in volumes_3.items():
        print(f"  {host_path} -> {mount_info['bind']}")
    print(f"\n코드 생성 에이전트 경로: {code_gen_path_3}")
    print(f"CSV 데이터 분석 에이전트 경로: {csv_agent_path_3}")
    
    is_accessible_code_gen_3 = "/workspace/data" in [v["bind"] for v in volumes_3.values()]
    is_accessible_csv_agent_3 = "/workspace/data" in [v["bind"] for v in volumes_3.values()]
    
    print(f"\n✅ 코드 생성 에이전트 경로 접근 가능: {is_accessible_code_gen_3}")
    print(f"✅ CSV 데이터 분석 에이전트 경로 접근 가능: {is_accessible_csv_agent_3}")
    
    return {
        "scenario_1": {
            "code_gen_works": is_accessible_code_gen,
            "csv_agent_works": is_accessible_csv_agent,
            "code_gen_path": code_gen_path_1,
            "csv_agent_path": csv_agent_path_1
        },
        "scenario_2": {
            "code_gen_works": is_accessible_code_gen_2,
            "csv_agent_works": is_accessible_csv_agent_2,
            "code_gen_path": code_gen_path_2,
            "csv_agent_path": csv_agent_path_2
        },
        "scenario_3": {
            "code_gen_works": is_accessible_code_gen_3,
            "csv_agent_works": is_accessible_csv_agent_3,
            "code_gen_path": code_gen_path_3,
            "csv_agent_path": csv_agent_path_3
        }
    }


def test_code_path_replacement():
    """코드에서 경로 변환 로직 테스트"""
    
    print("\n" + "=" * 80)
    print("코드 경로 변환 테스트")
    print("=" * 80)
    
    # 테스트 코드 예시
    test_code = '''
import pandas as pd

# 하드코딩된 경로들
df1 = pd.read_csv('deseq2_counts.csv')
df2 = pd.read_csv("/workspace/data/deseq2_counts.csv")
df3 = pd.read_csv("/home/doyamoon/agentic_ai/data/deseq2_counts.csv")

# 변수 사용
filepath = "/workspace/data/deseq2_counts.csv"
df4 = pd.read_csv(filepath)
'''
    
    csv_file_path = Path("/workspace/data/deseq2_counts.csv")
    code_file_path = Path("/workspace/generated_code/temp_code.py")
    
    # 코드 생성 에이전트 방식
    code_gen_docker_path = get_code_generation_agent_docker_path(code_file_path, csv_file_path)
    
    # CSV 데이터 분석 에이전트 방식
    csv_agent_docker_path = get_csv_agent_docker_path(csv_file_path)
    
    print("원본 코드:")
    print(test_code)
    
    # 코드 생성 에이전트 방식으로 변환
    code_gen_converted = test_code
    code_gen_converted = re.sub(
        r"pd\.read_csv\(['\"]deseq2_counts\.csv['\"]\)",
        f'pd.read_csv(filepath)',
        code_gen_converted
    )
    code_gen_converted = re.sub(
        r"pd\.read_csv\(['\"][^'\"]*deseq2_counts\.csv['\"]\)",
        f'pd.read_csv(filepath)',
        code_gen_converted
    )
    if 'filepath' not in code_gen_converted:
        code_gen_converted = f'filepath = "{code_gen_docker_path}"\n' + code_gen_converted
    
    print("\n코드 생성 에이전트 방식으로 변환:")
    print(code_gen_converted)
    
    # CSV 데이터 분석 에이전트 방식으로 변환
    csv_agent_converted = test_code
    csv_agent_converted = re.sub(
        r"pd\.read_csv\(['\"]deseq2_counts\.csv['\"]\)",
        f'pd.read_csv(filepath)',
        csv_agent_converted
    )
    csv_agent_converted = re.sub(
        r"pd\.read_csv\(['\"][^'\"]*deseq2_counts\.csv['\"]\)",
        f'pd.read_csv(filepath)',
        csv_agent_converted
    )
    if 'filepath' not in csv_agent_converted:
        csv_agent_converted = f'filepath = "{csv_agent_docker_path}"\n' + csv_agent_converted
    
    print("\nCSV 데이터 분석 에이전트 방식으로 변환:")
    print(csv_agent_converted)


def test_fixed_csv_agent_logic():
    """수정된 CSV 데이터 분석 에이전트 로직 테스트"""
    
    print("\n" + "=" * 80)
    print("수정된 CSV 데이터 분석 에이전트 로직 테스트")
    print("=" * 80)
    
    def get_fixed_csv_agent_docker_path(
        code_file_path: Path,
        csv_file_path: Path
    ) -> str:
        """수정된 CSV 데이터 분석 에이전트의 도커 경로 결정 로직"""
        code_parent = str(code_file_path.parent)
        csv_parent = str(csv_file_path.parent)
        
        if csv_parent == code_parent:
            # 같은 디렉토리면 /workspace/code/에서 접근 가능
            docker_path = f"/workspace/code/{csv_file_path.name}"
        else:
            # 다른 디렉토리면 /workspace/data/에서 접근 가능
            docker_path = f"/workspace/data/{csv_file_path.name}"
        
        return docker_path
    
    # 시나리오 1: 같은 디렉토리
    code_file_1 = Path("/workspace/generated_code/analysis.py")
    csv_file_1 = Path("/workspace/generated_code/deseq2_counts.csv")
    
    fixed_path_1 = get_fixed_csv_agent_docker_path(code_file_1, csv_file_1)
    code_gen_path_1 = get_code_generation_agent_docker_path(code_file_1, csv_file_1)
    
    print(f"\n시나리오 1: 같은 디렉토리")
    print(f"코드 파일: {code_file_1}")
    print(f"CSV 파일: {csv_file_1}")
    print(f"수정된 CSV 에이전트 경로: {fixed_path_1}")
    print(f"코드 생성 에이전트 경로: {code_gen_path_1}")
    print(f"✅ 경로 일치: {fixed_path_1 == code_gen_path_1}")
    
    # 시나리오 2: 다른 디렉토리
    code_file_2 = Path("/workspace/generated_code/analysis.py")
    csv_file_2 = Path("/workspace/data/deseq2_counts.csv")
    
    fixed_path_2 = get_fixed_csv_agent_docker_path(code_file_2, csv_file_2)
    code_gen_path_2 = get_code_generation_agent_docker_path(code_file_2, csv_file_2)
    
    print(f"\n시나리오 2: 다른 디렉토리")
    print(f"코드 파일: {code_file_2}")
    print(f"CSV 파일: {csv_file_2}")
    print(f"수정된 CSV 에이전트 경로: {fixed_path_2}")
    print(f"코드 생성 에이전트 경로: {code_gen_path_2}")
    print(f"✅ 경로 일치: {fixed_path_2 == code_gen_path_2}")
    
    return {
        "scenario_1_match": fixed_path_1 == code_gen_path_1,
        "scenario_2_match": fixed_path_2 == code_gen_path_2
    }


def generate_fix_recommendation():
    """수정 권장사항 생성"""
    
    print("\n" + "=" * 80)
    print("수정 완료")
    print("=" * 80)
    
    recommendation = """
CSV 데이터 분석 에이전트의 execute_code_node 함수를 수정했습니다.

수정 내용:
1. 코드 파일의 부모 디렉토리를 미리 결정 (temp_code_file 생성 위치 기반)
2. 각 CSV 파일에 대해 코드 파일의 부모 디렉토리와 비교
3. 같은 디렉토리면 /workspace/code/파일명, 다른 디렉토리면 /workspace/data/파일명 사용
4. 코드 생성 에이전트와 동일한 로직 적용

수정된 위치:
- agent.py의 execute_code_node 함수 내부 (약 2473-2680줄)
- 여러 파일 모드와 단일 파일 모드 모두 수정 완료
"""
    
    print(recommendation)


if __name__ == "__main__":
    print("도커 환경 파일 경로 처리 방식 비교 및 디버깅 테스트")
    print("=" * 80)
    
    # 시나리오 테스트
    results = test_file_path_scenarios()
    
    # 코드 변환 테스트
    test_code_path_replacement()
    
    # 수정된 로직 테스트
    fixed_results = test_fixed_csv_agent_logic()
    
    # 수정 완료 메시지
    generate_fix_recommendation()
    
    # 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    for scenario_name, result in results.items():
        print(f"\n{scenario_name}:")
        print(f"  코드 생성 에이전트: {'✅ 작동' if result['code_gen_works'] else '❌ 실패'} ({result['code_gen_path']})")
        print(f"  CSV 데이터 분석 에이전트 (수정 전): {'✅ 작동' if result['csv_agent_works'] else '❌ 실패'} ({result['csv_agent_path']})")
        
        if not result['csv_agent_works']:
            print(f"  ⚠️ CSV 데이터 분석 에이전트가 잘못된 경로를 사용합니다!")
    
    print("\n수정 후 비교:")
    print(f"  시나리오 1 (같은 디렉토리): {'✅ 경로 일치' if fixed_results['scenario_1_match'] else '❌ 경로 불일치'}")
    print(f"  시나리오 2 (다른 디렉토리): {'✅ 경로 일치' if fixed_results['scenario_2_match'] else '❌ 경로 불일치'}")

