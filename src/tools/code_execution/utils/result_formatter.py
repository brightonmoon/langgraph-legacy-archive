"""
Result Formatter - 실행 결과 포맷팅 유틸리티

레거시 코드와의 호환성을 유지하면서 통합된 결과 포맷팅 제공
"""

from typing import Optional, Dict, Any
from ..base import ExecutionResult


def format_execution_result(
    result: ExecutionResult,
    legacy_format: bool = False,
    filter_stderr: Optional[list] = None
) -> str:
    """실행 결과를 읽기 쉬운 문자열로 포맷팅 (통합)
    
    Args:
        result: 실행 결과
        legacy_format: 레거시 포맷 사용 여부 (기본값: False)
                      - True: 기존 code_execution.py 스타일 포맷
                      - False: 새로운 통합 포맷
        filter_stderr: stderr 필터링 키워드 리스트 (IPython 등에서 사용)
    
    Returns:
        포맷팅된 결과 문자열
    """
    if legacy_format:
        return _format_legacy(result, filter_stderr)
    else:
        return _format_unified(result, filter_stderr)


def _format_legacy(result: ExecutionResult, filter_stderr: Optional[list] = None) -> str:
    """레거시 포맷 (기존 code_execution.py 스타일)"""
    result_parts = []
    
    if result.stdout:
        result_parts.append(f"📊 실행 결과 (stdout):\n{result.stdout}")
    
    if result.stderr:
        # stderr 필터링 (IPython 등에서 사용)
        stderr_text = result.stderr
        if filter_stderr:
            filtered_lines = []
            for line in stderr_text.split('\n'):
                if not any(skip.lower() in line.lower() for skip in filter_stderr):
                    filtered_lines.append(line)
            stderr_text = '\n'.join(filtered_lines).strip()
        
        if stderr_text:
            if result.exit_code == 0:
                result_parts.append(f"⚠️ 경고 (stderr):\n{stderr_text}")
            else:
                result_parts.append(f"❌ 에러 (stderr):\n{stderr_text}")
    
    if result.exit_code != 0:
        result_parts.append(f"\n❌ 종료 코드: {result.exit_code}")
    
    if result.error:
        result_parts.append(f"❌ 오류: {result.error}")
    
    if not result_parts:
        result_parts.append("✅ 코드 실행 완료 (출력 없음)")
    
    return "\n\n".join(result_parts)


def _format_unified(result: ExecutionResult, filter_stderr: Optional[list] = None) -> str:
    """통합 포맷 (새로운 스타일)"""
    parts = []
    
    if result.success:
        parts.append("✅ 코드 실행 성공")
    else:
        parts.append("❌ 코드 실행 실패")
    
    if result.stdout:
        parts.append(f"\n📊 실행 결과 (stdout):\n{result.stdout}")
    
    if result.stderr:
        # stderr 필터링 (IPython 등에서 사용)
        stderr_text = result.stderr
        if filter_stderr:
            filtered_lines = []
            for line in stderr_text.split('\n'):
                if not any(skip.lower() in line.lower() for skip in filter_stderr):
                    filtered_lines.append(line)
            stderr_text = '\n'.join(filtered_lines).strip()
        
        if stderr_text:
            if result.exit_code == 0:
                parts.append(f"\n⚠️ 경고 출력 (stderr):\n{stderr_text}")
            else:
                parts.append(f"\n❌ 에러 출력 (stderr):\n{stderr_text}")
    
    if result.error:
        parts.append(f"\n❌ 오류: {result.error}")
    
    if result.output_files:
        parts.append(f"\n📁 생성된 출력 파일:")
        for file in result.output_files:
            parts.append(f"  - {file}")
    
    if result.execution_time > 0:
        parts.append(f"\n⏱️ 실행 시간: {result.execution_time:.2f}초")
    
    parts.append(f"🔢 종료 코드: {result.exit_code}")
    
    if result.metadata:
        parts.append(f"\n📋 메타데이터:")
        for key, value in result.metadata.items():
            parts.append(f"  - {key}: {value}")
    
    return "\n".join(parts)


def format_simple_result(
    stdout: str = "",
    stderr: str = "",
    return_code: int = 0,
    error: Optional[str] = None,
    filter_stderr: Optional[list] = None
) -> str:
    """간단한 결과 포맷팅 (레거시 호환)
    
    ExecutionResult 객체 없이 직접 포맷팅하는 편의 함수
    
    Args:
        stdout: 표준 출력
        stderr: 표준 에러 출력
        return_code: 종료 코드
        error: 오류 메시지
        filter_stderr: stderr 필터링 키워드 리스트
    
    Returns:
        포맷팅된 결과 문자열
    """
    result_parts = []
    
    if stdout:
        result_parts.append(f"📊 실행 결과 (stdout):\n{stdout}")
    
    if stderr:
        # stderr 필터링
        stderr_text = stderr
        if filter_stderr:
            filtered_lines = []
            for line in stderr_text.split('\n'):
                if not any(skip.lower() in line.lower() for skip in filter_stderr):
                    filtered_lines.append(line)
            stderr_text = '\n'.join(filtered_lines).strip()
        
        if stderr_text:
            if return_code == 0:
                result_parts.append(f"⚠️ 경고 (stderr):\n{stderr_text}")
            else:
                result_parts.append(f"❌ 에러 (stderr):\n{stderr_text}")
    
    if return_code != 0:
        result_parts.append(f"\n❌ 종료 코드: {return_code}")
    
    if error:
        result_parts.append(f"❌ 오류: {error}")
    
    if not result_parts:
        result_parts.append("✅ 코드 실행 완료 (출력 없음)")
    
    return "\n\n".join(result_parts)

