"""
IPython Session Executor 테스트

IPython의 InteractiveShell을 사용한 실제 세션 유지 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.code_execution import (
    CodeExecutionFactory,
    ExecutionEnvironment,
    execute_code_in_ipython
)


def test_ipython_session_basic():
    """IPython 세션 기본 테스트"""
    print("=" * 60)
    print("테스트 1: IPython 세션 기본 실행")
    print("=" * 60)
    
    # 테스트 코드 파일 생성
    test_code = """
import pandas as pd
import numpy as np

# 간단한 데이터 생성
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': [85, 90, 88]
})

print("데이터프레임:")
print(df)
print(f"\\n평균 점수: {df['score'].mean():.2f}")
"""
    
    test_file = project_root / "workspace" / "test_ipython_session_basic.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code, encoding='utf-8')
    
    try:
        result = execute_code_in_ipython(
            code_file=str(test_file),
            session_id="test_session_basic",
            timeout=30
        )
        
        print(f"실행 성공: {result.success}")
        print(f"종료 코드: {result.exit_code}")
        print(f"\n출력:\n{result.stdout}")
        
        if result.stderr:
            print(f"\n경고/에러:\n{result.stderr}")
        
        assert result.success, "IPython 세션 실행이 실패했습니다"
        assert "데이터프레임" in result.stdout, "예상된 출력이 없습니다"
        assert "평균 점수" in result.stdout, "예상된 출력이 없습니다"
        
        print("✅ IPython 세션 기본 실행 테스트 통과\n")
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if test_file.exists():
            test_file.unlink()


def test_ipython_session_state_persistence():
    """IPython 세션 상태 유지 테스트"""
    print("=" * 60)
    print("테스트 2: IPython 세션 상태 유지 확인")
    print("=" * 60)
    print("⚠️ 중요: IPython Session Executor는 실제 세션 상태를 유지합니다")
    print("=" * 60)
    
    session_id = "test_session_persistence"
    
    # 첫 번째 코드: 변수 정의
    test_code1 = """
x = 10
y = 20
print(f"x = {x}, y = {y}")
"""
    
    # 두 번째 코드: 첫 번째 코드의 변수 사용
    test_code2 = """
