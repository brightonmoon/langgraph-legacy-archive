"""
PDF 파서 의존성 확인 및 설치 가이드 스크립트

이 스크립트는 PDF 파서 비교 테스트에 필요한 모든 의존성을 확인합니다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def check_poppler() -> tuple[bool, str]:
    """Poppler 설치 여부 확인"""
    try:
        result = subprocess.run(
            ["which", "pdftoppm"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, f"✅ Poppler 설치됨: {result.stdout.strip()}"
        return False, "❌ Poppler가 설치되어 있지 않습니다"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "❌ Poppler 확인 불가"


def check_python_package(package_name: str, import_name: str | None = None) -> tuple[bool, str]:
    """Python 패키지 설치 여부 확인"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True, f"✅ {package_name} 설치됨"
    except ImportError:
        return False, f"❌ {package_name} 설치 안 됨"


def main():
    """메인 함수"""
    print("=" * 80)
    print("📦 PDF 파서 의존성 확인")
    print("=" * 80)
    print()

    # Python 패키지 확인
    print("🐍 Python 패키지:")
    print("-" * 80)
    
    python_packages = [
        ("langchain-community", "langchain_community"),
        ("pypdf", "pypdf"),
        ("pymupdf", "fitz"),
        ("unstructured", "unstructured"),
        ("pdfminer.six", "pdfminer"),
        ("pi-heif", "pi_heif"),
        ("unstructured-inference", "unstructured_inference"),
        ("pdf2image", "pdf2image"),
    ]
    
    missing_python = []
    for package_name, import_name in python_packages:
        installed, msg = check_python_package(package_name, import_name)
        print(f"  {msg}")
        if not installed:
            missing_python.append(package_name)
    
    print()
    
    # 시스템 패키지 확인
    print("🖥️  시스템 패키지:")
    print("-" * 80)
    
    poppler_installed, poppler_msg = check_poppler()
    print(f"  {poppler_msg}")
    
    print()
    print("=" * 80)
    
    # 요약 및 설치 가이드
    if missing_python or not poppler_installed:
        print("⚠️  누락된 의존성 발견")
        print("=" * 80)
        print()
        
        if missing_python:
            print("📦 Python 패키지 설치:")
            print("  source /home/doyamoon/agentic_ai/.venv/bin/activate")
            print("  uv pip install " + " ".join(missing_python))
            print()
        
        if not poppler_installed:
            print("🖥️  Poppler 설치:")
            print("  Ubuntu/Debian/WSL:")
            print("    sudo apt-get update")
            print("    sudo apt-get install -y poppler-utils")
            print()
            print("  macOS:")
            print("    brew install poppler")
            print()
        
        return 1
    else:
        print("✅ 모든 의존성이 설치되어 있습니다!")
        print("=" * 80)
        return 0


if __name__ == "__main__":
    sys.exit(main())

