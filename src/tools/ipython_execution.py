"""
IPython 코드 실행 도구

IPython shell을 사용하여 Python 코드를 실행하고 결과를 반환하는 도구
- IPython shell에서 코드 실행
- 실행 결과 캡처 (stdout, stderr, 변수 상태)
- 실행 시간 제한
- 보안 제약

⚠️ DEPRECATED: 이 모듈은 하위 호환성을 위해 유지되지만,
새로운 통합 코드 실행 시스템(src.tools.code_execution)의 IPythonExecutor 사용을 권장합니다.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.tools import tool

# 프로젝트 루트 및 경로 설정
try:
    from src.utils.paths import get_project_root, get_data_directory, get_workspace_directory
    _project_root = get_project_root()
    _data_directory = get_data_directory()
    _workspace_directory = get_workspace_directory()
    
    _allowed_paths = [
        _data_directory.resolve(),
        _workspace_directory.resolve(),
    ]
except ImportError:
    _current_file = Path(__file__).resolve()
    _project_root = _current_file.parent.parent.parent
    _allowed_paths = [
        _project_root / "data",
        _project_root / "workspace",
    ]
    for path in _allowed_paths:
        path.mkdir(parents=True, exist_ok=True)
        path.resolve()


def _get_sanitized_env() -> Dict[str, str]:
    """환경 변수를 sanitize하여 안전한 환경 변수만 반환"""
    safe_keys = {
        "PATH", "HOME", "PYTHONPATH", "VIRTUAL_ENV",
        "USER", "LANG", "LC_ALL", "PYTHONUNBUFFERED"
    }

    sensitive_substrings = {
        "API_KEY", "SECRET", "TOKEN", "PASSWORD",
        "CREDENTIALS", "AUTH"
    }

    sanitized = {}
    for key, value in os.environ.items():
        # 안전한 키 목록에 있거나, 민감한 문자열을 포함하지 않는 경우
        if key in safe_keys or not any(sensitive in key.upper() for sensitive in sensitive_substrings):
            sanitized[key] = value

    # PYTHONUNBUFFERED는 항상 설정
    sanitized["PYTHONUNBUFFERED"] = "1"

    return sanitized


def _is_path_allowed(filepath: Path) -> bool:
    """파일 경로가 허용된 경로 내에 있는지 확인"""
    try:
        resolved_path = filepath.resolve()
        for allowed_path in _allowed_paths:
            if resolved_path.is_relative_to(allowed_path):
                return True
        return False
    except Exception:
        return False


def _validate_code_security(code: str) -> tuple[bool, Optional[str]]:
    """코드의 보안 검증"""
    dangerous_patterns = [
        ('__import__', '동적 import 차단'),
        ('eval(', 'eval 함수 사용 차단'),
        ('exec(', 'exec 함수 사용 차단'),
        ('compile(', 'compile 함수 사용 차단'),
    ]
    
    for pattern, reason in dangerous_patterns:
        if pattern in code:
            return False, f"{reason}: {pattern}"
    
    return True, None


@tool("execute_ipython_code")
def execute_ipython_code_tool(
    code: str,
    timeout: int = 60,
    working_directory: Optional[str] = None,
    capture_output: bool = True
) -> str:
    """IPython shell에서 Python 코드를 실행하고 출력을 반환합니다.
    
    IPython을 사용하여 대화형 코드 실행을 지원합니다.
    실행 결과는 stdout과 stderr를 모두 캡처하여 반환합니다.
    
    Args:
        code: 실행할 Python 코드 문자열 (IPython 코드 블록)
        timeout: 실행 시간 제한 (초, 기본값: 60)
        working_directory: 작업 디렉토리 (None이면 프로젝트 루트)
        capture_output: 출력 캡처 여부 (기본값: True)
        
    Returns:
        실행 결과 문자열 (stdout + stderr)
    """
    try:
        # 보안 검증
        is_safe, error_msg = _validate_code_security(code)
        if not is_safe:
            return f"❌ 보안 검증 실패: {error_msg}\n\n코드 실행이 차단되었습니다."
        
        # 작업 디렉토리 설정
        if working_directory:
            work_dir = Path(working_directory).expanduser().resolve()
            if not _is_path_allowed(work_dir):
                allowed_paths_str = ", ".join([str(p) for p in _allowed_paths])
                return f"❌ 보안: 작업 디렉토리가 허용된 경로 외부입니다: {working_directory} (허용 경로: {allowed_paths_str})"
        else:
            work_dir = _allowed_paths[0]  # 기본값은 data 디렉토리
        
        # 가상환경 IPython 경로 확인
        venv_ipython = _project_root / ".venv" / "bin" / "ipython"
        venv_python = _project_root / ".venv" / "bin" / "python"
        
        # IPython이 설치되어 있는지 확인
        if venv_ipython.exists():
            ipython_executable = str(venv_ipython)
        elif venv_python.exists():
            # IPython이 없으면 Python으로 IPython 실행 시도
            ipython_executable = str(venv_python)
            # IPython 모듈로 실행
            cmd = [ipython_executable, "-m", "IPython", "--simple-prompt", "-c"]
        else:
            # 시스템 Python 사용
            ipython_executable = sys.executable
            cmd = [ipython_executable, "-m", "IPython", "--simple-prompt", "-c"]
        
        # IPython 실행 명령 구성
        if venv_ipython.exists():
            # IPython 직접 실행
            cmd = [ipython_executable, "--simple-prompt", "-c"]
        else:
            # Python -m IPython 실행
            cmd = [ipython_executable, "-m", "IPython", "--simple-prompt", "-c"]
        
        # 코드 실행
        try:
            process = subprocess.Popen(
                cmd + [code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(work_dir),
                env=_get_sanitized_env()
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return f"❌ 코드 실행 시간 초과 (제한: {timeout}초)\n\n실행 중인 프로세스가 종료되었습니다."
            
            # 결과 포맷팅
            result_parts = []
            
            if stdout:
                result_parts.append(f"📊 실행 결과 (stdout):\n{stdout}")
            
            if stderr:
                # IPython의 경고 메시지 필터링
                filtered_stderr = []
                for line in stderr.split('\n'):
                    # IPython 시작 메시지 등 필터링
                    if not any(skip in line.lower() for skip in [
                        'python', 'ipython', 'type', 'quit', 'exit',
                        'use', 'for', 'more', 'information'
                    ]):
                        filtered_stderr.append(line)
                
                filtered_stderr_str = '\n'.join(filtered_stderr).strip()
                if filtered_stderr_str:
                    if return_code == 0:
                        result_parts.append(f"⚠️ 경고 (stderr):\n{filtered_stderr_str}")
                    else:
                        result_parts.append(f"❌ 에러 (stderr):\n{filtered_stderr_str}")
            
            if return_code != 0:
                result_parts.append(f"\n❌ 종료 코드: {return_code}")
            
            if not result_parts:
                result_parts.append("✅ 코드 실행 완료 (출력 없음)")
            
            return "\n\n".join(result_parts)
            
        except FileNotFoundError:
            # IPython이 설치되지 않은 경우 Python으로 폴백
            return _execute_with_python_fallback(code, timeout, work_dir)
        except Exception as e:
            return f"❌ IPython 실행 중 오류 발생: {str(e)}\n\n에러 타입: {type(e).__name__}"
            
    except Exception as e:
        return f"❌ 도구 실행 중 오류 발생: {str(e)}"


def _execute_with_python_fallback(code: str, timeout: int, work_dir: Path) -> str:
    """IPython이 없을 때 Python으로 폴백 실행"""
    venv_python = _project_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        python_executable = str(venv_python)
    else:
        python_executable = sys.executable
    
    try:
        process = subprocess.Popen(
            [python_executable, "-u", "-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(work_dir),
            env=_get_sanitized_env()
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return f"❌ 코드 실행 시간 초과 (제한: {timeout}초)"
        
        result_parts = []
        if stdout:
            result_parts.append(f"📊 실행 결과:\n{stdout}")
        if stderr:
            if return_code == 0:
                result_parts.append(f"⚠️ 경고:\n{stderr}")
            else:
                result_parts.append(f"❌ 에러:\n{stderr}")
        if return_code != 0:
            result_parts.append(f"\n❌ 종료 코드: {return_code}")
        
        if not result_parts:
            result_parts.append("✅ 코드 실행 완료 (출력 없음)")
        
        return "\n\n".join(result_parts)
    except Exception as e:
        return f"❌ Python 폴백 실행 중 오류 발생: {str(e)}"