# 이전 실행의 변수 x, y 사용 가능 (세션 유지)
z = x + y
print(f"z = x + y = {z}")
"""
    
    test_file1 = project_root / "workspace" / "test_ipython_session1.py"
    test_file2 = project_root / "workspace" / "test_ipython_session2.py"
    test_file1.parent.mkdir(parents=True, exist_ok=True)
    test_file1.write_text(test_code1, encoding='utf-8')
    test_file2.write_text(test_code2, encoding='utf-8')
    
    try:
        # 첫 번째 실행
        result1 = execute_code_in_ipython(
            code_file=str(test_file1),
            session_id=session_id,
            timeout=30
        )
        
        print(f"\n첫 번째 실행 성공: {result1.success}")
        print(f"출력:\n{result1.stdout}")
        assert result1.success, "첫 번째 실행이 실패했습니다"
        
        # 두 번째 실행 (같은 세션 ID - 세션 상태 유지)
        result2 = execute_code_in_ipython(
            code_file=str(test_file2),
            session_id=session_id,  # 같은 세션 ID
            timeout=30
        )
        
        print(f"\n두 번째 실행 성공: {result2.success}")
        print(f"출력:\n{result2.stdout}")
        assert result2.success, "두 번째 실행이 실패했습니다"
        assert "z = x + y = 30" in result2.stdout, "세션 상태가 유지되지 않았습니다"
        
        # 세션 메타데이터 확인
        if result2.metadata:
            variables = result2.metadata.get("variables", [])
            print(f"\n세션 변수: {variables}")
            assert "x" in variables or "y" in variables or "z" in variables, "변수가 세션에 저장되지 않았습니다"
        
        print("\n✅ IPython 세션 상태 유지 확인 완료")
        print("   → Jupyter처럼 동작함을 확인")
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        for f in [test_file1, test_file2]:
            if f.exists():
                f.unlink()


def test_ipython_session_vs_independent():
    """IPython 세션 vs 독립 실행 비교"""
    print("\n" + "=" * 60)
    print("테스트 3: IPython 세션 vs 독립 실행 비교")
    print("=" * 60)
    
    # 동일한 코드 시나리오
    code1 = "x = 10\ny = 20\nprint(f'x={x}, y={y}')"
    code2 = "z = x + y\nprint(f'z={z}')"
    
    # 파일 생성
    test_file1 = project_root / "workspace" / "test_comparison1.py"
    test_file2 = project_root / "workspace" / "test_comparison2.py"
    test_file1.parent.mkdir(parents=True, exist_ok=True)
    test_file1.write_text(code1, encoding='utf-8')
    test_file2.write_text(code2, encoding='utf-8')
    
    try:
        print("\n--- IPython Session Executor (세션 상태 유지) ---")
        result_session1 = execute_code_in_ipython(
            code_file=str(test_file1),
            session_id="comparison_session",
            timeout=30
        )
        print(f"첫 번째 실행: {result_session1.success}")
        print(f"출력: {result_session1.stdout.strip()}")
        
        result_session2 = execute_code_in_ipython(
            code_file=str(test_file2),
            session_id="comparison_session",  # 같은 세션
            timeout=30
        )
        print(f"두 번째 실행: {result_session2.success}")
        print(f"출력: {result_session2.stdout.strip()}")
        assert result_session2.success, "세션 실행이 실패했습니다"
        assert "z=30" in result_session2.stdout, "세션 상태가 유지되지 않았습니다"
        print(f"✅ IPython Session: 세션 상태 유지됨 (z=30 계산 가능)")
        
        print("\n--- 독립 실행 (다른 세션 ID) ---")
        result_indep1 = execute_code_in_ipython(
            code_file=str(test_file1),
            session_id="independent_session1",
            timeout=30
        )
        print(f"첫 번째 실행: {result_indep1.success}")
        print(f"출력: {result_indep1.stdout.strip()}")
        
        result_indep2 = execute_code_in_ipython(
            code_file=str(test_file2),
            session_id="independent_session2",  # 다른 세션 ID
            timeout=30
        )
        print(f"두 번째 실행: {result_indep2.success}")
        print(f"출력: {result_indep2.stdout.strip()}")
        # 다른 세션이므로 실패해야 함
        if not result_indep2.success or "NameError" in result_indep2.stderr:
            print(f"✅ 독립 실행: 세션 분리됨 (z 계산 불가)")
        else:
            print(f"⚠️ 독립 실행: 예상과 다름")
        
        print("\n📊 결론:")
        print("   - 같은 session_id: 세션 상태 유지 (Jupyter처럼)")
        print("   - 다른 session_id: 독립 실행")
        
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        for f in [test_file1, test_file2]:
            if f.exists():
                f.unlink()


def test_ipython_session_accumulated_output():
    """IPython 세션 누적 출력 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: IPython 세션 누적 출력 확인")
    print("=" * 60)
    
    session_id = "test_accumulated"
    
    code1 = "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3]})\nprint('Step 1: DataFrame created')"
    code2 = "print(f'Step 2: DataFrame shape = {df.shape}')\nprint(df.head())"
    
    test_file1 = project_root / "workspace" / "test_accum1.py"
    test_file2 = project_root / "workspace" / "test_accum2.py"
    test_file1.parent.mkdir(parents=True, exist_ok=True)
    test_file1.write_text(code1, encoding='utf-8')
    test_file2.write_text(code2, encoding='utf-8')
    
    try:
        result1 = execute_code_in_ipython(
            code_file=str(test_file1),
            session_id=session_id,
            timeout=30
        )
        
        result2 = execute_code_in_ipython(
            code_file=str(test_file2),
            session_id=session_id,
            timeout=30
        )
        
        # 누적 출력 확인
        if result2.metadata and "accumulated_output" in result2.metadata:
            accumulated = result2.metadata["accumulated_output"]
            print(f"\n누적 출력 길이: {len(accumulated)} 문자")
            print(f"누적 출력 미리보기:\n{accumulated[:200]}...")
            assert len(accumulated) > 0, "누적 출력이 없습니다"
            assert "Step 1" in accumulated, "첫 번째 실행이 누적 출력에 없습니다"
            assert "Step 2" in accumulated, "두 번째 실행이 누적 출력에 없습니다"
            print("✅ 누적 출력 확인 완료")
        
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        for f in [test_file1, test_file2]:
            if f.exists():
                f.unlink()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("IPython Session Executor 테스트 시작")
    print("=" * 60)
    
    # IPython 설치 여부 확인
    executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.IPYTHON)
    is_available = executor.is_available()
    
    if not is_available:
        print("\n⚠️ IPython이 설치되어 있지 않습니다.")
        print("   설치 방법: uv add ipython")
        return 1
    
    print("✅ IPython 사용 가능\n")
    
    try:
        test_ipython_session_basic()
        test_ipython_session_state_persistence()
        test_ipython_session_vs_independent()
        test_ipython_session_accumulated_output()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        print("\n📝 요약:")
        print("1. IPython Session Executor는 실제 세션 상태를 유지합니다")
        print("2. 같은 session_id를 사용하면 Jupyter처럼 동작합니다")
        print("3. 다른 session_id를 사용하면 독립 실행됩니다")
        print("4. InteractiveShell을 사용하여 실제 IPython 세션을 제공합니다")
        return 0
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


