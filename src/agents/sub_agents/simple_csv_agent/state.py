"""
Simple CSV Agent State 정의
"""

from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState


class SimpleCSVState(MessagesState, total=False):
    """Simple CSV Analysis Agent의 상태
    
    MessagesState를 상속하여 메시지 히스토리 관리
    """
    # CSV 파일 경로
    csv_file_path: Optional[str]
    
    # CSV 메타데이터
    csv_metadata: Optional[str]
    
    # 생성된 코드
    generated_code: Optional[str]
    
    # 실행 결과
    execution_result: Optional[str]
    execution_error: Optional[str]
    
    # 최종 결과
    final_result: Optional[str]
    
    # 상태
    status: Optional[str]  # "reading", "planning", "generating", "executing", "analyzing", "summarizing", "completed", "error"
    
    # 반복 횟수 (에러 발생 시 재시도)
    iteration_count: int
    
    # 최대 반복 횟수
    max_iterations: int
    
    # Planning 관련 필드
    planning_result: Optional[str]  # Planning Tool 결과 (JSON 형식)
    planning_todos: Optional[List[Dict[str, Any]]]  # Todo 리스트
    current_subtask: Optional[int]  # 현재 진행 중인 하위 작업 인덱스
    subtask_results: Optional[List[Dict[str, Any]]]  # 각 하위 작업의 결과 저장
    subtask_codes: Optional[List[str]]  # 각 하위 작업의 생성된 코드 저장 (연속성 유지용)

