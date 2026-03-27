"""
Context 추출 유틸리티

실행 결과(stdout/stderr)에서 인사이트, 패턴, 통계 정보 등을 추출합니다.
stdout/stderr 기반으로 context를 추출하여 다음 코드 생성에 활용합니다.
"""

import re
from typing import Dict, Any, List, Optional
from ..base import ExecutionResult


def extract_context_from_result(
    result: ExecutionResult,
    user_query: Optional[str] = None
) -> Dict[str, Any]:
    """실행 결과에서 Context 추출 (stdout/stderr 기반)
    
    stdout/stderr에서 의미있는 정보를 추출하여
    다음 코드 생성 사이클에 활용할 수 있는 context를 생성합니다.
    
    Args:
        result: 실행 결과
        user_query: 사용자 쿼리 (선택적, 답변 추출에 사용)
        
    Returns:
        Context 딕셔너리:
        - insights: 발견된 인사이트 목록
        - patterns: 데이터 패턴 목록
        - statistics: 통계 정보 딕셔너리
        - answer: 사용자 질문에 대한 답변 (user_query가 있는 경우)
        - next_steps: 다음 분석 단계 제안
        - stdout_summary: stdout 요약 (핵심 정보만)
        - extracted_data: 추출된 데이터 값들 (숫자, 문자열 등)
        - errors: 에러 정보 (있는 경우)
    """
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    
    context = {
        "insights": [],
        "patterns": [],
        "statistics": {},
        "answer": None,
        "next_steps": [],
        "stdout_summary": "",
        "extracted_data": {},
        "errors": []
    }
    
    # stdout에서 의미있는 정보 추출
    if stdout:
        context.update(_extract_from_stdout(stdout, user_query))
    
    # stderr에서 에러 정보 추출
    if stderr:
        context["errors"] = _extract_errors(stderr)
    
    # 시각화가 있으면 인사이트로 추가
    if result.metadata.get("visualizations"):
        context["insights"].append("visualizations_created")
        context["visualizations"] = result.metadata["visualizations"]
    
    # 사용자 쿼리가 있으면 답변 추출 시도
    if user_query:
        context["answer"] = _extract_answer_from_stdout(stdout, user_query)
    
    return context


def _extract_from_stdout(stdout: str, user_query: Optional[str] = None) -> Dict[str, Any]:
    """stdout에서 의미있는 정보 추출"""
    extracted = {
        "insights": [],
        "patterns": [],
        "statistics": {},
        "extracted_data": {},
        "stdout_summary": ""
    }
    
    stdout_lower = stdout.lower()
    lines = stdout.split('\n')
    
    # 통계 정보 추출
    _extract_statistics(stdout, extracted)
    
    # 데이터 패턴 감지
    _extract_patterns(stdout_lower, extracted)
    
    # 숫자 데이터 추출
    _extract_numeric_data(stdout, extracted)
    
    # 핵심 라인 추출 (요약)
    extracted["stdout_summary"] = _create_stdout_summary(lines)
    
    return extracted


def _extract_statistics(stdout: str, extracted: Dict[str, Any]):
    """통계 정보 추출"""
    stats = extracted["statistics"]
    
    # 평균 관련
    mean_patterns = [
        r'평균[:\s]*([0-9.]+)',
        r'mean[:\s]*([0-9.]+)',
        r'avg[:\s]*([0-9.]+)',
        r'average[:\s]*([0-9.]+)'
    ]
    for pattern in mean_patterns:
        matches = re.findall(pattern, stdout, re.IGNORECASE)
        if matches:
            stats["mean"] = matches[0]
            extracted["insights"].append("mean_calculated")
            break
    
    # 합계 관련
    sum_patterns = [
        r'합계[:\s]*([0-9.]+)',
        r'sum[:\s]*([0-9.]+)',
        r'total[:\s]*([0-9.]+)'
    ]
    for pattern in sum_patterns:
        matches = re.findall(pattern, stdout, re.IGNORECASE)
        if matches:
            stats["sum"] = matches[0]
            extracted["insights"].append("sum_calculated")
            break
    
    # 개수 관련
    count_patterns = [
        r'개수[:\s]*([0-9]+)',
        r'count[:\s]*([0-9]+)',
        r'행[:\s]*([0-9]+)',
        r'rows[:\s]*([0-9]+)',
        r'데이터[:\s]*([0-9]+)'
    ]
    for pattern in count_patterns:
        matches = re.findall(pattern, stdout, re.IGNORECASE)
        if matches:
            stats["count"] = matches[0]
            extracted["insights"].append("count_calculated")
            break
    
    # 최대/최소값
    max_match = re.search(r'최대[:\s]*([0-9.]+)|max[:\s]*([0-9.]+)', stdout, re.IGNORECASE)
    if max_match:
        stats["max"] = max_match.group(1) or max_match.group(2)
        extracted["insights"].append("max_found")
    
    min_match = re.search(r'최소[:\s]*([0-9.]+)|min[:\s]*([0-9.]+)', stdout, re.IGNORECASE)
    if min_match:
        stats["min"] = min_match.group(1) or min_match.group(2)
        extracted["insights"].append("min_found")


