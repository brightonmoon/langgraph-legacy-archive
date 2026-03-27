"""
Docling 고급 기능 예제

Docling의 고급 기능들을 보여줍니다:
- 테이블 구조 추출
- 이미지 및 수식 처리
- 배치 처리
- LangChain 통합
- 다양한 문서 형식 처리

사용법:
    uv run python tests/test_docling_advanced.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    print("⚠️  Docling이 설치되지 않았습니다. 다음 명령으로 설치하세요:")
    print("   uv pip install docling")
    sys.exit(1)

try:
    from langchain_core.documents import Document
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

from src.utils.paths import get_project_root


def extract_tables(result) -> List[Dict]:
    """문서에서 테이블 추출"""
    tables = []
    # tables 속성 직접 사용
    if hasattr(result.document, 'tables'):
        for table in result.document.tables:
            table_info = {
                "type": "table",
                "rows": len(table.rows) if hasattr(table, 'rows') else 0,
                "columns": len(table.columns) if hasattr(table, 'columns') else 0,
            }
            tables.append(table_info)
    return tables


def extract_images(result) -> List[Dict]:
    """문서에서 이미지 정보 추출"""
    images = []
    # pictures 속성 직접 사용
    if hasattr(result.document, 'pictures'):
        for picture in result.document.pictures:
            image_info = {
                "type": "image",
                "has_image": True,
            }
            if hasattr(picture, 'image') and picture.image:
                if hasattr(picture.image, 'width'):
                    image_info["width"] = picture.image.width
                if hasattr(picture.image, 'height'):
                    image_info["height"] = picture.image.height
            images.append(image_info)
    return images


def extract_formulas(result) -> List[Dict]:
    """문서에서 수식 정보 추출"""
    formulas = []
    # iterate_items()를 사용하여 수식 찾기
    try:
        for item_tuple in result.document.iterate_items():
            item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
            if hasattr(item, 'formula') or type(item).__name__ == 'FormulaItem':
                formula_info = {
                    "type": "formula",
                    "has_formula": True,
                }
                formulas.append(formula_info)
    except Exception:
        pass
    return formulas


def analyze_document_structure(source: str) -> Dict:
    """문서 구조 분석"""
    print(f"\n📊 문서 구조 분석: {source}")
    print("-" * 60)
    
    # DocumentConverter는 기본 생성자만 사용 (파라미터 없음)
    converter = DocumentConverter()
    
    try:
        result = converter.convert(source)
        
        # 아이템 타입 통계
        item_types = {}
        for item_tuple in result.document.iterate_items():
            # iterate_items()는 (item, depth) 튜플을 반환
            item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
            item_type = type(item).__name__
            item_types[item_type] = item_types.get(item_type, 0) + 1
        
        # 테이블, 이미지, 수식 추출
        tables = extract_tables(result)
        images = extract_images(result)
        formulas = extract_formulas(result)
        
        # 총 아이템 수 계산
        total_items = len(list(result.document.iterate_items()))
        
        analysis = {
            "source": source,
            "total_items": total_items,
            "item_types": item_types,
            "tables": {
                "count": len(tables),
                "details": tables
            },
            "images": {
                "count": len(images),
                "details": images
            },
            "formulas": {
                "count": len(formulas),
                "details": formulas
            }
        }
        
        # 결과 출력
        print(f"✅ 분석 완료!")
        print(f"  총 아이템 수: {analysis['total_items']}")
        print(f"  테이블 수: {analysis['tables']['count']}")
        print(f"  이미지 수: {analysis['images']['count']}")
        print(f"  수식 수: {analysis['formulas']['count']}")
        print(f"\n  아이템 타입 분포:")
        for item_type, count in sorted(item_types.items()):
            print(f"    • {item_type}: {count}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return {}


def batch_process_documents(
    input_dir: Path,
    output_dir: Path,
    file_pattern: str = "*.pdf"
) -> None:
    """여러 문서를 배치로 처리"""
    print(f"\n📦 배치 처리 시작")
    print(f"  입력 디렉토리: {input_dir}")
    print(f"  출력 디렉토리: {output_dir}")
    print(f"  파일 패턴: {file_pattern}")
    print("-" * 60)
    
    if not input_dir.exists():
        print(f"❌ 입력 디렉토리가 존재하지 않습니다: {input_dir}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 찾기
    files = list(input_dir.glob(file_pattern))
    if not files:
        print(f"⚠️  {file_pattern} 패턴에 맞는 파일을 찾을 수 없습니다.")
        return
    
    print(f"📁 발견된 파일 수: {len(files)}\n")
    
    converter = DocumentConverter()
    success_count = 0
    error_count = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] 처리 중: {file_path.name}")
        
        try:
            result = converter.convert(str(file_path))
            
            # Markdown으로 저장
            output_file = output_dir / f"{file_path.stem}.md"
            markdown = result.document.export_to_markdown()
            output_file.write_text(markdown, encoding="utf-8")
            
            print(f"  ✅ 완료: {output_file}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            error_count += 1
    
    print(f"\n📊 배치 처리 완료:")
    print(f"  성공: {success_count}")
    print(f"  실패: {error_count}")


def langchain_integration_example(source: str) -> None:
    """LangChain 통합 예제"""
    if not HAS_LANGCHAIN:
        print("⚠️  LangChain이 설치되지 않았습니다.")
        print("   uv pip install langchain langchain-core")
        return
    
    print(f"\n🔗 LangChain 통합 예제")
    print(f"  소스: {source}")
    print("-" * 60)
    
    converter = DocumentConverter()
    
    try:
        result = converter.convert(source)
        markdown = result.document.export_to_markdown()
        
        # 총 아이템 수 계산
        total_items = len(list(result.document.iterate_items()))
        
        # LangChain Document 생성
        doc = Document(
            page_content=markdown,
            metadata={
                "source": source,
                "total_items": total_items,
            }
        )
        
        print(f"✅ LangChain Document 생성 완료!")
        print(f"  페이지 내용 길이: {len(doc.page_content):,} 자")
        print(f"  메타데이터: {doc.metadata}")
        print(f"\n  내용 미리보기 (처음 500자):")
        print("-" * 60)
        print(doc.page_content[:500])
        print("-" * 60)
        
        return doc
        
    except Exception as e:
        print(f"❌ 변환 실패: {e}")
        return None


def process_multiple_formats() -> None:
    """다양한 문서 형식 처리 예제"""
    print(f"\n📚 다양한 문서 형식 처리 예제")
    print("-" * 60)
    
    project_root = get_project_root()
    test_data_dir = project_root / "tests" / "test_data"
    
    if not test_data_dir.exists():
        print(f"⚠️  테스트 데이터 디렉토리가 없습니다: {test_data_dir}")
        return
    
    converter = DocumentConverter()
    
    # 지원하는 형식들
    formats = {
        "PDF": "*.pdf",
        "DOCX": "*.docx",
        "PPTX": "*.pptx",
        "XLSX": "*.xlsx",
        "HTML": "*.html",
        "이미지": "*.png,*.jpg,*.jpeg,*.tiff",
    }
    
    for format_name, pattern in formats.items():
        if "," in pattern:
            patterns = pattern.split(",")
            files = []
            for p in patterns:
                files.extend(list(test_data_dir.glob(p.strip())))
        else:
            files = list(test_data_dir.glob(pattern))
        
        if files:
            print(f"\n{format_name} 파일 발견: {len(files)}개")
            for file_path in files[:3]:  # 최대 3개만 처리
                print(f"  처리 중: {file_path.name}")
                try:
                    result = converter.convert(str(file_path))
                    markdown = result.document.export_to_markdown()
                    print(f"    ✅ 완료 (길이: {len(markdown):,} 자)")
                except Exception as e:
                    print(f"    ❌ 실패: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Docling 고급 기능 예제",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 모든 고급 예제 실행
  uv run python tests/test_docling_advanced.py
  
  # 문서 구조 분석
  uv run python tests/test_docling_advanced.py --analyze <파일경로>
  
  # 배치 처리
  uv run python tests/test_docling_advanced.py --batch <입력디렉토리> <출력디렉토리>
  
  # LangChain 통합
  uv run python tests/test_docling_advanced.py --langchain <파일경로>
        """
    )
    
    parser.add_argument(
        "--analyze",
        type=str,
        help="문서 구조 분석할 파일 경로 또는 URL"
    )
    parser.add_argument(
        "--batch",
        nargs=2,
        metavar=("INPUT_DIR", "OUTPUT_DIR"),
        help="배치 처리: 입력 디렉토리와 출력 디렉토리"
    )
    parser.add_argument(
        "--langchain",
        type=str,
        help="LangChain 통합 예제: 파일 경로 또는 URL"
    )
    parser.add_argument(
        "--formats",
        action="store_true",
        help="다양한 문서 형식 처리 예제"
    )
    
    args = parser.parse_args()
    
    if not HAS_DOCLING:
        sys.exit(1)
    
    # 특정 기능 실행
    if args.analyze:
        analyze_document_structure(args.analyze)
    elif args.batch:
        input_dir = Path(args.batch[0])
        output_dir = Path(args.batch[1])
        batch_process_documents(input_dir, output_dir)
    elif args.langchain:
        langchain_integration_example(args.langchain)
    elif args.formats:
        process_multiple_formats()
    else:
        # 모든 예제 실행
        print("="*60)
        print("🚀 Docling 고급 기능 예제")
        print("="*60)
        
        # 예제 1: 문서 구조 분석
        url = "https://arxiv.org/pdf/2408.09869"
        analyze_document_structure(url)
        
        # 예제 2: LangChain 통합
        if HAS_LANGCHAIN:
            langchain_integration_example(url)
        
        # 예제 3: 다양한 형식 처리
        process_multiple_formats()
        
        print("\n" + "="*60)
        print("✅ 모든 예제 완료!")
        print("="*60)
        print("\n💡 특정 기능만 실행하려면:")
        print("   --analyze: 문서 구조 분석")
        print("   --batch: 배치 처리")
        print("   --langchain: LangChain 통합")
        print("   --formats: 다양한 형식 처리")


if __name__ == "__main__":
    main()

