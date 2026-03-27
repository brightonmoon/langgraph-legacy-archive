"""
보고서 생성 프롬프트 템플릿

사전 정의된 prompt 템플릿을 사용하여 일관된 보고서를 생성합니다.
"""

import json
from typing import Dict, Any, Optional


# 기본 보고서 생성 시스템 프롬프트
DEFAULT_REPORT_GENERATION_SYSTEM_PROMPT = """당신은 전문적인 보고서 작성 전문가입니다.

**당신의 역할:**
제공된 context 정보를 바탕으로 명확하고 구조화된 보고서를 작성합니다.

**보고서 작성 원칙:**
1. 제공된 context를 정확하게 반영하세요
2. 불필요한 추측이나 추가 정보를 포함하지 마세요
3. 명확하고 간결한 문장을 사용하세요
4. 구조화된 형식으로 작성하세요
5. 모든 내용은 한글로 작성하세요

**보고서 기본 구조:**
- 요약 (Executive Summary)
- 주요 내용 (Main Content)
- 결론 (Conclusion)

**중요:**
- context에 없는 정보는 포함하지 마세요
- 보고서 작성에만 집중하세요
- 다른 작업(분석, 코드 실행 등)은 수행하지 마세요"""


def create_report_generation_user_prompt(
    context: Dict[str, Any],
    report_template: Optional[str] = None,
    additional_instructions: Optional[str] = None
) -> str:
    """보고서 생성용 사용자 프롬프트 생성
    
    Args:
        context: 보고서 생성에 사용할 컨텍스트 정보 (다른 에이전트/도구가 생성)
        report_template: 사용할 보고서 템플릿 (선택적)
        additional_instructions: 추가 지시사항 (선택적)
    
    Returns:
        사용자 프롬프트 문자열
    """
    prompt_parts = []
    
    # Context 정보 추가
    prompt_parts.append("=" * 60)
    prompt_parts.append("보고서 생성 컨텍스트")
    prompt_parts.append("=" * 60)
    
    # Context를 구조화된 형식으로 변환
    if isinstance(context, dict):
        for key, value in context.items():
            prompt_parts.append(f"\n[{key}]")
            if isinstance(value, (dict, list)):
                prompt_parts.append(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                prompt_parts.append(str(value))
    else:
        prompt_parts.append(str(context))
    
    prompt_parts.append("\n" + "=" * 60)
    
    # 보고서 템플릿 추가 (있는 경우)
    if report_template:
        prompt_parts.append("\n[보고서 템플릿]")
        prompt_parts.append(report_template)
        prompt_parts.append("\n위 템플릿을 참고하여 보고서를 작성하세요.")
    
    # 추가 지시사항 추가 (있는 경우)
    if additional_instructions:
        prompt_parts.append("\n[추가 지시사항]")
        prompt_parts.append(additional_instructions)
    
    # 최종 지시
    prompt_parts.append("\n위 컨텍스트 정보를 바탕으로 전문적인 보고서를 작성하세요.")
    
    return "\n".join(prompt_parts)

