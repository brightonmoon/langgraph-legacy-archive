"""
Docker Python SDK를 직접 사용한 샌드박스 환경 테스트

이 테스트는 Docker Python SDK를 직접 사용하여
격리된 Docker 컨테이너에서 Python 코드를 실행하는 기능을 검증합니다.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import docker
except ImportError:
    print("❌ docker 패키지가 설치되지 않았습니다.")
    print("   설치: pip install docker")
    sys.exit(1)


def execute_code_in_docker_sandbox(
    code_file: Path,
    csv_file: Path = None,
    output_dir: Path = None,
    image: str = "csv-sandbox:test"
) -> Dict[str, Any]:
    """Docker 샌드박스에서 코드 실행"""
    client = docker.from_env()
    
    # 볼륨 마운트 설정
    volumes = {
        str(code_file.parent): {"bind": "/workspace/code", "mode": "ro"},
    }
    
    # CSV 파일이 있으면 마운트
    # CSV 파일이 코드 파일과 같은 디렉토리에 있으면 이미 마운트됨
    # 다른 디렉토리에 있으면 별도로 마운트
    if csv_file and csv_file.exists():
        csv_parent = str(csv_file.parent)
        code_parent = str(code_file.parent)
        if csv_parent != code_parent:
            volumes[csv_parent] = {"bind": "/workspace/data", "mode": "ro"}
        else:
            # 같은 디렉토리면 코드 디렉토리에서 접근 가능
            pass
    
    # 결과 디렉토리가 있으면 마운트
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        volumes[str(output_dir)] = {"bind": "/workspace/results", "mode": "rw"}
    
    # 컨테이너 실행
    try:
        # Docker SDK의 run() 메서드는 timeout 파라미터를 지원하지 않음
        # 대신 detach=False로 실행하고, 컨테이너가 자동으로 종료되도록 함
        result = client.containers.run(
            image,
            f"python /workspace/code/{code_file.name}",
            volumes=volumes,
            remove=True,  # 실행 후 자동 삭제
            stderr=True,  # stderr도 캡처
            stdout=True,  # stdout 캡처
        )
        
        stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
        
        return {
            "success": True,
            "stdout": stdout,
            "exit_code": 0
        }
    except docker.errors.ContainerError as e:
        # 컨테이너 실행 중 에러 발생
        stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
        return {
            "success": False,
            "stdout": "",
            "stderr": stderr,
            "exit_code": e.exit_status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "exit_code": -1
        }


def test_docker_sdk_sandbox():
    """Docker Python SDK를 사용한 샌드박스 테스트"""
    print("=" * 60)
    print("Docker Python SDK 직접 사용 테스트")
    print("=" * 60)
    
    # 작업 디렉토리 설정
    workspace_root = project_root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    # 테스트 1: 간단한 Python 코드 실행
    print("\n" + "=" * 60)
    print("테스트 1: 간단한 Python 코드 실행")
    print("=" * 60)
    
    test_code_1 = """
print("✅ 기본 Python 테스트 성공")
print(f"Python 버전: {__import__('sys').version}")
"""
    
    test_file_1 = workspace_root / "test_basic.py"
    test_file_1.write_text(test_code_1, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_1}")
    
    print("\n🚀 Docker 컨테이너에서 실행...")
    result = execute_code_in_docker_sandbox(
        code_file=test_file_1,
        image="python:3.11-slim"
    )
    
    print("\n📊 실행 결과:")
    print("-" * 60)
    if result["success"]:
        print(f"✅ 성공")
        print(f"출력:\n{result['stdout']}")
    else:
        print(f"❌ 실패")
        if "stderr" in result:
            print(f"에러:\n{result['stderr']}")
        if "error" in result:
            print(f"오류: {result['error']}")
    print("-" * 60)
    
    # 테스트 2: Pandas/NumPy 코드 실행
    print("\n" + "=" * 60)
    print("테스트 2: Pandas/NumPy 코드 실행")
    print("=" * 60)
    
    test_code_2 = """
import pandas as pd
import numpy as np

# 간단한 데이터프레임 생성
df = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50]
})

# 기본 연산
result = df['A'].sum()
print(f"✅ Pandas 기본 연산 테스트 성공: {result}")
print(f"DataFrame shape: {df.shape}")

# NumPy 연산
arr = np.array([1, 2, 3, 4, 5])
print(f"NumPy sum: {np.sum(arr)}")
"""
    
    test_file_2 = workspace_root / "test_pandas_numpy.py"
    test_file_2.write_text(test_code_2, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_2}")
    
    print("\n🚀 Docker 컨테이너에서 실행 (csv-sandbox:test 이미지 사용)...")
    result = execute_code_in_docker_sandbox(
        code_file=test_file_2,
        image="csv-sandbox:test"  # pandas/numpy가 설치된 이미지
    )
    
    print("\n📊 실행 결과:")
    print("-" * 60)
    if result["success"]:
        print(f"✅ 성공")
        print(f"출력:\n{result['stdout']}")
    else:
        print(f"❌ 실패")
        if "stderr" in result:
            print(f"에러:\n{result['stderr']}")
        if "error" in result:
            print(f"오류: {result['error']}")
    print("-" * 60)
    
    # 테스트 3: CSV 파일 읽기 테스트
    print("\n" + "=" * 60)
    print("테스트 3: CSV 파일 읽기 테스트")
    print("=" * 60)
    
    # 간단한 CSV 파일 생성
    csv_content = """col1,col2,col3
1,2,3
4,5,6
7,8,9"""
    
    csv_file = workspace_root / "test_data.csv"
    csv_file.write_text(csv_content, encoding='utf-8')
    print(f"📝 CSV 파일 생성: {csv_file}")
    
    test_code_3 = """
import pandas as pd
import os

# CSV 파일 경로 확인
csv_path = '/workspace/data/test_data.csv'
if not os.path.exists(csv_path):
    # 대안 경로 시도
    csv_path = '/workspace/code/test_data.csv'

# CSV 파일 읽기
df = pd.read_csv(csv_path)
print(f"✅ CSV 읽기 성공")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\\nData:\\n{df}")
"""
    
    test_file_3 = workspace_root / "test_csv_read.py"
    test_file_3.write_text(test_code_3, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_3}")
    
    print("\n🚀 Docker 컨테이너에서 실행...")
    result = execute_code_in_docker_sandbox(
        code_file=test_file_3,
        csv_file=csv_file,
        image="csv-sandbox:test"
    )
    
    print("\n📊 실행 결과:")
    print("-" * 60)
    if result["success"]:
        print(f"✅ 성공")
        print(f"출력:\n{result['stdout']}")
    else:
        print(f"❌ 실패")
        if "stderr" in result:
            print(f"에러:\n{result['stderr']}")
        if "error" in result:
            print(f"오류: {result['error']}")
    print("-" * 60)
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    # Docker 클라이언트 확인
    try:
        client = docker.from_env()
        client.ping()
        print("✅ Docker 연결 성공")
    except Exception as e:
        print(f"❌ Docker 연결 실패: {str(e)}")
        print("   Docker가 실행 중인지 확인하세요.")
        sys.exit(1)
    
    test_docker_sdk_sandbox()

