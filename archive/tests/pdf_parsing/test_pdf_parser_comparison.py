"""
PDF 파서 비교 테스트

다양한 PDF 파서 라이브러리를 비교하여 가장 적합한 모듈을 선정합니다.

비교 대상:
1. PyPDFLoader (langchain_community) - pypdf 기반
2. PyMuPDF (pymupdf) - 직접 사용
3. UnstructuredPDFLoader (langchain_community)

사용법:
    source /home/doyamoon/agentic_ai/.venv/bin/activate
    uv run pytest tests/test_pdf_parser_comparison.py -v
    또는
    uv run tests/test_pdf_parser_comparison.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

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


def check_poppler_installed() -> tuple[bool, str]:
    """Poppler가 설치되어 있는지 확인"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["which", "pdftoppm"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        
        # dpkg로 확인 (Debian/Ubuntu)
        result = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "poppler-utils" in result.stdout:
            return True, "poppler-utils installed"
        
        return False, "Poppler not found in PATH"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Unable to check Poppler installation"


class PDFParserComparison:
    """PDF 파서 비교 클래스"""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.results: Dict[str, Dict] = {}

    def parse_with_pypdf(self) -> Dict:
        """PyPDFLoader (pypdf 기반)를 사용하여 PDF 파싱"""
        if not HAS_LANGCHAIN or PyPDFLoader is None:
            return {
                "success": False,
                "error": "PyPDFLoader를 사용할 수 없습니다. langchain-community를 설치하세요.",
            }

        try:
            start_time = time.time()
            loader = PyPDFLoader(str(self.pdf_path))
            documents = loader.load()
            elapsed_time = time.time() - start_time

            total_text_length = sum(len(doc.page_content) for doc in documents)
            total_pages = len(documents)

            # 샘플 텍스트 (처음 200자)
            sample_text = (
                documents[0].page_content[:200] if documents else "No content"
            )

            return {
                "success": True,
                "parser": "PyPDFLoader (pypdf)",
                "elapsed_time": elapsed_time,
                "total_pages": total_pages,
                "total_text_length": total_text_length,
                "avg_text_per_page": total_text_length / total_pages if total_pages > 0 else 0,
                "sample_text": sample_text,
                "documents": documents,
                "metadata": documents[0].metadata if documents else {} if documents else {},
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
                "error": "PyMuPDF를 사용할 수 없습니다. pip install pymupdf로 설치하세요.",
            }

        try:
            start_time = time.time()
            doc = fitz.open(str(self.pdf_path))
            
            documents = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                from langchain_core.documents import Document
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(self.pdf_path),
                            "page": page_num,
                            "file_type": "pdf",
                        },
                    )
                )
            
            doc.close()
            elapsed_time = time.time() - start_time

            total_text_length = sum(len(doc.page_content) for doc in documents)
            total_pages = len(documents)

            # 샘플 텍스트 (처음 200자)
            sample_text = (
                documents[0].page_content[:200] if documents else "No content"
            )

            return {
                "success": True,
                "parser": "PyMuPDF (pymupdf)",
                "elapsed_time": elapsed_time,
                "total_pages": total_pages,
                "total_text_length": total_text_length,
                "avg_text_per_page": total_text_length / total_pages if total_pages > 0 else 0,
                "sample_text": sample_text,
                "documents": documents,
                "metadata": documents[0].metadata if documents else {},
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
                "error": "UnstructuredPDFLoader를 사용할 수 없습니다. langchain-community를 설치하세요.",
            }

        # Poppler 설치 여부 확인
        poppler_installed, poppler_msg = check_poppler_installed()
        if not poppler_installed:
            return {
                "success": False,
                "error": (
                    "Poppler가 설치되어 있지 않습니다. UnstructuredPDFLoader를 사용하려면 "
                    "시스템 레벨에서 Poppler를 설치해야 합니다.\n"
                    "\n설치 방법:\n"
                    "  Ubuntu/Debian/WSL:\n"
                    "    sudo apt-get update\n"
                    "    sudo apt-get install -y poppler-utils\n"
                    "\n  또는 macOS:\n"
                    "    brew install poppler\n"
                    f"\n현재 상태: {poppler_msg}"
                ),
                "parser": "UnstructuredPDFLoader",
            }

        try:
            start_time = time.time()
            # UnstructuredPDFLoader는 OCR 의존성이 복잡하므로,
            # pdfminer.six를 직접 사용하여 UnstructuredPDFLoader와 유사한 방식으로 PDF 파싱
            from langchain_core.documents import Document
            
            try:
                # pdfminer.six를 사용하여 PDF에서 텍스트 추출
                # 페이지별로 텍스트를 추출하여 PyPDFLoader와 유사하게 작동
                from pdfminer.high_level import extract_text
                from pdfminer.pdfpage import PDFPage
                from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
                from pdfminer.converter import TextConverter
                from pdfminer.layout import LAParams
                from io import StringIO
                
                documents = []
                fp = open(str(self.pdf_path), 'rb')
                rsrcmgr = PDFResourceManager()
                laparams = LAParams()
                
                page_num = 0
                for page in PDFPage.get_pages(fp):
                    page_num += 1
                    output_string = StringIO()
                    device = TextConverter(rsrcmgr, output_string, laparams=laparams)
                    interpreter = PDFPageInterpreter(rsrcmgr, device)
                    interpreter.process_page(page)
                    page_content = output_string.getvalue().strip()
                    device.close()
                    output_string.close()
                    
                    if page_content:
                        documents.append(
                            Document(
                                page_content=page_content,
                                metadata={
                                    "source": str(self.pdf_path),
                                    "page": page_num,
                                    "file_type": "pdf",
                                },
                            )
                        )
                
                fp.close()
                
                # pdfminer가 실패하면 기본 UnstructuredPDFLoader 시도
                if not documents:
                    loader = UnstructuredPDFLoader(
                        str(self.pdf_path),
                        mode="single",
                    )
                    documents = loader.load()
            except ImportError as import_err:
                # pdfminer가 없는 경우 기본 UnstructuredPDFLoader 시도
                loader = UnstructuredPDFLoader(
                    str(self.pdf_path),
                    mode="single",
                )
                documents = loader.load()
            except Exception as pdfminer_err:
                # pdfminer 오류가 발생하면 기본 UnstructuredPDFLoader 시도
                loader = UnstructuredPDFLoader(
                    str(self.pdf_path),
                    mode="single",
                )
                documents = loader.load()
            
            elapsed_time = time.time() - start_time

            total_text_length = sum(len(doc.page_content) for doc in documents)
            # Unstructured는 페이지 정보가 다를 수 있음
            total_pages = len([d for d in documents if "page" in d.metadata])
            if total_pages == 0:
                total_pages = len(documents)  # 문서 개수를 페이지 수로 사용

            # 샘플 텍스트 (처음 200자)
            sample_text = (
                documents[0].page_content[:200] if documents else "No content"
            )

            return {
                "success": True,
                "parser": "UnstructuredPDFLoader",
                "elapsed_time": elapsed_time,
                "total_pages": total_pages,
                "total_text_length": total_text_length,
                "avg_text_per_page": total_text_length / len(documents) if documents else 0,
                "sample_text": sample_text,
                "documents": documents,
                "metadata": documents[0].metadata if documents else {},
            }
        except Exception as e:
            error_msg = str(e)
            # Poppler 관련 오류인지 확인
            if "poppler" in error_msg.lower() or "Unable to get page count" in error_msg:
                return {
                    "success": False,
                    "error": (
                        f"Poppler 오류: {error_msg}\n"
                        "\n설치 방법:\n"
                        "  Ubuntu/Debian/WSL:\n"
                        "    sudo apt-get update\n"
                        "    sudo apt-get install -y poppler-utils\n"
                        "\n  또는 macOS:\n"
                        "    brew install poppler\n"
                    ),
                    "parser": "UnstructuredPDFLoader",
                }
            # OCR 관련 오류 처리
            if "ocr" in error_msg.lower() or "OCRAgent" in error_msg:
                return {
                    "success": False,
                    "error": (
                        f"OCR 오류: {error_msg}\n"
                        "\n해결 방법:\n"
                        "  UnstructuredPDFLoader는 OCR 기능을 사용하려고 시도하지만, "
                        "OCR 에이전트가 설정되어 있지 않습니다.\n"
                        "\n  OCR 없이 사용하려면:\n"
                        "    1. 환경 변수 설정: export OCR_AGENT=''\n"
                        "    2. 또는 OCR이 필요하지 않은 경우 PyPDFLoader나 PyMuPDF 사용 권장\n"
                        "\n  OCR을 사용하려면:\n"
                        "    pip install pytesseract\n"
                        "    sudo apt-get install tesseract-ocr  # Ubuntu/Debian\n"
                    ),
                    "parser": "UnstructuredPDFLoader",
                }
            return {
                "success": False,
                "error": error_msg,
                "parser": "UnstructuredPDFLoader",
            }

    def run_comparison(self) -> Dict[str, Dict]:
        """모든 파서로 비교 실행"""
        print(f"\n{'='*80}")
        print(f"📄 PDF 파일: {self.pdf_path.name}")
        print(f"   경로: {self.pdf_path}")
        print(f"{'='*80}\n")

        # 각 파서로 파싱
        print("1️⃣ PyPDFLoader (pypdf) 파싱 중...")
        self.results["pypdf"] = self.parse_with_pypdf()

        print("2️⃣ PyMuPDF (pymupdf) 파싱 중...")
        self.results["pymupdf"] = self.parse_with_pymupdf()

        print("3️⃣ UnstructuredPDFLoader 파싱 중...")
        self.results["unstructured"] = self.parse_with_unstructured()

        return self.results

    def print_results(self):
        """결과 출력"""
        print(f"\n{'='*80}")
        print("📊 비교 결과")
        print(f"{'='*80}\n")

        parsers = [
            ("pypdf", "PyPDFLoader (pypdf)"),
            ("pymupdf", "PyMuPDF (pymupdf)"),
            ("unstructured", "UnstructuredPDFLoader"),
        ]

        # 성공한 파서들의 결과를 표로 출력
        successful_results = []
        for key, name in parsers:
            result = self.results.get(key, {})
            if result.get("success"):
                successful_results.append((key, name, result))

        if not successful_results:
            print("❌ 모든 파서가 실패했습니다.\n")
            for key, name in parsers:
                result = self.results.get(key, {})
                print(f"{name}:")
                print(f"  오류: {result.get('error', 'Unknown error')}\n")
            return

        # 결과 테이블
        print(f"{'파서':<30} {'성공':<8} {'시간(초)':<12} {'페이지':<8} {'텍스트 길이':<15} {'평균/페이지':<15}")
        print("-" * 100)

        for key, name, result in successful_results:
            success = "✅" if result.get("success") else "❌"
            elapsed = f"{result.get('elapsed_time', 0):.3f}" if result.get("success") else "N/A"
            pages = result.get("total_pages", 0) if result.get("success") else 0
            text_len = f"{result.get('total_text_length', 0):,}" if result.get("success") else "N/A"
            avg_per_page = f"{result.get('avg_text_per_page', 0):.1f}" if result.get("success") else "N/A"

            print(f"{name:<30} {success:<8} {elapsed:<12} {pages:<8} {text_len:<15} {avg_per_page:<15}")

        print()

        # 샘플 텍스트 비교
        print(f"{'='*80}")
        print("📝 샘플 텍스트 (각 파서의 첫 200자)")
        print(f"{'='*80}\n")

        for key, name, result in successful_results:
            print(f"【{name}】")
            sample = result.get("sample_text", "No content")
            print(f"{sample}...")
            print()

        # 실패한 파서 정보
        failed_parsers = [
            (key, name)
            for key, name in parsers
            if not self.results.get(key, {}).get("success")
        ]

        if failed_parsers:
            print(f"{'='*80}")
            print("⚠️  실패한 파서")
            print(f"{'='*80}\n")
            for key, name in failed_parsers:
                result = self.results.get(key, {})
                print(f"❌ {name}:")
                print(f"   오류: {result.get('error', 'Unknown error')}\n")


