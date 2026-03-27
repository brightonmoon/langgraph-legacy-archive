"""
PDF를 Docling으로 Markdown으로 변환하는 스크립트

사용법:
    uv run python tests/scripts/convert_pdf_to_markdown.py <PDF파일경로> [--output <출력파일경로>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import ImageRefMode
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    print("⚠️  Docling이 설치되지 않았습니다. 다음 명령으로 설치하세요:")
    print("   uv pip install docling")
    sys.exit(1)


def convert_pdf_to_markdown(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    image_mode: str = "placeholder"
) -> Path:
    """
    PDF를 Docling으로 Markdown으로 변환
    
    Args:
        pdf_path: PDF 파일 경로
        output_path: 출력 Markdown 파일 경로 (None이면 자동 생성)
        image_mode: 이미지 처리 모드 ("placeholder", "referenced", "embedded")
    
    Returns:
        출력 파일 경로
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    # 출력 경로 결정
    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.md"
    else:
        output_path = Path(output_path)
    
    print(f"\n{'='*60}")
    print(f"📄 PDF → Markdown 변환")
    print(f"{'='*60}")
    print(f"입력 파일: {pdf_path}")
    print(f"출력 파일: {output_path}")
    print(f"이미지 모드: {image_mode}")
    print(f"{'='*60}\n")
    
    # 이미지 모드 설정
    image_ref_mode = ImageRefMode.PLACEHOLDER
    if image_mode == "referenced":
        image_ref_mode = ImageRefMode.REFERENCED
    elif image_mode == "embedded":
        image_ref_mode = ImageRefMode.EMBEDDED
    
    # DocumentConverter 생성
    print("🔄 DocumentConverter 초기화 중...")
    converter = DocumentConverter(
        format_options={
            "markdown": {
                "image_ref_mode": image_ref_mode,
            }
        }
    )
    
    # 문서 변환
    print(f"📖 문서 변환 중...")
    try:
        result = converter.convert(str(pdf_path))
        print("✅ 변환 완료!\n")
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        raise
    
    # Markdown으로 export
    print("📝 Markdown으로 변환 중...")
    markdown = result.document.export_to_markdown()
    
    # 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    
    # 문서 정보 출력
    print("\n📋 문서 정보:")
    try:
        items = list(result.document.iterate_items())
        item_count = len(items)
        print(f"  - 아이템 수: {item_count:,}")
        
        # 아이템 타입 통계
        item_types = {}
        for item_tuple in items:
            item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
            item_type = type(item).__name__
            item_types[item_type] = item_types.get(item_type, 0) + 1
        
        print("  - 아이템 타입:")
        for item_type, count in sorted(item_types.items()):
            print(f"    • {item_type}: {count:,}")
        
        # 추가 정보
        if hasattr(result.document, 'tables'):
            print(f"  - 테이블 수: {len(result.document.tables)}")
        if hasattr(result.document, 'pictures'):
            print(f"  - 이미지 수: {len(result.document.pictures)}")
        if hasattr(result.document, 'num_pages'):
            print(f"  - 페이지 수: {result.document.num_pages}")
    except Exception as e:
        print(f"  ⚠️  문서 정보 추출 중 오류: {e}")
    
    print(f"\n💾 결과 저장: {output_path}")
    print(f"📊 출력 크기: {len(markdown):,} 자 ({output_path.stat().st_size / 1024:.2f} KB)")
    print(f"{'='*60}\n")
    
    return output_path


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="PDF를 Docling으로 Markdown으로 변환",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 사용 (출력 파일 자동 생성)
  uv run python tests/scripts/convert_pdf_to_markdown.py document.pdf
  
  # 출력 파일 지정
  uv run python tests/scripts/convert_pdf_to_markdown.py document.pdf --output output.md
  
  # 이미지 모드 지정
  uv run python tests/scripts/convert_pdf_to_markdown.py document.pdf --image-mode referenced
        """
    )
    
    parser.add_argument(
        "pdf_path",
        type=str,
        help="변환할 PDF 파일 경로"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="출력 Markdown 파일 경로 (기본: PDF와 같은 디렉토리에 .md 확장자)"
    )
    parser.add_argument(
        "--image-mode",
        type=str,
        choices=["placeholder", "referenced", "embedded"],
        default="placeholder",
        help="이미지 처리 모드 (기본: placeholder)"
    )
    
    args = parser.parse_args()
    
    if not HAS_DOCLING:
        sys.exit(1)
    
    try:
        output_path = convert_pdf_to_markdown(
            args.pdf_path,
            args.output,
            args.image_mode
        )
        print(f"✅ 변환 완료: {output_path}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
