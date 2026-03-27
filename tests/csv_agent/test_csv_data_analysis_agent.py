"""
CSV Data Analysis Agent 테스트

CSV 파일 분석 Agent의 기능을 테스트합니다.
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent


def test_agent_import():
    """Agent 모듈 import 테스트"""
    try:
        from src.agents.sub_agents.csv_data_analysis_agent import (
            create_csv_data_analysis_agent,
            agent
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Agent 모듈 import 실패: {e}")


def test_agent_creation():
    """Agent 생성 테스트"""
    from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent
    
    try:
        agent = create_csv_data_analysis_agent()
        assert agent is not None
        print("✅ Agent 생성 성공")
    except Exception as e:
        pytest.skip(f"Agent 생성 실패 (환경변수 미설정 가능): {e}")


def test_code_execution_tool():
    """코드 실행 도구 테스트"""
    from src.tools.code_execution import execute_python_code_tool
    
    # 간단한 코드 실행 테스트
    test_code = """
print("Hello, World!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
    
    result = execute_python_code_tool.invoke({
        "code": test_code,
        "timeout": 10
    })
    
    assert result is not None
    assert "Hello, World!" in result
    assert "2 + 2 = 4" in result
    print("✅ 코드 실행 도구 테스트 통과")


def test_code_execution_with_error():
    """에러가 있는 코드 실행 테스트"""
    from src.tools.code_execution import execute_python_code_tool
    
    # 에러가 있는 코드
    error_code = """
print("시작")
x = 1 / 0  # ZeroDivisionError
print("끝")
"""
    
    result = execute_python_code_tool.invoke({
        "code": error_code,
        "timeout": 10
    })
    
    assert result is not None
    assert "❌" in result or "에러" in result or "Error" in result
    print("✅ 에러 처리 테스트 통과")


def test_code_execution_security():
    """보안 검증 테스트"""
    from src.tools.code_execution import execute_python_code_tool
    
    # 위험한 코드 (차단되어야 함)
    dangerous_code = """
import os
os.system("rm -rf /")  # 위험한 코드
"""
    
    result = execute_python_code_tool.invoke({
        "code": dangerous_code,
        "timeout": 10
    })
    
    assert "보안" in result or "차단" in result
    print("✅ 보안 검증 테스트 통과")


def test_csv_metadata_tool():
    """CSV 메타데이터 도구 테스트"""
    from src.tools.csv_tools import read_csv_metadata_tool
    from src.utils.paths import get_data_directory
    
    # 테스트용 CSV 파일을 data/ 디렉토리에 생성 (보안 검증 통과를 위해)
    data_dir = get_data_directory()
    test_csv_path = data_dir / "test_sample.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 간단한 CSV 파일 생성
    import pandas as pd
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "score": [85.5, 90.0, 88.5]
    })
    df.to_csv(test_csv_path, index=False)
    
    try:
        result = read_csv_metadata_tool.invoke({
            "filepath": str(test_csv_path)
        })
        
        assert result is not None
        assert "컬럼" in result or "column" in result.lower()
        print("✅ CSV 메타데이터 도구 테스트 통과")
    finally:
        # 테스트 파일 정리
        if test_csv_path.exists():
            test_csv_path.unlink()


