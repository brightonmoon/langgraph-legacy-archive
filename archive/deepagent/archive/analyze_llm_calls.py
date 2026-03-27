#!/usr/bin/env python3
"""
LLM 호출 횟수 분석 스크립트

JSON 파일에서 실제 LLM 호출 횟수를 분석합니다.
"""

import json
import sys


def analyze_llm_calls(json_file):
    """JSON 파일에서 LLM 호출 횟수 분석"""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 60)
    print("LLM 호출 횟수 분석")
    print("=" * 60)
    
    # 현재 카운트
    current_count = data.get("llm_calls", 0)
    print(f"\n📊 현재 카운트 (`llm_calls`): {current_count}회")
    
    # 분석
    orchestrator_calls = 2  # analyze_task + synthesize_results
    
    print(f"\n1. Orchestrator 호출 (gpt-oss:120b-cloud):")
    print(f"   - analyze_task: 1회")
    print(f"   - synthesize_results: 1회")
    print(f"   총: {orchestrator_calls}회 ✅")
    
    # Worker 분석
    worker_results = data.get("worker_results", {})
    print(f"\n2. Worker 호출 분석 (로컬 LLM: qwen2.5-coder:latest):")
    
    total_worker_calls_estimated = 0
    
    for worker_name, worker_result in worker_results.items():
        result_str = worker_result.get("result", "")
        
        # Tool 사용 여부 확인
        has_write_todos = "write_todos" in result_str
        has_write_file = "write_file" in result_str
        has_task = "task" in result_str and "subagent_type" in result_str
        
        # 복잡도에 따른 추정
        if has_task:
            estimated = 3  # 서브에이전트 생성은 더 복잡
        elif has_write_file:
            estimated = 2  # 파일 쓰기
        elif has_write_todos:
            estimated = 2  # Todo 작성
        else:
            estimated = 1  # 기본
        
        total_worker_calls_estimated += estimated
        
        tool_used = []
        if has_write_todos:
            tool_used.append("write_todos")
        if has_write_file:
            tool_used.append("write_file")
        if has_task:
            tool_used.append("task")
        
        print(f"   {worker_name}: 예상 {estimated}회 (도구: {', '.join(tool_used) if tool_used else '없음'})")
    
    print(f"\n   Worker 총 예상 호출: {total_worker_calls_estimated}회")
    
    # 전체 요약
    print(f"\n3. 전체 요약:")
    print(f"   Orchestrator (Cloud): {orchestrator_calls}회")
    print(f"   Worker (로컬 LLM):    {total_worker_calls_estimated}회")
    print(f"   ────────────────────────────────")
    print(f"   총 예상 호출:         {orchestrator_calls + total_worker_calls_estimated}회")
    print(f"\n   현재 카운트 ({current_count}회)는 실제보다 약 {int((orchestrator_calls + total_worker_calls_estimated) / current_count * 10) / 10}배 적습니다.")
    
    # 각 Worker의 상세 분석
    print(f"\n4. Worker별 상세 분석:")
    for worker_name, worker_result in worker_results.items():
        subtask = worker_result.get("subtask", {})
        result_str = worker_result.get("result", "")
        
        print(f"\n   {worker_name}: {subtask.get('task', '알 수 없음')}")
        print(f"      결과 타입: ", end="")
        
        if "write_todos" in result_str:
            print("write_todos (작업 분해)")
            print(f"      예상 LLM 호출: 2-3회")
            print(f"      - 호출 1: tool call 결정")
            print(f"      - 호출 2: tool 결과 처리 후 최종 응답")
        elif "write_file" in result_str:
            print("write_file (파일 저장)")
            print(f"      예상 LLM 호출: 2-3회")
            print(f"      - 호출 1: tool call 결정")
            print(f"      - 호출 2: tool 결과 처리 후 최종 응답")
        elif "task" in result_str and "subagent_type" in result_str:
            print("task (서브에이전트 생성)")
            print(f"      예상 LLM 호출: 3-5회")
            print(f"      - 호출 1: 서브에이전트 생성 결정")
            print(f"      - 호출 2-4: 서브에이전트 내부 처리")
            print(f"      - 호출 5: 최종 결과 통합")
        else:
            print("기본 응답")
            print(f"      예상 LLM 호출: 1회")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python analyze_llm_calls.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    analyze_llm_calls(json_file)







