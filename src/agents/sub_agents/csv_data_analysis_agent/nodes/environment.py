"""
환경 검증 노드

Docker 이미지 환경에서 pandas 분석 가능 여부를 확인합니다.
"""

from __future__ import annotations

from typing import Dict, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent import CSVAnalysisState
else:
    # 런타임에 타입을 사용하지 않으므로 Any로 대체
    CSVAnalysisState = Any


def _validate_environment_for_pandas_analysis() -> Dict[str, Any]:
    """Docker 이미지 환경에서 pandas 분석 가능 여부 확인
    
    Docker 이미지(csv-sandbox:test) 내부의 패키지 설치 상태를 확인합니다.
    
    Returns:
        검증 결과 딕셔너리
    """
    validation_result = {
        "success": False,
        "packages": {},
        "test_result": None,
        "errors": [],
        "docker_image": None,
        "docker_available": False
    }
    
    # 필수 패키지 목록
    required_packages = {
        "pandas": "데이터 분석",
        "numpy": "수치 연산",
        "matplotlib": "시각화",
        "seaborn": "고급 시각화"
    }
    
    # Docker 이미지 이름 가져오기
    from src.utils.paths import get_docker_image_name
    docker_image = get_docker_image_name()
    validation_result["docker_image"] = docker_image
    
    print(f"🔍 [Environment Validation] Docker 이미지 환경 검증 중... (이미지: {docker_image})")
    
    # Docker Python SDK 사용
    try:
        import docker
        client = docker.from_env()
        client.ping()
        validation_result["docker_available"] = True
        print(f"  ✅ Docker 연결 성공")
    except ImportError:
        validation_result["errors"].append("docker 모듈이 설치되지 않았습니다. 'pip install docker'로 설치하세요.")
        print(f"  ❌ docker 모듈 없음")
        return validation_result
    except Exception as e:
        validation_result["errors"].append(f"Docker 연결 실패: {str(e)}")
        validation_result["errors"].append("Docker 데몬이 실행 중인지 확인하세요.")
        print(f"  ❌ Docker 연결 실패: {str(e)}")
        return validation_result
    
    # Docker 이미지 존재 여부 확인
    try:
        client.images.get(docker_image)
        print(f"  ✅ Docker 이미지 확인: {docker_image}")
    except docker.errors.ImageNotFound:
        validation_result["errors"].append(f"Docker 이미지 '{docker_image}'를 찾을 수 없습니다.")
        validation_result["errors"].append(f"다음 명령으로 이미지를 빌드하세요: docker build -t {docker_image} -f tests/Dockerfile.sandbox tests/")
        print(f"  ❌ Docker 이미지 없음: {docker_image}")
        return validation_result
    
    # Docker 컨테이너에서 패키지 확인
    print(f"  🔍 Docker 컨테이너에서 패키지 확인 중...")
    
    for package_name, description in required_packages.items():
        try:
            # Docker 컨테이너에서 패키지 버전 확인
            check_command = f"python -c \"import {package_name}; print({package_name}.__version__)\""
            result = client.containers.run(
                docker_image,
                check_command,
                remove=True,
                stderr=True,
                stdout=True,
            )
            
            stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            version = stdout.strip()
            
            validation_result["packages"][package_name] = {
                "installed": True,
                "version": version,
                "description": description
            }
            print(f"  ✅ {package_name} {version} 설치됨 (Docker 이미지)")
        except docker.errors.ContainerError as e:
            # 패키지가 없거나 import 실패
            stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else str(e)
            validation_result["packages"][package_name] = {
                "installed": False,
                "version": None,
                "description": description
            }
            validation_result["errors"].append(f"{package_name}이(가) Docker 이미지에 설치되지 않았습니다.")
            print(f"  ❌ {package_name} 설치되지 않음 (Docker 이미지): {stderr[:100]}")
        except Exception as e:
            validation_result["packages"][package_name] = {
                "installed": False,
                "version": None,
                "description": description
            }
            validation_result["errors"].append(f"{package_name} 확인 중 오류: {str(e)}")
            print(f"  ⚠️ {package_name} 확인 실패: {str(e)}")
    
    # pandas가 설치되어 있으면 간단한 테스트 실행
    if validation_result["packages"].get("pandas", {}).get("installed", False):
        try:
            # 테스트 코드를 파일로 저장하여 실행 (따옴표 문제 방지)
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
                test_code = """import pandas as pd
import numpy as np

# 간단한 테스트 데이터 생성
df = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50]
})

# 기본 연산 테스트
result = df['A'].sum()
print(f"✅ Pandas 기본 연산 테스트 성공: {result}")

# CSV 읽기 시뮬레이션 (실제 파일 없이)
from io import StringIO
test_csv = "col1,col2\\n1,2\\n3,4"
df_test = pd.read_csv(StringIO(test_csv))
print(f"✅ CSV 읽기 테스트 성공: {len(df_test)} 행")
"""
                tmp_file.write(test_code)
                tmp_file_path = tmp_file.name
            
            # 임시 파일을 Docker 컨테이너에 마운트하여 실행
            result = client.containers.run(
                docker_image,
                f"python /tmp/test_validation.py",
                volumes={tmp_file_path: {"bind": "/tmp/test_validation.py", "mode": "ro"}},
                remove=True,
                stderr=True,
                stdout=True,
            )
            
            # 임시 파일 삭제
            import os
            os.unlink(tmp_file_path)
            
            stdout = result.decode('utf-8') if isinstance(result, bytes) else str(result)
            if "✅" in stdout and "성공" in stdout:
                validation_result["test_result"] = "success"
                validation_result["success"] = True
                print("  ✅ 환경 테스트 통과 (Docker 이미지)")
            else:
                validation_result["test_result"] = f"테스트 실행 실패: {stdout}"
                validation_result["errors"].append(f"환경 테스트 실패: {stdout[:200]}")
                print(f"  ⚠️ 환경 테스트 결과: {stdout[:100]}...")
        except docker.errors.ContainerError as e:
            stderr = e.stderr.decode('utf-8') if hasattr(e, 'stderr') and e.stderr else str(e)
            validation_result["test_result"] = f"테스트 실행 실패: {stderr}"
            validation_result["errors"].append(f"테스트 실행 중 오류: {stderr[:200]}")
            print(f"  ❌ 테스트 실행 실패: {stderr[:100]}")
        except Exception as e:
            validation_result["test_result"] = f"테스트 실행 실패: {str(e)}"
            validation_result["errors"].append(f"테스트 실행 중 오류: {str(e)}")
            print(f"  ❌ 테스트 실행 실패: {str(e)}")
    else:
        validation_result["errors"].append("pandas가 Docker 이미지에 설치되지 않아 테스트를 실행할 수 없습니다.")
    
    # 결과 요약
    if validation_result["success"]:
        print(f"✅ Docker 이미지 환경 검증 완료: pandas 분석 가능 ({docker_image})")
    else:
        print(f"⚠️ Docker 이미지 환경 검증 실패: 일부 패키지가 없거나 테스트 실패 ({docker_image})")
        if validation_result["errors"]:
            print("  오류:")
            for error in validation_result["errors"]:
                print(f"    - {error}")
    
    return validation_result