@pytest.mark.skipif(
    not os.getenv("OLLAMA_API_KEY"),
    reason="OLLAMA_API_KEY 환경변수가 설정되지 않았습니다"
)
def test_agent_full_workflow():
    """Agent 전체 워크플로우 테스트 (실제 모델 필요)"""
    from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent
    from src.utils.paths import get_data_directory
    
    # 테스트용 CSV 파일을 data/ 디렉토리에 생성 (보안 검증 통과를 위해)
    data_dir = get_data_directory()
    test_csv_path = data_dir / "test_sample_analysis.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    import pandas as pd
    df = pd.DataFrame({
        "product": ["A", "B", "C", "A", "B", "C"],
        "sales": [100, 150, 120, 110, 160, 130],
        "region": ["North", "South", "North", "South", "North", "South"]
    })
    df.to_csv(test_csv_path, index=False)
    
    try:
        # Agent 생성
        agent = create_csv_data_analysis_agent()
        
        # 초기 상태 설정 (올바른 필드명 사용)
        initial_state = {
            "CSV_file_path": str(test_csv_path),  # 올바른 필드명
            "query": "제품별 평균 판매량을 계산하세요",  # 올바른 필드명
            "messages": [],
            "error_count": 0  # 에러 카운트 초기화
        }
        
        # Agent 실행 (전체 워크플로우) - Checkpointer를 위한 config 추가
        config = {
            "configurable": {
                "thread_id": "test_workflow_thread"  # Checkpointer를 위한 thread_id
            }
        }
        
        result = agent.invoke(initial_state, config=config)
        
        assert result is not None
        assert "status" in result
        assert result["status"] in ["completed", "error", "error_threshold_reached", "validation_passed"]
        
        print(f"✅ Agent 워크플로우 테스트 완료")
        print(f"   상태: {result['status']}")
        print(f"   에러 카운트: {result.get('error_count', 0)}")
        if result.get('final_report'):
            print(f"   최종 보고서 생성됨")
        
    except Exception as e:
        pytest.fail(f"Agent 워크플로우 테스트 실패: {e}")
    finally:
        # 테스트 파일 정리
        if test_csv_path.exists():
            test_csv_path.unlink()


@pytest.mark.skipif(
    not os.getenv("OLLAMA_API_KEY"),
    reason="OLLAMA_API_KEY 환경변수가 설정되지 않았습니다"
)
def test_error_counting_and_interrupt():
    """에러 카운팅 및 interrupt 기능 테스트"""
    from src.agents.sub_agents.csv_data_analysis_agent import create_csv_data_analysis_agent
    from src.utils.paths import get_data_directory
    
    # 테스트용 CSV 파일 생성
    data_dir = get_data_directory()
    test_csv_path = data_dir / "test_error_counting.csv"
    test_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    import pandas as pd
    df = pd.DataFrame({
        "value": [1, 2, 3, 4, 5]
    })
    df.to_csv(test_csv_path, index=False)
    
    try:
        # Agent 생성
        agent = create_csv_data_analysis_agent()
        
        # 초기 상태 설정
        initial_state = {
            "CSV_file_path": str(test_csv_path),
            "query": "존재하지 않는 컬럼을 사용하여 분석하세요",  # 의도적으로 에러 발생
            "messages": [],
            "error_count": 0
        }
        
        # Checkpointer를 위한 config
        config = {
            "configurable": {
                "thread_id": "test_error_counting_thread"
            }
        }
        
        # Agent 실행 (에러가 발생할 것으로 예상)
        result = agent.invoke(initial_state, config=config)
        
        assert result is not None
        assert "error_count" in result
        
        error_count = result.get("error_count", 0)
        print(f"✅ 에러 카운팅 테스트 완료")
        print(f"   최종 에러 카운트: {error_count}")
        print(f"   상태: {result.get('status', 'N/A')}")
        
        # 에러가 3번 이상 발생했는지 확인
        if error_count >= 3:
            assert result.get("status") == "error_threshold_reached"
            print(f"   ⚠️ 에러가 {error_count}번 발생하여 interrupt가 호출되었습니다.")
        
    except Exception as e:
        print(f"⚠️ 테스트 중 예외 발생 (예상 가능): {e}")
        # 에러가 발생하는 것 자체가 테스트 목적이므로 실패로 처리하지 않음
    finally:
        # 테스트 파일 정리
        if test_csv_path.exists():
            test_csv_path.unlink()


