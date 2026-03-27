#!/bin/bash
# OCR 의존성 설치 스크립트 (UnstructuredPDFLoader용)

set -e

echo "=========================================="
echo "🔍 OCR 의존성 설치 스크립트"
echo "=========================================="
echo ""

# OS 감지
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux (Ubuntu/Debian/WSL)
    echo "📦 Ubuntu/Debian/WSL 환경 감지"
    echo ""
    echo "다음 명령으로 Tesseract OCR을 설치합니다:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y tesseract-ocr"
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
        
        # 추가 언어 패키지 (선택사항)
        echo ""
        echo "한국어 지원을 원하시면 다음 명령을 실행하세요:"
        echo "  sudo apt-get install -y tesseract-ocr-kor"
        echo ""
        
        echo "✅ Tesseract OCR 설치 완료!"
        echo ""
        echo "설치 확인:"
        which tesseract
        tesseract --version | head -2
    else
        echo "❌ 설치가 취소되었습니다."
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "📦 macOS 환경 감지"
    echo ""
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew가 설치되어 있지 않습니다."
        echo "   먼저 Homebrew를 설치해주세요: https://brew.sh"
        exit 1
    fi
    echo "다음 명령으로 Tesseract OCR을 설치합니다:"
    echo "  brew install tesseract"
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        brew install tesseract
        echo ""
        echo "✅ Tesseract OCR 설치 완료!"
        echo ""
        echo "설치 확인:"
        which tesseract
        tesseract --version | head -2
    else
        echo "❌ 설치가 취소되었습니다."
        exit 1
    fi
else
    echo "❌ 지원하지 않는 운영체제입니다: $OSTYPE"
    echo ""
    echo "수동 설치 가이드:"
    echo "  Ubuntu/Debian/WSL: sudo apt-get install -y tesseract-ocr"
    echo "  macOS: brew install tesseract"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 설치 완료!"
echo "=========================================="



