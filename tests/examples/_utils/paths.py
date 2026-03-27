"""프로젝트 경로 설정

이 모듈을 import하면 자동으로 프로젝트 루트가 sys.path에 추가됩니다.
"""
import sys
from pathlib import Path

# 경로 상수 정의
EXAMPLES_DIR = Path(__file__).parent.parent
PROJECT_ROOT = EXAMPLES_DIR.parent.parent

# 프로젝트 루트를 sys.path에 추가 (중복 방지)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 자주 사용되는 디렉토리 경로
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data"
DATA_DIR = PROJECT_ROOT / "data"


def get_test_csv_path(filename: str) -> Path:
    """테스트 CSV 파일 경로 반환"""
    return TEST_DATA_DIR / filename


def get_data_path(filename: str) -> Path:
    """데이터 디렉토리 파일 경로 반환"""
    return DATA_DIR / filename


def ensure_test_data_dir() -> Path:
    """테스트 데이터 디렉토리가 존재하는지 확인하고 경로 반환"""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_DIR