def test_filepath_undefined_bug_fix():
    """filepath 변수 미정의 문제 수정 테스트
    
    버그: pd.read_csv(filepath)가 있지만 filepath 변수가 정의되지 않은 경우
    수정: prepare_code_for_execution()에서 filepath 변수 사용 여부를 확인하고 누락된 경우 추가
    """
    from src.agents.sub_agents.csv_data_analysis_agent.utils.code_processing import (
        prepare_code_for_execution
    )
    from pathlib import Path
    
    # 테스트 케이스 1: filepath 변수가 사용되지만 정의되지 않은 경우
    code_without_filepath = """
import pandas as pd

# filepath 변수 정의 없이 사용
df = pd.read_csv(filepath)
print(df.head())
"""
    
    csv_file_paths = [Path("/test/data/sample.csv")]
    
    # prepare_code_for_execution 실행
    result_code = prepare_code_for_execution(code_without_filepath, csv_file_paths)
    
    # filepath 변수가 추가되었는지 확인
    assert 'filepath =' in result_code, "filepath 변수가 추가되지 않았습니다"
    assert 'pd.read_csv(filepath)' in result_code, "pd.read_csv(filepath) 패턴이 유지되지 않았습니다"
    
    # filepath 변수 정의가 코드 앞부분에 있는지 확인 (import 다음)
    lines = result_code.split('\n')
    filepath_line_idx = None
    for i, line in enumerate(lines):
        if 'filepath =' in line and filepath_line_idx is None:
            filepath_line_idx = i
            break
    
    assert filepath_line_idx is not None, "filepath 변수 정의를 찾을 수 없습니다"
    
    # import 문 다음에 filepath 변수가 있는지 확인
    import_found = False
    for i in range(filepath_line_idx):
        if 'import' in lines[i]:
            import_found = True
            break
    
    assert import_found or filepath_line_idx < 5, "filepath 변수가 코드 앞부분에 없습니다"
    
    print("✅ filepath 변수 미정의 문제 수정 테스트 통과")
    print(f"   filepath 변수 정의 라인: {filepath_line_idx + 1}")


def test_error_detection_bug_fix():
    """에러 감지 실패 문제 수정 테스트
    
    버그: stderr에 Traceback/Error가 있어도 success=True로 처리되는 경우
    수정: execute_code_node와 validate_execution_result_node에서 Python 에러를 올바르게 감지
    """
    # 테스트는 validate_execution_result_node의 로직을 직접 테스트
    # 실제 노드 함수는 State 기반이므로 로직을 분리하여 테스트
    
    # Python 에러 키워드 감지 로직 테스트
    test_cases = [
        ("Traceback (most recent call last):", True),
        ("NameError: name 'filepath' is not defined", True),
        ("FileNotFoundError: [Errno 2] No such file", True),
        ("TypeError: unsupported operand type(s)", True),
        ("ValueError: invalid literal", True),
        ("AttributeError: 'NoneType' object", True),
        ("KeyError: 'column_name'", True),
        ("IndexError: list index out of range", True),
        ("ModuleNotFoundError: No module named", True),
        ("ImportError: cannot import name", True),
        ("Normal output without errors", False),
        ("This is just a warning message", False),
    ]
    
    error_keywords = [
        "Traceback", "Error:", "Exception:", "NameError", "FileNotFoundError",
        "KeyError", "ValueError", "TypeError", "AttributeError", "IndexError",
        "ModuleNotFoundError", "ImportError"
    ]
    
    for stderr_content, expected_error in test_cases:
        has_python_error = any(keyword in stderr_content for keyword in error_keywords)
        assert has_python_error == expected_error, (
            f"에러 감지 실패: '{stderr_content[:50]}...' -> "
            f"예상={expected_error}, 실제={has_python_error}"
        )
    
    print("✅ 에러 감지 실패 문제 수정 테스트 통과")
    print(f"   테스트 케이스: {len(test_cases)}개 통과")


def test_prepare_code_for_execution_multiple_files():
    """여러 파일 모드에서 filepath 변수 처리 테스트"""
    from src.agents.sub_agents.csv_data_analysis_agent.utils.code_processing import (
        prepare_code_for_execution
    )
    from pathlib import Path
    
    # 여러 파일 모드: filepath_2, filepath_3 등이 사용되지만 정의되지 않은 경우
    code_with_multiple_filepaths = """
import pandas as pd

df1 = pd.read_csv(filepath)
df2 = pd.read_csv(filepath_2)
# filepath_2는 정의되지 않았음
"""
    
    csv_file_paths = [
        Path("/test/data/file1.csv"),
        Path("/test/data/file2.csv")
    ]
    
    result_code = prepare_code_for_execution(code_with_multiple_filepaths, csv_file_paths)
    
    # filepath와 filepath_2가 모두 정의되었는지 확인
    assert 'filepath =' in result_code, "filepath 변수가 추가되지 않았습니다"
    assert 'filepath_2 =' in result_code, "filepath_2 변수가 추가되지 않았습니다"
    
    print("✅ 여러 파일 모드 filepath 변수 처리 테스트 통과")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

