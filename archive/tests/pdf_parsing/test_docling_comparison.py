"""
Docling과 기존 PDF 파서 비교 테스트

Docling과 다른 PDF 파서들(PyPDFLoader, PyMuPDF, UnstructuredPDFLoader)을 비교합니다.

비교 항목:
- 처리 속도
- 텍스트 추출 품질
- 레이아웃 보존
- 테이블 구조 인식
- 복잡한 문서 처리 능력

사용법:
    uv run python tests/test_docling_comparison.py [--file <PDF파일경로>]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Docling
try:
    from docling.document_converter import DocumentConverter
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    DocumentConverter = None

# 기존 파서들
try:
    from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    PyPDFLoader = None
    UnstructuredPDFLoader = None

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    fitz = None

from src.utils.paths import get_data_directory, get_project_root


def analyze_text_structure(text: str) -> Dict:
    """텍스트 구조 분석"""
    lines = text.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # 통계 정보
    word_count = len(re.findall(r'\b\w+\b', text))
    sentence_count = len(re.findall(r'[.!?]+', text))
    paragraph_count = len([line for line in lines if line.strip() and not line.strip().startswith(' ')])
    
    # 텍스트 품질 지표
    avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0
    max_line_length = max((len(line) for line in non_empty_lines), default=0)
    
    # 단어 단위로 잘 분리되었는지 확인
    fragmented_lines = sum(1 for line in non_empty_lines if len(line) == 1)
    fragmented_ratio = fragmented_lines / len(non_empty_lines) if non_empty_lines else 0
    
    return {
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty_lines),
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_line_length": avg_line_length,
        "max_line_length": max_line_length,
        "fragmented_lines": fragmented_lines,
        "fragmented_ratio": fragmented_ratio,
    }


def extract_key_elements(text: str) -> Dict:
    """주요 요소 추출"""
    # 제목 추출
    title_candidates = []
    lines = text.split('\n')
    for line in lines[:50]:
        line = line.strip()
        if 5 < len(line) < 200 and line and line[0].isupper():
            title_candidates.append(line)
    
    # 키워드 추출
    keywords = re.findall(r'\b[A-Z][A-Z\s]+\b', text)
    keywords = [kw.strip() for kw in keywords if len(kw.strip()) > 2][:20]
    
    # 숫자/날짜 추출
    numbers = re.findall(r'\b\d{4,5}\b', text)
    dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
    
    # 이메일 추출
    emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
    
    return {
        "title_candidates": title_candidates[:5],
        "keywords": list(set(keywords))[:10],
        "years": list(set(numbers))[:5],
        "dates": list(set(dates))[:5],
        "emails": list(set(emails))[:5],
    }


class PDFParserComparison:
    """PDF 파서 비교 클래스"""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.results: Dict[str, Dict] = {}

    def parse_with_docling(self) -> Dict:
        """Docling을 사용하여 PDF 파싱"""
        if not HAS_DOCLING:
            return {
                "success": False,
                "error": "Docling이 설치되지 않았습니다.",
            }

        try:
            start_time = time.time()
            # DocumentConverter는 기본 생성자만 사용 (파라미터 없음)
            converter = DocumentConverter()
            result = converter.convert(str(self.pdf_path))
            elapsed_time = time.time() - start_time

            # Markdown으로 변환
            markdown = result.document.export_to_markdown()
            
            structure = analyze_text_structure(markdown)
            key_elements = extract_key_elements(markdown)
            
            # 테이블, 이미지, 수식 개수
            table_count = len(result.document.tables) if hasattr(result.document, 'tables') else 0
            image_count = len(result.document.pictures) if hasattr(result.document, 'pictures') else 0
            
            # 수식 개수 계산
            formula_count = 0
            try:
                for item_tuple in result.document.iterate_items():
                    item = item_tuple[0] if isinstance(item_tuple, tuple) else item_tuple
                    if hasattr(item, 'formula') or type(item).__name__ == 'FormulaItem':
                        formula_count += 1
            except Exception:
                pass
            
            # 총 아이템 수
            total_items = len(list(result.document.iterate_items()))

            return {
                "success": True,
                "parser": "Docling",
                "elapsed_time": elapsed_time,
                "total_items": total_items,
                "total_text_length": len(markdown),
                "full_text": markdown,
                "structure": structure,
                "key_elements": key_elements,
                "table_count": table_count,
                "image_count": image_count,
                "formula_count": formula_count,
                "sample_text": markdown[:500] if markdown else "No content",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parser": "Docling",
            }

    def parse_with_pypdf(self) -> Dict:
        """PyPDFLoader (pypdf 기반)를 사용하여 PDF 파싱"""
        if not HAS_LANGCHAIN or PyPDFLoader is None:
            return {
                "success": False,
                "error": "PyPDFLoader를 사용할 수 없습니다.",
            }

        try:
            start_time = time.time()
            loader = PyPDFLoader(str(self.pdf_path))
            documents = loader.load()
            elapsed_time = time.time() - start_time

            full_text = "\n".join(doc.page_content for doc in documents)
            
            structure = analyze_text_structure(full_text)
            key_elements = extract_key_elements(full_text)

            return {
                "success": True,
                "parser": "PyPDFLoader (pypdf)",
                "elapsed_time": elapsed_time,
                "total_pages": len(documents),
                "total_text_length": len(full_text),
                "full_text": full_text,
                "structure": structure,
                "key_elements": key_elements,
                "sample_text": full_text[:500] if full_text else "No content",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parser": "PyPDFLoader (pypdf)",
            }

    def parse_with_pymupdf(self) -> Dict:
        """PyMuPDF (fitz)를 직접 사용하여 PDF 파싱"""
        if not HAS_PYMUPDF:
            return {
                "success": False,
                "error": "PyMuPDF를 사용할 수 없습니다.",
            }

        try:
            start_time = time.time()
            doc = fitz.open(str(self.pdf_path))
            
            full_text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                full_text_parts.append(text)
            
            doc.close()
            elapsed_time = time.time() - start_time

            full_text = "\n".join(full_text_parts)
            
            structure = analyze_text_structure(full_text)
            key_elements = extract_key_elements(full_text)

            return {
                "success": True,
                "parser": "PyMuPDF (pymupdf)",
                "elapsed_time": elapsed_time,
                "total_pages": len(full_text_parts),
                "total_text_length": len(full_text),
                "full_text": full_text,
                "structure": structure,
                "key_elements": key_elements,
                "sample_text": full_text[:500] if full_text else "No content",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parser": "PyMuPDF (pymupdf)",
            }

    def parse_with_unstructured(self) -> Dict:
        """UnstructuredPDFLoader를 사용하여 PDF 파싱"""
        if not HAS_LANGCHAIN or UnstructuredPDFLoader is None:
            return {
                "success": False,
                "error": "UnstructuredPDFLoader를 사용할 수 없습니다.",
            }

        try:
            start_time = time.time()
            loader = UnstructuredPDFLoader(
                str(self.pdf_path),
                mode="elements",
                strategy="auto",
            )
            documents = loader.load()
            elapsed_time = time.time() - start_time

            full_text = "\n".join(doc.page_content for doc in documents)
            
            structure = analyze_text_structure(full_text)
            key_elements = extract_key_elements(full_text)

            return {
                "success": True,
                "parser": "UnstructuredPDFLoader",
                "elapsed_time": elapsed_time,
                "total_elements": len(documents),
                "total_text_length": len(full_text),
                "full_text": full_text,
                "structure": structure,
                "key_elements": key_elements,
                "sample_text": full_text[:500] if full_text else "No content",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parser": "UnstructuredPDFLoader",
            }

    def compare_all(self) -> Dict:
        """모든 파서로 파싱하고 비교"""
        print(f"\n{'='*60}")
        print(f"📊 PDF 파서 비교 테스트")
        print(f"{'='*60}")
        print(f"파일: {self.pdf_path}")
        print(f"{'='*60}\n")

        # 각 파서로 파싱
        parsers = [
            ("Docling", self.parse_with_docling),
            ("PyPDFLoader", self.parse_with_pypdf),
            ("PyMuPDF", self.parse_with_pymupdf),
            ("UnstructuredPDFLoader", self.parse_with_unstructured),
        ]

        for parser_name, parse_func in parsers:
            print(f"🔄 {parser_name}로 파싱 중...")
            result = parse_func()
            self.results[parser_name] = result
            
            if result.get("success"):
                print(f"  ✅ 완료 ({result.get('elapsed_time', 0):.2f}초)")
            else:
                print(f"  ❌ 실패: {result.get('error', 'Unknown error')}")

        return self.results

    def print_comparison(self) -> None:
        """비교 결과 출력"""
        print(f"\n{'='*60}")
        print(f"📊 비교 결과")
        print(f"{'='*60}\n")

        # 성공한 파서만 필터링
        successful_results = {
            name: result for name, result in self.results.items()
            if result.get("success", False)
        }

        if not successful_results:
            print("❌ 성공한 파서가 없습니다.")
            return

        # 처리 시간 비교
        print("⏱️  처리 시간 비교:")
        print("-" * 60)
        sorted_by_time = sorted(
            successful_results.items(),
            key=lambda x: x[1].get("elapsed_time", float('inf'))
        )
        for i, (name, result) in enumerate(sorted_by_time, 1):
            time_val = result.get("elapsed_time", 0)
            print(f"  {i}. {name:25s}: {time_val:6.2f}초")
        print()

        # 텍스트 길이 비교
        print("📏 텍스트 길이 비교:")
        print("-" * 60)
        sorted_by_length = sorted(
            successful_results.items(),
            key=lambda x: x[1].get("total_text_length", 0),
            reverse=True
        )
        for i, (name, result) in enumerate(sorted_by_length, 1):
            length = result.get("total_text_length", 0)
            print(f"  {i}. {name:25s}: {length:8,} 자")
        print()

        # 텍스트 품질 비교
        print("📊 텍스트 품질 비교:")
        print("-" * 60)
        for name, result in sorted(successful_results.items()):
            structure = result.get("structure", {})
            print(f"\n  {name}:")
            print(f"    • 단어 수: {structure.get('word_count', 0):,}")
            print(f"    • 문장 수: {structure.get('sentence_count', 0):,}")
            print(f"    • 평균 줄 길이: {structure.get('avg_line_length', 0):.1f}")
            print(f"    • 단편화 비율: {structure.get('fragmented_ratio', 0):.2%}")

        # Docling 특별 기능
        if "Docling" in successful_results:
            docling_result = successful_results["Docling"]
            print(f"\n  Docling 특별 기능:")
            print(f"    • 테이블 수: {docling_result.get('table_count', 0)}")
            print(f"    • 이미지 수: {docling_result.get('image_count', 0)}")
            print(f"    • 수식 수: {docling_result.get('formula_count', 0)}")
            print(f"    • 총 아이템 수: {docling_result.get('total_items', 0)}")

        # 샘플 텍스트 비교
        print(f"\n{'='*60}")
        print(f"📝 샘플 텍스트 비교 (처음 300자)")
        print(f"{'='*60}")
        for name, result in sorted(successful_results.items()):
            sample = result.get("sample_text", "")[:300]
            print(f"\n{name}:")
            print("-" * 60)
            print(sample)
            if len(result.get("sample_text", "")) > 300:
                print("...")

    def save_comparison(self, output_file: Optional[Path] = None) -> None:
        """비교 결과를 파일로 저장"""
        if output_file is None:
            output_file = Path("test_output") / f"docling_comparison_{self.pdf_path.stem}.md"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            "# Docling 파서 비교 결과\n",
            f"**파일**: `{self.pdf_path}`\n",
            f"**생성 시간**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "\n## 비교 결과\n\n",
        ]
        
        successful_results = {
            name: result for name, result in self.results.items()
            if result.get("success", False)
        }
        
        # 요약 테이블
        lines.append("| 파서 | 처리 시간 (초) | 텍스트 길이 | 단어 수 |\n")
        lines.append("|------|---------------|------------|----------|\n")
        
        for name, result in sorted(successful_results.items()):
            structure = result.get("structure", {})
            lines.append(
                f"| {name} | "
                f"{result.get('elapsed_time', 0):.2f} | "
                f"{result.get('total_text_length', 0):,} | "
                f"{structure.get('word_count', 0):,} |\n"
            )
        
        lines.append("\n## 상세 결과\n\n")
        
        for name, result in sorted(successful_results.items()):
            lines.append(f"### {name}\n\n")
            lines.append(f"- **처리 시간**: {result.get('elapsed_time', 0):.2f}초\n")
            lines.append(f"- **텍스트 길이**: {result.get('total_text_length', 0):,} 자\n")
            
            structure = result.get("structure", {})
            lines.append(f"- **단어 수**: {structure.get('word_count', 0):,}\n")
            lines.append(f"- **문장 수**: {structure.get('sentence_count', 0):,}\n")
            
            if "table_count" in result:
                lines.append(f"- **테이블 수**: {result.get('table_count', 0)}\n")
            if "image_count" in result:
                lines.append(f"- **이미지 수**: {result.get('image_count', 0)}\n")
            if "formula_count" in result:
                lines.append(f"- **수식 수**: {result.get('formula_count', 0)}\n")
            
            lines.append("\n**샘플 텍스트**:\n\n")
            lines.append("```\n")
            lines.append(result.get("sample_text", "")[:1000])
            lines.append("\n```\n\n")
        
        output_file.write_text("".join(lines), encoding="utf-8")
        print(f"\n💾 비교 결과 저장: {output_file}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Docling과 기존 PDF 파서 비교 테스트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 비교 (테스트 데이터 디렉토리에서 PDF 찾기)
  uv run python tests/test_docling_comparison.py
  
  # 특정 파일 비교
  uv run python tests/test_docling_comparison.py --file document.pdf
  
  # URL에서 비교
  uv run python tests/test_docling_comparison.py --url https://arxiv.org/pdf/2408.09869
  
  # 결과를 파일로 저장
  uv run python tests/test_docling_comparison.py --file document.pdf --output result.md
        """
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="비교할 PDF 파일 경로"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="비교할 PDF URL (다운로드 후 비교)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="결과 저장 파일 경로"
    )
    
    args = parser.parse_args()
    
    # PDF 파일 찾기
    pdf_path = None
    
    if args.file:
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
            sys.exit(1)
    elif args.url:
        # URL에서 다운로드
        import requests
        print(f"📥 URL에서 다운로드 중: {args.url}")
        try:
            response = requests.get(args.url, timeout=30)
            response.raise_for_status()
            
            pdf_path = Path("test_output") / "downloaded.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(response.content)
            print(f"✅ 다운로드 완료: {pdf_path}")
        except Exception as e:
            print(f"❌ 다운로드 실패: {e}")
            sys.exit(1)
    else:
        # 테스트 데이터 디렉토리에서 찾기
        project_root = get_project_root()
        test_data_dir = project_root / "tests" / "test_data"
        
        if test_data_dir.exists():
            pdf_files = list(test_data_dir.glob("*.pdf"))
            if pdf_files:
                pdf_path = pdf_files[0]
                print(f"📁 테스트 파일 사용: {pdf_path}")
            else:
                print(f"⚠️  {test_data_dir}에 PDF 파일이 없습니다.")
                print("   --file 또는 --url 옵션을 사용하세요.")
                sys.exit(1)
        else:
            print(f"⚠️  테스트 데이터 디렉토리가 없습니다: {test_data_dir}")
            print("   --file 또는 --url 옵션을 사용하세요.")
            sys.exit(1)
    
    # 비교 실행
    comparison = PDFParserComparison(pdf_path)
    comparison.compare_all()
    comparison.print_comparison()
    
    # 결과 저장
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = None
    comparison.save_comparison(output_file)


if __name__ == "__main__":
    main()

