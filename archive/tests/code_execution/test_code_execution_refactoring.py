"""
코드 실행 리팩토링 테스트

통합된 코드 실행 시스템이 제대로 작동하는지 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.code_execution import (
    CodeExecutionFactory,
    ExecutionEnvironment,
    ExecutionConfig,
    execute_code_locally,
    execute_code_in_docker,
    execute_code_in_ipython,
    execute_code_in_repl
)
from src.tools.code_execution.utils import (
    validate_code_security,
    is_path_allowed,
    get_allowed_paths
)


def test_security_validation():
    """보안 검증 테스트"""
    print("=" * 60)
    print("테스트 1: 보안 검증")
    print("=" * 60)
    
    # 안전한 코드
    safe_code = """
import pandas as pd
import numpy as np
df = pd.DataFrame({'a': [1, 2, 3]})
print(df)
"""
    is_safe, error = validate_code_security(safe_code, strict_mode=True)
    print(f"✅ 안전한 코드: {is_safe} (예상: True)")
    assert is_safe, "안전한 코드가 차단되었습니다"
    
    # 위험한 코드
    dangerous_code = """
import os
os.system('rm -rf /')
"""
    is_safe, error = validate_code_security(dangerous_code, strict_mode=True)
    print(f"❌ 위험한 코드: {is_safe} (예상: False)")
    print(f"   오류 메시지: {error}")
    assert not is_safe, "위험한 코드가 허용되었습니다"
    
    print("✅ 보안 검증 테스트 통과\n")


def test_path_validation():
    """경로 검증 테스트"""
    print("=" * 60)
    print("테스트 2: 경로 검증")
    print("=" * 60)
    
    allowed_paths = get_allowed_paths()
    print(f"허용된 경로: {[str(p) for p in allowed_paths]}")
    
    # 허용된 경로 테스트
    if allowed_paths:
        test_path = allowed_paths[0] / "test.py"
        is_allowed = is_path_allowed(test_path)
        print(f"✅ 허용된 경로: {is_allowed} (예상: True)")
        assert is_allowed, "허용된 경로가 차단되었습니다"
    
    # 차단된 경로 테스트
    blocked_path = Path("/etc/passwd")
    is_allowed = is_path_allowed(blocked_path)
    print(f"❌ 차단된 경로: {is_allowed} (예상: False)")
    assert not is_allowed, "차단된 경로가 허용되었습니다"
    
    print("✅ 경로 검증 테스트 통과\n")


def test_local_executor():
    """로컬 Executor 테스트"""
    print("=" * 60)
    print("테스트 3: 로컬 Executor")
    print("=" * 60)
    
    # 테스트 코드 파일 생성
    test_code = """
print("Hello, World!")
print("테스트 성공!")
"""
    
    test_file = project_root / "workspace" / "test_code_execution.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code, encoding='utf-8')
    
    try:
        result = execute_code_locally(
            code_file=str(test_file),
            timeout=10
        )
        
        print(f"실행 성공: {result.success}")
        print(f"종료 코드: {result.exit_code}")
        print(f"출력:\n{result.stdout}")
        
        assert result.success, "로컬 실행이 실패했습니다"
        assert "Hello, World!" in result.stdout, "예상된 출력이 없습니다"
        
        print("✅ 로컬 Executor 테스트 통과\n")
    finally:
        # 테스트 파일 정리
        if test_file.exists():
            test_file.unlink()


def test_factory():
    """Factory 테스트"""
    print("=" * 60)
    print("테스트 4: CodeExecutionFactory")
    print("=" * 60)
    
    # 사용 가능한 환경 확인
    available_envs = CodeExecutionFactory.get_available_environments()
    print(f"사용 가능한 실행 환경: {[e.value for e in available_envs]}")
    
    # Local Executor 생성
    local_executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.LOCAL)
    print(f"✅ Local Executor 생성 성공: {local_executor.get_environment().value}")
    assert local_executor.get_environment() == ExecutionEnvironment.LOCAL
    
    # REPL Executor 생성
    repl_executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.REPL)
    print(f"✅ REPL Executor 생성 성공: {repl_executor.get_environment().value}")
    assert repl_executor.get_environment() == ExecutionEnvironment.REPL
    
    print("✅ Factory 테스트 통과\n")


def test_repl_executor():
    """REPL Executor 테스트"""
    print("=" * 60)
    print("테스트 5: REPL Executor (세션 상태 유지)")
    print("=" * 60)
    
    # 테스트 코드 파일 생성
    test_code1 = """
x = 10
print(f"x = {x}")
"""
    
    test_code2 = """
y = x + 5
print(f"y = {y}")
"""
    
    test_file1 = project_root / "workspace" / "test_repl1.py"
    test_file2 = project_root / "workspace" / "test_repl2.py"
    test_file1.parent.mkdir(parents=True, exist_ok=True)
    test_file1.write_text(test_code1, encoding='utf-8')
    test_file2.write_text(test_code2, encoding='utf-8')
    
    try:
        # 첫 번째 코드 실행
        result1 = execute_code_in_repl(
            code_file=str(test_file1),
            session_id="test_session",
            timeout=10
        )
        
        print(f"첫 번째 실행 성공: {result1.success}")
        print(f"출력:\n{result1.stdout}")
        assert result1.success, "첫 번째 실행이 실패했습니다"
        
        # 두 번째 코드 실행 (세션 상태 유지)
        result2 = execute_code_in_repl(
            code_file=str(test_file2),
            session_id="test_session",  # 같은 세션 ID
            timeout=10
        )
        
        print(f"두 번째 실행 성공: {result2.success}")
        print(f"출력:\n{result2.stdout}")
        assert result2.success, "두 번째 실행이 실패했습니다"
        assert "y = 15" in result2.stdout, "세션 상태가 유지되지 않았습니다"
        
        # 누적 출력 확인
        accumulated = result2.metadata.get("accumulated_output", "")
        print(f"누적 출력 길이: {len(accumulated)} 문자")
        assert len(accumulated) > 0, "누적 출력이 없습니다"
        
        print("✅ REPL Executor 테스트 통과\n")
    finally:
        # 테스트 파일 정리
        for f in [test_file1, test_file2]:
            if f.exists():
                f.unlink()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("코드 실행 리팩토링 테스트 시작")
    print("=" * 60 + "\n")
    
    try:
        test_security_validation()
        test_path_validation()
        test_local_executor()
        test_factory()
        test_repl_executor()
        
        print("=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