def _extract_patterns(stdout_lower: str, extracted: Dict[str, Any]):
    """데이터 패턴 감지"""
    patterns = extracted["patterns"]
    
    # 상관관계
    if "correlation" in stdout_lower or "상관관계" in stdout_lower or "상관" in stdout_lower:
        patterns.append("correlation_detected")
        extracted["insights"].append("correlation_analysis_done")
    
    # 이상치
    if "outlier" in stdout_lower or "이상치" in stdout_lower:
        patterns.append("outliers_detected")
        extracted["insights"].append("outliers_found")
    
    # 결측값
    if "missing" in stdout_lower or "결측" in stdout_lower or "null" in stdout_lower or "nan" in stdout_lower:
        patterns.append("missing_values_detected")
        extracted["insights"].append("missing_values_found")
    
    # 중복값
    if "duplicate" in stdout_lower or "중복" in stdout_lower:
        patterns.append("duplicates_detected")
        extracted["insights"].append("duplicates_found")
    
    # 정규분포
    if "normal" in stdout_lower or "정규" in stdout_lower or "gaussian" in stdout_lower:
        patterns.append("normal_distribution")
        extracted["insights"].append("normal_distribution_detected")
    
    # 시각화 생성
    if "saved" in stdout_lower or "저장" in stdout_lower or "png" in stdout_lower or "jpg" in stdout_lower:
        patterns.append("visualization_created")
        extracted["insights"].append("visualization_saved")


def _extract_numeric_data(stdout: str, extracted: Dict[str, Any]):
    """숫자 데이터 추출"""
    # 숫자 패턴 추출 (예: "값: 123.45" 형태)
    numeric_patterns = [
        r'([a-zA-Z가-힣]+)[:\s]*([0-9.]+)',
        r'([0-9.]+)',
    ]
    
    extracted_data = extracted["extracted_data"]
    
    # 키-값 쌍 추출
    for line in stdout.split('\n'):
        # "키: 값" 형태
        match = re.search(r'([a-zA-Z가-힣_]+)[:\s]+([0-9.]+)', line, re.IGNORECASE)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            extracted_data[key] = value


def _create_stdout_summary(lines: List[str]) -> str:
    """stdout 요약 생성 (핵심 정보만)"""
    summary_lines = []
    
    # 빈 라인 제거 및 의미있는 라인만 추출
    meaningful_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 3]
    
    # 숫자가 포함된 라인 우선 추출
    numeric_lines = [line for line in meaningful_lines if re.search(r'[0-9]', line)]
    
    # 요약 생성 (최대 10줄)
    if numeric_lines:
        summary_lines.extend(numeric_lines[:5])
    
    # 나머지 의미있는 라인 추가
    remaining = [line for line in meaningful_lines if line not in numeric_lines]
    summary_lines.extend(remaining[:5])
    
    return '\n'.join(summary_lines[:10])


def _extract_errors(stderr: str) -> List[str]:
    """stderr에서 에러 정보 추출"""
    errors = []
    lines = stderr.split('\n')
    
    # 에러 라인 추출
    error_keywords = ['error', 'exception', 'traceback', '에러', '오류', '실패']
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in error_keywords):
            if line.strip():
                errors.append(line.strip())
    
    return errors[:5]  # 최대 5개 에러만 반환


def _extract_answer_from_stdout(stdout: str, query: str) -> Optional[str]:
    """stdout에서 사용자 쿼리에 대한 답변 추출"""
    query_lower = query.lower()
    lines = stdout.split('\n')
    
    # 쿼리 키워드와 관련된 라인 찾기
    query_keywords = []
    if '평균' in query_lower or 'mean' in query_lower:
        query_keywords.extend(['평균', 'mean', 'avg', 'average'])
    if '합계' in query_lower or 'sum' in query_lower:
        query_keywords.extend(['합계', 'sum', 'total'])
    if '개수' in query_lower or 'count' in query_lower:
        query_keywords.extend(['개수', 'count', '행', 'rows'])
    
    # 관련 라인 찾기
    for line in lines:
        if any(keyword.lower() in line.lower() for keyword in query_keywords):
            if any(char.isdigit() for char in line):
                return line.strip()
    
    # 숫자가 포함된 첫 번째 의미있는 라인 반환
    for line in lines:
        if line.strip() and len(line.strip()) > 5:
            if any(char.isdigit() for char in line):
                return line.strip()[:200]  # 최대 200자
    
    # 숫자가 없는 경우 첫 번째 의미있는 라인 반환
    for line in lines:
        if line.strip() and len(line.strip()) > 10:
            return line.strip()[:200]  # 최대 200자
    
    return None


def _extract_answer_simple(stdout: str, query: str) -> Optional[str]:
    """간단한 답변 추출 (LLM 사용 권장)
    
    실제 구현에서는 LLM을 사용하여 더 정확한 답변 추출을 권장합니다.
    """
    # 간단한 패턴 매칭
    lines = stdout.split('\n')
    
    # 숫자나 결과가 포함된 라인 찾기
    for line in lines:
        if any(keyword in query.lower() for keyword in ['평균', 'mean', '합계', 'sum', '개수', 'count']):
            if any(char.isdigit() for char in line):
                return line.strip()
    
    # 첫 번째 의미있는 라인 반환
    for line in lines:
        if line.strip() and len(line.strip()) > 10:
            return line.strip()[:200]  # 최대 200자
    
    return None
