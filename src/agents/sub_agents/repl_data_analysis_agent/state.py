"""
REPL Data Analysis Agent - State 정의

REPL 기반 하이브리드 스키마 데이터 분석 에이전트의 상태를 정의합니다.
MessagesState를 상속하여 LangGraph Studio에서 메시지 타입 선택 UI를 제공합니다.
"""

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import MessagesState


class DataAnalysisREPLState(MessagesState, total=False):
    """REPL 기반 데이터 분석 에이전트 상태
    
    MessagesState를 상속하여 LangGraph Studio에서 메시지 타입(HUMAN, AI, SYSTEM, Tool, Function) 선택 UI 제공
    messages는 Required, 나머지 필드는 Optional
    
    필드 분류:
    - 사용자 입력: query, data_file_paths
    - 코드 생성 및 실행: generated_code, execution_result, execution_error
    - REPL 세션 관리: repl_session_id, accumulated_output, session_variables
    - 반복 제어: iteration_count, max_iterations, should_retry, retry_reason
    - 결과 검증: result_valid, insights
    - 최종 결과: final_result, status
    """
    
    # ========== 사용자 입력 ==========
    query: Optional[str]  # 사용자 쿼리
    data_file_paths: Optional[List[str]]  # 데이터 파일 경로 (CSV, Excel 등)
    
    # ========== 데이터 메타데이터 ==========
    data_metadata: Optional[str]  # 데이터 파일 메타데이터
    
    # ========== 코드 생성 및 실행 ==========
    generated_code: Optional[str]  # 생성된 Python 코드
    execution_result: Optional[str]  # REPL 실행 결과
    execution_error: Optional[str]  # 실행 오류 (있는 경우)
    
    # ========== REPL 세션 관리 ==========
    repl_session_id: Optional[str]  # 세션 ID (상태 유지용)
    accumulated_output: Optional[str]  # 누적된 출력 (커널 상태 유지)
    session_variables: Optional[Dict[str, Any]]  # 세션 변수 (상태 유지)
    
    # ========== 반복 제어 ==========
    iteration_count: int  # 반복 횟수 (기본값: 0)
    max_iterations: int  # 최대 반복 횟수 (기본값: 5)
    should_retry: bool  # 재시도 필요 여부
    retry_reason: Optional[str]  # 재시도 이유
    
    # ========== 결과 검증 ==========
    result_valid: Optional[bool]  # 결과 유효성 검증 결과
    insights: Optional[List[str]]  # 발견된 인사이트 목록
    
    # ========== 최종 결과 ==========
    final_result: Optional[str]  # 최종 결과
    status: Optional[str]  # 현재 상태






