#!/usr/bin/env python3
"""
DeepAgent 실행 스크립트

deepagents 라이브러리를 사용하는 Deep Agent를 실행합니다.
"""

import sys
import os
import argparse

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import DeepAgentLibrary
from tools import create_brave_search_tool


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="DeepAgents 라이브러리를 사용하는 Deep Agent 실행"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="사용할 모델명 (예: claude-sonnet-4-5-20250929, gpt-4o, ollama:gpt-oss:120b-cloud)"
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="실행할 쿼리 (지정하지 않으면 대화형 모드)"
    )
    parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="Ollama 모델 사용 안 함"
    )
    parser.add_argument(
        "--with-search",
        action="store_true",
        help="인터넷 검색 도구 포함"
    )
    
    args = parser.parse_args()
    
    try:
        # 도구 준비
        tools = []
        if args.with_search:
            search_tool = create_brave_search_tool()
            if search_tool:
                tools.append(search_tool)
                print("✅ Brave Search 도구가 추가되었습니다.")
        
        # DeepAgent 생성
        agent = DeepAgentLibrary(
            model=args.model,
            tools=tools if tools else None,
            use_ollama=not args.no_ollama
        )
        
        # 정보 출력
        info = agent.get_info()
        print(f"\n📋 에이전트 정보:")
        print(f"   타입: {info['type']}")
        print(f"   라이브러리: {info['library']}")
        print(f"   기능: {', '.join(info['features'])}")
        print()
        
        # 쿼리 실행 또는 대화형 모드
        if args.query:
            agent.chat(args.query)
        else:
            agent.chat()
            
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

