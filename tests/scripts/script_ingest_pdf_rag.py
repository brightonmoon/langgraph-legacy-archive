"""
PDF 문서를 RAG 벡터스토어에 임베딩하는 스크립트.

사용법:
    uv run tests/scripts/script_ingest_pdf_rag.py \
        --pdf "data/MACHINE LEARNING FOR SMALL molecule lead optimization.pdf" \
        --vectorstore-id "ml_small_molecule" \
        --chunk-size 1000 \
        --chunk-overlap 200
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.agents.sub_agents.rag_agent.data_utils import load_pdf_as_documents
from src.agents.sub_agents.rag_agent.vectorstore import VectorStoreManager
from src.utils.paths import get_project_root

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="PDF 문서를 RAG 벡터스토어에 임베딩",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF 파일 경로 (data/ 디렉토리 기준 또는 절대 경로)",
    )
    parser.add_argument(
        "--vectorstore-id",
        type=str,
        default=None,
        help="벡터스토어 ID (기본값: PDF 파일명 기반 자동 생성)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="청크 크기 (기본값: 1000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="청크 간 겹침 크기 (기본값: 200)",
    )
    parser.add_argument(
        "--vectorstore-dir",
        type=str,
        default=None,
        help="벡터스토어 디렉토리 (기본값: .rag_vectorstores/)",
    )

    args = parser.parse_args()

    # PDF 파일 경로 확인
    pdf_path = Path(args.pdf)
    if not pdf_path.is_absolute():
        pdf_path = get_project_root() / pdf_path

    if not pdf_path.exists():
        print(f"❌ 오류: PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return 1

    print(f"📄 PDF 파일: {pdf_path}")
    print(f"   크기: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    # 벡터스토어 ID 생성
    if args.vectorstore_id:
        vectorstore_id = args.vectorstore_id
    else:
        # PDF 파일명 기반으로 자동 생성
        stem = pdf_path.stem.lower().replace(" ", "_")
        vectorstore_id = f"pdf_{stem}"

    print(f"🔍 벡터스토어 ID: {vectorstore_id}")
    print(f"📊 청크 크기: {args.chunk_size}, 겹침: {args.chunk_overlap}")

    # PDF 로드
    print("\n📖 PDF 문서 로드 중...")
    try:
        documents = load_pdf_as_documents(
            pdf_path,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"✅ {len(documents)}개의 문서 청크 생성됨")
    except Exception as e:
        print(f"❌ PDF 로드 실패: {e}")
        return 1

    # 벡터스토어 매니저 초기화
    manager = VectorStoreManager(vectorstore_dir=args.vectorstore_dir)

    # 임베딩 및 저장
    print(f"\n🔢 임베딩 생성 및 벡터스토어 저장 중...")
    print(f"   임베딩 모델: bge-m3:latest")
    print(f"   저장 위치: {manager.base_dir / vectorstore_id}")

    try:
        start_time = datetime.now(timezone.utc)
        vectorstore_id_result = manager.index_documents(
            documents,
            vectorstore_id=vectorstore_id,
        )
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        print(f"\n✅ 완료!")
        print(f"   벡터스토어 ID: {vectorstore_id_result}")
        print(f"   처리 시간: {duration:.2f}초")
        print(f"   저장 위치: {manager.base_dir / vectorstore_id_result}")

        # 저장된 파일 확인
        store_path = manager.base_dir / vectorstore_id_result
        if (store_path / "documents.json").exists():
            import json

            with open(store_path / "documents.json", "r", encoding="utf-8") as f:
                saved_docs = json.load(f)
            print(f"   저장된 문서 수: {len(saved_docs)}")

        if (store_path / "embeddings.npy").exists():
            import numpy as np

            embeddings = np.load(store_path / "embeddings.npy", allow_pickle=False)
            print(f"   임베딩 벡터 수: {embeddings.shape[0]}")
            print(f"   임베딩 차원: {embeddings.shape[1]}")

        return 0

    except Exception as e:
        print(f"❌ 임베딩 저장 실패: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())




