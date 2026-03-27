"""
Task Tool - 서브에이전트 생성을 위한 도구
"""

import os
from typing import Optional
from langchain.tools import tool
from src.utils.config import setup_langsmith_disabled, init_chat_model_helper
from langchain.messages import HumanMessage, SystemMessage


@tool("task")
def task_tool(description: str, context: Optional[str] = None) -> str:
    """서브에이전트를 생성하여 특정 작업을 수행합니다.
    
    이 도구는 메인 에이전트의 컨텍스트를 깨끗하게 유지하면서,
    전문화된 서브에이전트를 생성하여 특정 서브태스크를 수행합니다.
    
    Args:
        description: 수행할 작업 설명
        context: 작업에 필요한 컨텍스트 정보 (선택사항)
        
    Returns:
        서브에이전트 실행 결과
    """
    try:
        # 서브에이전트를 위한 간단한 모델 생성
        setup_langsmith_disabled()
        model = init_chat_model_helper(
            model_name="ollama:gpt-oss:120b-cloud",
            api_key=os.getenv("OLLAMA_API_KEY"),
            temperature=0.7
        )
        
        if not model:
            return "❌ 서브에이전트 모델 초기화 실패"
        
        # 서브에이전트 시스템 메시지
        system_message = SystemMessage(
            content="""당신은 특정 작업을 수행하는 전문화된 서브에이전트입니다.
사용자의 요청을 정확하고 간결하게 처리하세요.
작업이 완료되면 결과만 반환하세요."""
        )
        
        # 작업 설명과 컨텍스트를 포함한 사용자 메시지
        user_content = description
        if context:
            user_content = f"컨텍스트: {context}\n\n작업: {description}"
        
        user_message = HumanMessage(content=user_content)
        
        # 서브에이전트 실행
        response = model.invoke([system_message, user_message])
        
        # 응답 처리
        if hasattr(response, 'content'):
            result = response.content
        else:
            result = str(response)
        
        return f"✅ 서브에이전트 작업 완료\n\n{result}"
        
    except Exception as e:
        return f"❌ 서브에이전트 실행 중 오류 발생: {str(e)}"






