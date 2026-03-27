"""
Python 코드 실행 도구

생성된 Python 코드를 안전하게 실행하고 출력을 캡처하는 도구
- stdout/stderr 캡처
- 실행 시간 제한
- 보안 제약 (허용된 경로 내에서만 실행: 데이터 디렉토리 및 워크스페이스)
- 에러 처리 및 예외 캡처

⚠️ DEPRECATED: 이 모듈은 하위 호환성을 위해 유지되지만,
새로운 통합 코드 실행 시스템(src.tools.code_execution) 사용을 권장합니다.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional
from langchain.tools import tool


def _get_sanitized_env() -> dict:
    """환경 변수에서 민감한 정보를 제거한 안전한 환경 변수 딕셔너리를 반환

    Returns:
        필수 환경 변수만 포함하고 민감한 정보는 제외한 딕셔너리
    """
    # 허용할 필수 환경 변수 키들
    allowed_keys = ['PATH', 'HOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'USER', 'LANG', 'LC_ALL']

    # 차단할 민감한 키워드들 (대소문자 무시)
    sensitive_keywords = ['API_KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CREDENTIALS', 'AUTH']

    sanitized_env = {}

    for key, value in os.environ.items():
        # 민감한 키워드가 포함되어 있으면 제외
        key_upper = key.upper()
        if any(keyword in key_upper for keyword in sensitive_keywords):
            continue

        # 허용 목록에 있는 키만 포함
        if key in allowed_keys:
            sanitized_env[key] = value

    # PYTHONUNBUFFERED 추가 (항상 필요)
    sanitized_env['PYTHONUNBUFFERED'] = '1'

    return sanitized_env

# 프로젝트 루트 및 경로 설정 (범용 경로 유틸리티 사용)
try:
    from src.utils.paths import get_project_root, get_data_directory, get_workspace_directory
    _project_root = get_project_root()
    _data_directory = get_data_directory()
    _workspace_directory = get_workspace_directory()
    
    # 허용된 작업 디렉토리 (데이터 디렉토리와 워크스페이스 디렉토리 허용)
    _allowed_paths = [
        _data_directory.resolve(),
        _workspace_directory.resolve(),
    ]
except ImportError:
    # 하위 호환성: 경로 유틸리티가 없는 경우 기본값 사용
    _current_file = Path(__file__).resolve()
    _project_root = _current_file.parent.parent.parent
    _allowed_paths = [
        _project_root / "data",
        _project_root / "workspace",
    ]
    # 디렉토리가 없으면 생성
    for path in _allowed_paths:
        path.mkdir(parents=True, exist_ok=True)
        path.resolve()


def _is_path_allowed(filepath: Path) -> bool:
    """파일 경로가 허용된 경로 내에 있는지 확인
    
    Args:
        filepath: 확인할 파일 경로
        
    Returns:
        허용된 경로 내에 있으면 True, 아니면 False
    """
    try:
        resolved_path = filepath.resolve()
        # 여러 허용 경로 중 하나라도 매칭되면 허용
        for allowed_path in _allowed_paths:
            if resolved_path.is_relative_to(allowed_path):
                return True
        return False
    except Exception:
        return False


def _validate_code_security(code: str) -> tuple[bool, Optional[str]]:
    """코드의 보안 검증

    위험한 함수나 모듈 사용을 차단합니다.

    Args:
        code: 검증할 코드 문자열

    Returns:
        (is_safe, error_message) 튜플
    """
    # 차단할 위험한 패턴들
    dangerous_patterns = [
        ('import os', 'os 모듈의 위험한 함수 사용 가능'),
        ('import sys', 'sys 모듈의 위험한 함수 사용 가능'),
        ('import subprocess', 'subprocess 직접 사용 차단'),
        ('__import__', '동적 import 차단'),
        ('eval(', 'eval 함수 사용 차단'),
        ('exec(', 'exec 함수 사용 차단'),
        ('compile(', 'compile 함수 사용 차단'),
        ('open(', '파일 시스템 직접 접근 차단'),
        ('file(', '파일 시스템 직접 접근 차단'),
    ]

    code_lower = code.lower()

    # 위험한 패턴 검사 - 각 패턴을 독립적으로 검사
    for pattern, reason in dangerous_patterns:
        if pattern.lower() in code_lower:
            return False, f"보안: {reason} ({pattern})"

    return True, None


@tool("execute_python_code")
def execute_python_code_tool(
    code: str,
    timeout: int = 30,
    working_directory: Optional[str] = None
) -> str:
    """Python 코드를 실행하고 출력을 반환합니다.
    
    생성된 데이터 분석 코드를 실행하여 결과를 얻습니다.
    stdout과 stderr를 모두 캡처하여 반환합니다.
    
    Args:
        code: 실행할 Python 코드 문자열
        timeout: 실행 시간 제한 (초, 기본값: 30)
        working_directory: 작업 디렉토리 (None이면 프로젝트 루트)
        
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
            work_dir = _allowed_paths[0]  # 기본값은 tests 디렉토리
        
        # 가상환경 Python 경로 확인
        venv_python = _project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            python_executable = str(venv_python)
        else:
            # 가상환경이 없으면 시스템 Python 사용
            python_executable = sys.executable
        
        # 코드를 임시 파일로 저장 (디버깅 용이)
        # 실제로는 stdin으로 전달하지만, 에러 메시지에서 참조할 수 있도록
        temp_code_file = None
        try:
            # subprocess로 코드 실행
            # -u: unbuffered output (실시간 출력)
            # -c: 코드 문자열 실행
            process = subprocess.Popen(
                [python_executable, "-u", "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(work_dir),
                env=_get_sanitized_env()
            )
            
            try:
                # 타임아웃과 함께 실행
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                # 타임아웃 발생 시 프로세스 종료
                process.kill()
                process.wait()
                return f"❌ 코드 실행 시간 초과 (제한: {timeout}초)\n\n실행 중인 프로세스가 종료되었습니다."
            
            # 결과 포맷팅
            result_parts = []
            
            if stdout:
                result_parts.append(f"📊 실행 결과 (stdout):\n{stdout}")
            
            if stderr:
                if return_code == 0:
                    # 경고일 수 있음
                    result_parts.append(f"⚠️ 경고 (stderr):\n{stderr}")
                else:
                    # 에러
                    result_parts.append(f"❌ 에러 (stderr):\n{stderr}")
            
            if return_code != 0:
                result_parts.append(f"\n❌ 종료 코드: {return_code}")
            
            if not result_parts:
                result_parts.append("✅ 코드 실행 완료 (출력 없음)")
            
            return "\n\n".join(result_parts)
            
        except Exception as e:
            return f"❌ 코드 실행 중 오류 발생: {str(e)}\n\n에러 타입: {type(e).__name__}"
            
    except Exception as e:
        return f"❌ 도구 실행 중 오류 발생: {str(e)}"


@tool("execute_python_file")
def execute_python_file_tool(
    filepath: str,
    timeout: int = 30,
    args: Optional[list] = None
) -> str:
    """Python 파일을 실행하고 출력을 반환합니다.
    
    Args:
        filepath: 실행할 Python 파일 경로
        timeout: 실행 시간 제한 (초, 기본값: 30)
        args: 스크립트에 전달할 인자 리스트 (선택사항)
        
    Returns:
        실행 결과 문자열 (stdout + stderr)
    """
    try:
        path = Path(filepath).expanduser().resolve()
        
        # 보안: 허용된 경로 외부 접근 제한
        if not _is_path_allowed(path):
            allowed_paths_str = ", ".join([str(p) for p in _allowed_paths])
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다. (허용 경로: {allowed_paths_str})"
        
        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        if not path.is_file():
            return f"❌ 경로가 파일이 아닙니다: {filepath}"
        
        if not path.suffix == ".py":
            return f"❌ Python 파일이 아닙니다: {filepath}"
        
        # 가상환경 Python 경로 확인
        venv_python = _project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            python_executable = str(venv_python)
        else:
            python_executable = sys.executable
        
        # 파일 내용 읽기 (보안 검증용)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            return f"❌ 파일 읽기 실패: {str(e)}"
        
        # 보안 검증
        is_safe, error_msg = _validate_code_security(file_content)
        if not is_safe:
            return f"❌ 보안 검증 실패: {error_msg}\n\n파일 실행이 차단되었습니다."
        
        # subprocess로 파일 실행
        cmd = [python_executable, str(path)]
        if args:
            cmd.extend(args)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(path.parent),
            env=_get_sanitized_env()
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return f"❌ 파일 실행 시간 초과 (제한: {timeout}초)\n\n파일: {filepath}"
        
        # 결과 포맷팅
        result_parts = []
        
        if stdout:
            result_parts.append(f"📊 실행 결과 (stdout):\n{stdout}")
        
        if stderr:
            if return_code == 0:
                result_parts.append(f"⚠️ 경고 (stderr):\n{stderr}")
            else:
                result_parts.append(f"❌ 에러 (stderr):\n{stderr}")
        
        if return_code != 0:
            result_parts.append(f"\n❌ 종료 코드: {return_code}")
        
        if not result_parts:
            result_parts.append("✅ 파일 실행 완료 (출력 없음)")
        
        return "\n\n".join(result_parts)
        
    except Exception as e:
        return f"❌ 도구 실행 중 오류 발생: {str(e)}"

