#!/usr/bin/env python3
"""
병렬 검색 에이전트 실행 스크립트

Tavily와 Brave Search를 병렬로 사용하여 검색 결과를 취합하고 보고서를 작성합니다.
"""

import sys
import os
import argparse

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agents.sub_agents.parallel_search_agent.agent import ParallelSearchAgent


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="병렬 검색 에이전트 실행 (Tavily + Brave Search)"
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
        help="실행할 검색 쿼리 (지정하지 않으면 대화형 모드)"
    )
    
    args = parser.parse_args()
    
    try:
        # 병렬 검색 에이전트 생성
        print("=" * 60)
        print("병렬 검색 에이전트 초기화 중...")
        print("=" * 60)
        
        agent = ParallelSearchAgent(model=args.model)
        
        # 정보 출력
        info = agent.get_info()
        print(f"\n📋 에이전트 정보:")
        print(f"   타입: {info['type']}")
        print(f"   라이브러리: {info['library']}")
        print(f"   기능: {', '.join(info['features'])}")
        print()
        
        # 쿼리 실행 또는 대화형 모드
        if args.query:
            print(f"🔍 검색 쿼리: {args.query}\n")
            agent.chat(args.query)
        else:
            agent.chat()
            
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



