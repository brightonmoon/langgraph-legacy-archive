"""
Planning Tool - 작업 분해 및 계획 수립 도구
"""

import json
from typing import List
from langchain.tools import tool


@tool("write_todos")
def write_todos_tool(task: str, subtasks: List[str] = None) -> str:
    """복잡한 작업을 하위 작업으로 분해하고 관리합니다.
    
    이 도구는 복잡한 멀티 스텝 작업을 이산적인 단계로 분해하여,
    진행 상황을 추적하고 동적으로 계획을 조정할 수 있게 합니다.
    
    Args:
        task: 메인 작업 설명
        subtasks: 하위 작업 리스트 (선택사항)
        
    Returns:
        JSON 형식의 Todo 리스트 (task와 todos 필드 포함)
        
    Example:
        write_todos("웹 애플리케이션 개발", ["데이터베이스 설계", "API 개발", "프론트엔드 구현"])
    """
    try:
        # subtasks가 제공되지 않으면 빈 리스트로 초기화
        if subtasks is None:
            subtasks = []
        
        # 각 하위 작업을 Todo 아이템으로 변환
        todos = []
        for i, subtask in enumerate(subtasks):
            todos.append({
                "id": i + 1,
                "task": subtask,
                "status": "pending",
                "completed": False
            })
        
        # 메인 작업과 Todo 리스트를 포함한 결과 반환
        result = {
            "task": task,
            "todos": todos,
            "total_tasks": len(todos),
            "completed_tasks": 0
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Todo 생성 중 오류 발생: {str(e)}",
            "task": task,
            "todos": []
        }, ensure_ascii=False)
