def create_validate_environment_node() -> Callable[[CSVAnalysisState], CSVAnalysisState]:
    """환경 검증 노드 생성
    
    Returns:
        환경 검증 노드 함수
    """
    def validate_environment_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """환경 검증 노드: Docker 이미지 환경에서 pandas 분석 가능 여부 확인
        
        Docker 이미지(csv-sandbox:test) 내부의 패키지 설치 상태를 확인합니다.
        """
        print("🔍 [Environment Validation] Docker 이미지 환경 검증 중...")
        
        # 이미 검증된 경우 건너뛰기
        if state.get("environment_validated", False):
            print("✅ 환경 검증 이미 완료됨")
            return {
                "status": "environment_validated"
            }
        
        # Docker 이미지 환경 검증 실행
        validation_result = _validate_environment_for_pandas_analysis()
        
        # 검증 결과 포맷팅
        validation_summary = []
        validation_summary.append("=== Docker 이미지 환경 검증 결과 ===\n")
        
        # Docker 이미지 정보
        docker_image = validation_result.get("docker_image", "unknown")
        docker_available = validation_result.get("docker_available", False)
        validation_summary.append(f"🐳 Docker 이미지: {docker_image}")
        validation_summary.append(f"🔌 Docker 연결: {'✅ 연결됨' if docker_available else '❌ 연결 실패'}\n")
        
        # 패키지 상태
        validation_summary.append("📦 패키지 상태 (Docker 이미지 내부):")
        for pkg_name, pkg_info in validation_result["packages"].items():
            if pkg_info["installed"]:
                validation_summary.append(f"  ✅ {pkg_name} {pkg_info['version']} ({pkg_info['description']})")
            else:
                validation_summary.append(f"  ❌ {pkg_name} 미설치 ({pkg_info['description']})")
        
        # 테스트 결과
        if validation_result["test_result"]:
            validation_summary.append(f"\n🧪 테스트 결과:")
            if validation_result["test_result"] == "success":
                validation_summary.append("  ✅ 환경 테스트 통과 (Docker 이미지)")
            else:
                validation_summary.append(f"  ⚠️ {validation_result['test_result']}")
        
        # 오류 목록
        if validation_result["errors"]:
            validation_summary.append(f"\n❌ 오류:")
            for error in validation_result["errors"]:
                validation_summary.append(f"  - {error}")
        
        validation_summary_text = "\n".join(validation_summary)
        
        if validation_result["success"]:
            print(f"✅ Docker 이미지 환경 검증 완료: pandas 분석 가능 ({docker_image})")
            return {
                "environment_validated": True,
                "environment_validation_result": validation_summary_text,
                "status": "environment_validated"
            }
        else:
            print(f"⚠️ Docker 이미지 환경 검증 실패: 일부 패키지가 없거나 테스트 실패 ({docker_image})")
            # 경고만 표시하고 계속 진행 (실제 실행 시 오류 발생 가능)
            return {
                "environment_validated": False,
                "environment_validation_result": validation_summary_text,
                "status": "environment_validation_warning",
                "errors": validation_result["errors"]
            }
    
    return validate_environment_node

