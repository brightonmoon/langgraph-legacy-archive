"""
LangGraph를 통해 PDF RAG 에이전트를 테스트하는 스크립트.

사용법:
    # 환경 변수로 벡터스토어 ID 설정
    export RAG_AGENT_DEFAULT_VECTORSTORE_ID=ml_small_molecule
    uv run tests/scripts/test_pdf_rag_langgraph.py

    # 또는 state에 직접 전달
    uv run tests/scripts/test_pdf_rag_langgraph.py --vectorstore-id ml_small_molecule
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.agents.sub_agents.rag_agent.agent import create_rag_agent_graph

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="LangGraph를 통해 PDF RAG 에이전트 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--vectorstore-id",
        type=str,
        default=None,
        help="벡터스토어 ID (기본값: 환경 변수 RAG_AGENT_DEFAULT_VECTORSTORE_ID 또는 ml_small_molecule)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is machine learning for small molecule lead optimization?",
        help="테스트할 질문",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="대화형 모드 (여러 질문 가능)",
    )

    args = parser.parse_args()

    # 벡터스토어 ID 결정
    vectorstore_id = (
        args.vectorstore_id
        or os.getenv("RAG_AGENT_DEFAULT_VECTORSTORE_ID")
        or "ml_small_molecule"
    )

    print("🚀 LangGraph PDF RAG 에이전트 테스트\n")
    print(f"📚 벡터스토어 ID: {vectorstore_id}")
    print(f"💬 질문: {args.query}\n")

    # RAG 에이전트 그래프 생성
    try:
        graph = create_rag_agent_graph()
        print("✅ RAG 에이전트 그래프 생성 완료\n")
    except Exception as e:
        print(f"❌ 그래프 생성 실패: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # 초기 상태 설정
    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": args.query,
            }
        ],
        "vectorstore_id": vectorstore_id,
    }

    # 그래프 실행
    try:
        print("🔍 검색 및 답변 생성 중...\n")
        result = graph.invoke(initial_state)

        # 결과 출력
        print("=" * 80)
        print("📋 검색 결과")
        print("=" * 80)

        retrieved_docs = result.get("retrieved_documents", [])
        if retrieved_docs:
            print(f"\n✅ {len(retrieved_docs)}개의 관련 문서를 찾았습니다:\n")
            for i, doc in enumerate(retrieved_docs[:5], 1):  # 상위 5개만 표시
                content = doc.get("content", "") or doc.get("page_content", "")
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "Unknown")
                page = metadata.get("page", "N/A")

                preview = content[:150] + "..." if len(content) > 150 else content
                print(f"[{i}] {source} (페이지: {page})")
                print(f"    {preview}\n")
        else:
            print("\n⚠️  검색된 문서가 없습니다.")
            print(f"   벡터스토어가 존재하는지 확인하세요: .rag_vectorstores/{vectorstore_id}")

        print("=" * 80)
        print("💡 최종 답변")
        print("=" * 80)
        final_answer = result.get("final_answer", "")
        if final_answer:
            print(f"\n{final_answer}\n")
        else:
            print("\n⚠️  답변이 생성되지 않았습니다.")

        # 메타데이터 출력
        metadata = result.get("metadata", {})
        if metadata:
            print("=" * 80)
            print("📊 메타데이터")
            print("=" * 80)
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            print()

        # 대화형 모드
        if args.interactive:
            print("\n" + "=" * 80)
            print("💬 대화형 모드 (종료하려면 'quit' 또는 'exit' 입력)")
            print("=" * 80 + "\n")

            thread_state = {"messages": result.get("messages", [])}

            while True:
                try:
                    user_input = input("질문: ").strip()
                    if not user_input or user_input.lower() in ["quit", "exit", "q"]:
                        print("\n👋 종료합니다.")
                        break

                    # 새로운 질문으로 상태 업데이트
                    thread_state["messages"].append(
                        {
                            "role": "user",
                            "content": user_input,
                        }
                    )

                    # 그래프 실행
                    result = graph.invoke(thread_state)

                    # 답변 출력
                    answer = result.get("final_answer", "")
                    if answer:
                        print(f"\n답변: {answer}\n")
                    else:
                        print("\n⚠️  답변이 생성되지 않았습니다.\n")

                    # 상태 업데이트
                    thread_state["messages"] = result.get("messages", [])

                except KeyboardInterrupt:
                    print("\n\n👋 종료합니다.")
                    break
                except Exception as e:
                    print(f"\n❌ 오류 발생: {e}\n")

        return 0

    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())




