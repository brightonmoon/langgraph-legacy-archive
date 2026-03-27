"""
파라미터 추출 유틸리티

메시지에서 CSV 분석에 필요한 파라미터를 추출하는 함수들을 제공합니다.
"""

import re
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain.messages import HumanMessage, SystemMessage

from .file_path import normalize_csv_path


def extract_natural_language_query_from_messages(messages: List) -> str:
    """메시지에서 자연어 쿼리 추출
    
    Args:
        messages: 메시지 리스트
        
    Returns:
        추출된 자연어 쿼리 문자열
    """
    if not messages:
        return ""
    
    # 마지막 HumanMessage에서 내용 추출
    for message in reversed(messages):
        message_content = None
        
        # HumanMessage 객체인 경우
        if hasattr(message, 'content'):
            message_content = message.content if hasattr(message, 'content') else str(message)
        # 딕셔너리 형식인 경우 (LangGraph Studio에서 전달되는 형식)
        elif isinstance(message, dict):
            # role이 "user"이거나 type이 "human"인 경우
            if message.get("role") == "user" or message.get("type") == "human":
                message_content = message.get("content", "")
            # content만 있는 경우
            elif "content" in message:
                message_content = message.get("content", "")
        
        if message_content:
            return message_content
    
    return ""


def extract_parameters_rule_based(natural_language_query: str) -> Dict[str, Any]:
    """규칙 기반 파라미터 추출 (폴백용)
    
    여러 파일 경로를 추출할 수 있도록 개선됨
    
    Args:
        natural_language_query: 자연어 쿼리
        
    Returns:
        추출된 파라미터 딕셔너리 (단일 파일 또는 다중 파일)
    """
    # CSV 파일 경로 패턴 매칭 (모든 매칭 찾기)
    csv_patterns = [
        r'([\w/]+\.csv)',  # 파일명 패턴
        r'["\']([^"\']+\.csv)["\']',  # 따옴표로 감싼 파일명
        r'파일[:\s]+([^\s]+\.csv)',  # "파일: xxx.csv" 패턴
        r'CSV[:\s]+([^\s]+\.csv)',  # "CSV: xxx.csv" 패턴
    ]
    
    csv_filepaths = []
    for pattern in csv_patterns:
        matches = re.findall(pattern, natural_language_query, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ""
            if match and match not in csv_filepaths:
                csv_filepaths.append(match)
    
    # 파일 경로 정규화
    normalized_paths = []
    for csv_filepath in csv_filepaths:
        normalized = normalize_csv_path(csv_filepath)
        if normalized and normalized not in normalized_paths:
            normalized_paths.append(normalized)
    
    # 분석 요청은 원본 쿼리 사용 (파일명 제거)
    user_query = natural_language_query
    for csv_filepath in normalized_paths:
        filename = Path(csv_filepath).name
        user_query = re.sub(re.escape(filename), "", user_query, flags=re.IGNORECASE)
    user_query = re.sub(r'\s+', ' ', user_query).strip()
    
    # 단일 파일 또는 다중 파일 반환
    if len(normalized_paths) == 0:
        return {
            "CSV_file_path": "",
            "query": user_query if user_query else natural_language_query
        }
    elif len(normalized_paths) == 1:
        # 단일 파일 모드 (하위 호환성)
        return {
            "CSV_file_path": normalized_paths[0],
            "query": user_query if user_query else natural_language_query
        }
    else:
        # 다중 파일 모드
        return {
            "CSV_file_paths": normalized_paths,
            "query": user_query if user_query else natural_language_query
        }


def extract_csv_parameters_from_messages(
    messages: List,
    csv_file_path: Optional[str] = None,
    csv_file_paths: Optional[List[str]] = None,
    query: Optional[str] = None,
    model=None
) -> Dict[str, Any]:
    """메시지에서 CSV 분석 파라미터 추출 (내부 헬퍼 함수)
    
    여러 파일 경로를 추출할 수 있도록 개선됨
    
    Args:
        messages: 메시지 리스트
        csv_file_path: 이미 제공된 CSV 파일 경로 (단일 파일 모드)
        csv_file_paths: 이미 제공된 CSV 파일 경로 목록 (다중 파일 모드)
        query: 이미 제공된 사용자 쿼리 (있으면 사용)
        model: LLM 모델 (파라미터 추출에 사용, 없으면 규칙 기반만 사용)
        
    Returns:
        추출된 파라미터 딕셔너리: 단일 파일 또는 다중 파일 모드
    """
    # 이미 파라미터가 모두 제공된 경우 그대로 반환
    if csv_file_paths and len(csv_file_paths) > 0:
        return {
            "CSV_file_paths": csv_file_paths,
            "query": query or ""
        }
    elif csv_file_path and query:
        return {
            "CSV_file_path": csv_file_path,
            "query": query
        }
    
    # 메시지에서 자연어 쿼리 추출
    natural_language_query = extract_natural_language_query_from_messages(messages)
    
    # 자연어 쿼리가 없으면 에러
    if not natural_language_query:
        return {
            "CSV_file_path": csv_file_path or "",
            "query": query or ""
        }
    
    # LLM 기반 추출 시도 (모델이 제공된 경우)
    if model:
        try:
            system_prompt = """당신은 자연어 쿼리를 분석하여 CSV 데이터 분석에 필요한 파라미터를 추출하는 전문가입니다.

**추출해야 할 정보:**
1. CSV 파일 경로: 쿼리에서 명시적으로 언급된 파일 경로 또는 파일명
   - 단일 파일: "CSV_file_path": "파일 경로"
   - 여러 파일: "CSV_file_paths": ["파일1.csv", "파일2.csv", ...]
   - 예: "DESeq2_counts.csv", "data/sales.csv", "/path/to/data.csv"
   - 파일명만 언급된 경우: 데이터 디렉토리(data/)에서 찾기
   - 여러 파일이 언급된 경우 모두 추출하세요

2. 분석 요청: 사용자가 원하는 분석 내용
   - 통계 분석, 시각화, 필터링, 그룹별 비교 등
   - 여러 파일 간 연계 분석, 병합, 비교 등

**응답 형식 (JSON):**
단일 파일인 경우:
{
    "CSV_file_path": "파일 경로 또는 파일명",
    "query": "분석 요청 내용"
}

여러 파일인 경우:
{
    "CSV_file_paths": ["파일1.csv", "파일2.csv", ...],
    "query": "분석 요청 내용"
}

**중요:**
- CSV 파일은 데이터 디렉토리(data/)에 있다고 가정
- 파일명만 언급된 경우 데이터 디렉토리(data/) 기준으로 해석
- 여러 파일이 언급되면 모두 추출하여 CSV_file_paths 배열에 포함
- 분석 요청은 사용자의 원래 의도를 최대한 보존"""
            
            user_prompt = f"""다음 자연어 쿼리를 분석하여 CSV 데이터 분석에 필요한 파라미터를 추출하세요:

자연어 쿼리:
{natural_language_query}

JSON 형식으로 응답하세요."""
            
            response = model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # JSON 추출 및 파싱
            extracted_data = None
            
            # 방법 1: 코드 블록 내 JSON 찾기
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                try:
                    extracted_data = json.loads(json_block_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # 방법 2: 중괄호로 감싼 JSON 찾기
            if not extracted_data:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
            
            # 방법 3: 전체 응답을 JSON으로 시도
            if not extracted_data:
                try:
                    extracted_data = json.loads(response_text.strip())
                except json.JSONDecodeError:
                    pass
            
            if extracted_data:
                extracted_query = extracted_data.get("query") or extracted_data.get("user_query", natural_language_query)
                
                # 여러 파일 경로 추출 시도
                extracted_csv_filepaths = extracted_data.get("CSV_file_paths", [])
                if not extracted_csv_filepaths:
                    # 단일 파일 경로 추출 시도
                    extracted_csv_filepath = extracted_data.get("CSV_file_path") or extracted_data.get("csv_filepath", "")
                    if extracted_csv_filepath:
                        extracted_csv_filepaths = [extracted_csv_filepath]
                
                # 파일 경로 정규화
                normalized_paths = []
                for filepath in extracted_csv_filepaths:
                    normalized = normalize_csv_path(filepath)
                    if normalized and normalized not in normalized_paths:
                        normalized_paths.append(normalized)
                
                # 단일 파일 또는 다중 파일 반환
                if len(normalized_paths) == 0:
                    return {
                        "CSV_file_path": csv_file_path or "",
                        "query": extracted_query or query or natural_language_query
                    }
                elif len(normalized_paths) == 1:
                    # 단일 파일 모드 (하위 호환성)
                    return {
                        "CSV_file_path": normalized_paths[0],
                        "query": extracted_query or query or natural_language_query
                    }
                else:
                    # 다중 파일 모드
                    return {
                        "CSV_file_paths": normalized_paths,
                        "query": extracted_query or query or natural_language_query
                    }
        except Exception as e:
            print(f"⚠️ LLM 기반 파라미터 추출 실패: {str(e)}, 규칙 기반으로 폴백")
    
    # 규칙 기반 추출 (폴백)
    rule_based_result = extract_parameters_rule_based(natural_language_query)
    
    # 규칙 기반 결과 반환 (이미 단일/다중 파일 모드로 반환됨)
    if "CSV_file_paths" in rule_based_result:
        return {
            "CSV_file_paths": rule_based_result.get("CSV_file_paths", []),
            "query": rule_based_result.get("query") or query or natural_language_query
        }
    else:
        return {
            "CSV_file_path": rule_based_result.get("CSV_file_path") or csv_file_path or "",
            "query": rule_based_result.get("query") or query or natural_language_query
        }

