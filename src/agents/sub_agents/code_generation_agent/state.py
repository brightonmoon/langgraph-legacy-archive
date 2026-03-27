"""
Code Generation Agent - State 정의

코딩 에이전트의 상태를 정의합니다.
MessagesState를 상속하여 LangGraph Studio에서 메시지 타입 선택 UI를 제공합니다.
"""

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import MessagesState


class CodeGenerationState(MessagesState, total=False):
    """코딩 에이전트 상태
    
    MessagesState를 상속하여 LangGraph Studio에서 메시지 타입(HUMAN, AI, SYSTEM, Tool, Function) 선택 UI 제공
    messages는 Required, 나머지 필드는 Optional
    
    필드 분류:
    - 입력: task_description, requirements, context (도메인별 컨텍스트)
    - 코드 생성: generated_code, generated_code_file
    - 코드 검증: code_valid, validation_errors
    - 코드 실행: execution_result, execution_errors
    - 코드 수정: fixed_code, fix_iterations
    - 제어: status, max_iterations
    """
    
    # ========== 입력 (사용자 또는 다른 에이전트로부터) ==========
    task_description: Optional[str]  # 작업 설명
    requirements: Optional[str]  # 요구사항
    context: Optional[Dict[str, Any]]  # 컨텍스트 (도메인별: csv_analysis, web_development, api_development 등)
    
    # ========== Planning (작업 계획 수립) ==========
    planning_result: Optional[str]  # Planning Tool 결과 (JSON 형식)
    planning_todos: Optional[List[Dict[str, Any]]]  # Todo 리스트
    current_subtask: Optional[int]  # 현재 진행 중인 하위 작업 인덱스
    
    # ========== 코드 생성 ==========
    generated_code: Optional[str]  # 생성된 코드
    generated_code_file: Optional[str]  # 코드 파일 경로
    target_filepath: Optional[str]  # 목표 파일 경로 (Planning 기반)
    
    # ========== Filesystem (파일 관리) ==========
    files_created: Optional[List[str]]  # 생성된 파일 목록
    files_edited: Optional[List[str]]  # 편집된 파일 목록
    files_read: Optional[List[str]]  # 읽은 파일 목록
    
    # ========== 코드 검증 ==========
    code_valid: Optional[bool]  # 코드 유효성
    validation_errors: Optional[List[str]]  # 검증 오류 목록
    code_syntax_valid: Optional[bool]  # 코드 문법 검증 결과
    syntax_errors: Optional[List[str]]  # 문법 오류 목록
    auto_fixed: Optional[bool]  # 프로그램으로 자동 수정 성공 여부
    
    # ========== 코드 실행 ==========
    execution_result: Optional[str]  # 실행 결과
    execution_errors: Optional[List[str]]  # 실행 오류 목록
    execution_context: Optional[Dict[str, Any]]  # 실행 결과에서 추출된 context
    
    # ========== 코드 수정 ==========
    fixed_code: Optional[str]  # 수정된 코드
    fix_iterations: Optional[int]  # 수정 반복 횟수
    previous_fix_errors: Optional[List[str]]  # 이전 수정 시 발견된 오류 목록 (다음 수정 시 참조)
    
    # ========== 제어 및 상태 추적 ==========
    status: Optional[str]  # 현재 상태 (planning, analyzing, generating, tool_executing, validating, executing, fixing, done, error)
    max_iterations: Optional[int]  # 최대 반복 횟수 (기본값: 3)
    call_count: Optional[int]  # LLM 호출 횟수 (통계/디버깅용)
    tool_call_count: Optional[int]  # Tool 호출 횟수 (통계/디버깅용)
    errors: Optional[List[str]]  # 에러 목록 (에러 처리용)