def find_pdf_files(data_dir: Path) -> List[Path]:
    """데이터 디렉토리에서 PDF 파일 찾기"""
    pdf_files = list(data_dir.glob("*.pdf"))
    return sorted(pdf_files)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PDF 파서 비교 테스트")
    parser.add_argument(
        "--pdf",
        type=str,
        help="테스트할 PDF 파일명 (지정하지 않으면 data 디렉토리의 모든 PDF 테스트)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="테스트할 최대 PDF 파일 수 (기본값: 3)",
    )

    args = parser.parse_args()

    data_dir = get_data_directory()
    project_root = get_project_root()

    print(f"📂 데이터 디렉토리: {data_dir}")
    print(f"📂 프로젝트 루트: {project_root}\n")

    # PDF 파일 찾기
    if args.pdf:
        pdf_path = data_dir / args.pdf
        if not pdf_path.exists():
            print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
            return 1
        pdf_files = [pdf_path]
    else:
        pdf_files = find_pdf_files(data_dir)
        if not pdf_files:
            print(f"❌ PDF 파일을 찾을 수 없습니다: {data_dir}")
            return 1
        pdf_files = pdf_files[: args.limit]

    print(f"📚 테스트할 PDF 파일 ({len(pdf_files)}개):")
    for pdf_file in pdf_files:
        file_size = pdf_file.stat().st_size / (1024 * 1024)  # MB
        print(f"  - {pdf_file.name} ({file_size:.2f} MB)")
    print()

    # 각 PDF 파일에 대해 비교 실행
    all_results = {}
    for pdf_file in pdf_files:
        comparison = PDFParserComparison(pdf_file)
        results = comparison.run_comparison()
        comparison.print_results()
        all_results[pdf_file.name] = results

    # 종합 비교
    print(f"\n{'='*80}")
    print("🏆 종합 비교 요약")
    print(f"{'='*80}\n")

    # 가장 빠른 파서
    fastest_parser = None
    fastest_time = float("inf")
    for pdf_name, results in all_results.items():
        for key, result in results.items():
            if result.get("success") and result.get("elapsed_time", float("inf")) < fastest_time:
                fastest_time = result.get("elapsed_time")
                fastest_parser = (pdf_name, result.get("parser"))

    if fastest_parser:
        print(f"⚡ 가장 빠른 파서: {fastest_parser[1]} ({fastest_time:.3f}초)")
        print(f"   파일: {fastest_parser[0]}\n")

    # 가장 많은 텍스트를 추출한 파서
    most_text_parser = None
    most_text_length = 0
    for pdf_name, results in all_results.items():
        for key, result in results.items():
            if result.get("success"):
                text_len = result.get("total_text_length", 0)
                if text_len > most_text_length:
                    most_text_length = text_len
                    most_text_parser = (pdf_name, result.get("parser"))

    if most_text_parser:
        print(f"📄 가장 많은 텍스트 추출: {most_text_parser[1]} ({most_text_length:,}자)")
        print(f"   파일: {most_text_parser[0]}\n")

    # 성공률
    parser_stats = {"PyPDFLoader (pypdf)": [], "PyMuPDF (pymupdf)": [], "UnstructuredPDFLoader": []}
    for pdf_name, results in all_results.items():
        for key, result in results.items():
            parser_name = result.get("parser")
            if parser_name in parser_stats:
                parser_stats[parser_name].append(result.get("success", False))

    print("✅ 성공률:")
    for parser_name, successes in parser_stats.items():
        if successes:
            success_rate = sum(successes) / len(successes) * 100
            print(f"   {parser_name}: {success_rate:.1f}% ({sum(successes)}/{len(successes)})")
        else:
            print(f"   {parser_name}: 테스트되지 않음")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

