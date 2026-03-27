#!/usr/bin/env python3
"""
Google Drive 폴더 다운로드 스크립트
gdown을 사용하여 Google Drive 폴더를 다운로드합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def extract_folder_id(url: str) -> str:
    """Google Drive 폴더 URL에서 폴더 ID를 추출합니다."""
    # URL 형식: https://drive.google.com/drive/u/0/folders/{FOLDER_ID}
    if 'folders/' in url:
        folder_id = url.split('folders/')[-1].split('?')[0].split('/')[0]
        return folder_id
    # 이미 ID만 있는 경우
    elif len(url) == 33 and url.isalnum():
        return url
    else:
        raise ValueError(f"유효하지 않은 폴더 URL 또는 ID: {url}")

def download_folder(folder_url_or_id: str, output_dir: str = "./downloads"):
    """Google Drive 폴더를 다운로드합니다."""
    import gdown
    
    # 폴더 ID 추출
    try:
        folder_id = extract_folder_id(folder_url_or_id)
        print(f"📁 폴더 ID: {folder_id}")
    except ValueError as e:
        print(f"❌ 오류: {e}")
        return False
    
    # 출력 디렉토리 생성
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # gdown을 사용하여 폴더 다운로드
    # 폴더 URL 형식: https://drive.google.com/drive/folders/{FOLDER_ID}
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    print(f"📥 다운로드 시작: {folder_url}")
    print(f"📂 저장 위치: {output_path.absolute()}")
    
    try:
        # --folder 옵션으로 폴더 다운로드
        # --remaining-ok: 50개 이상 파일이 있어도 다운로드 계속
        gdown.download_folder(
            folder_url,
            output=str(output_path),
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
        print(f"✅ 다운로드 완료: {output_path.absolute()}")
        return True
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. Google Drive 폴더 공유 설정을 '링크가 있는 모든 사용자'로 변경하세요")
        print("2. 폴더에 최대 50개 파일이 있는지 확인하세요 (50개 초과 시 --remaining-ok 필요)")
        print("3. 폴더 URL이 올바른지 확인하세요")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Google Drive 폴더를 다운로드합니다"
    )
    parser.add_argument(
        "folder_url",
        help="Google Drive 폴더 URL 또는 폴더 ID"
    )
    parser.add_argument(
        "-o", "--output",
        default="./downloads",
        help="다운로드할 디렉토리 경로 (기본값: ./downloads)"
    )
    
    args = parser.parse_args()
    
    success = download_folder(args.folder_url, args.output)
    sys.exit(0 if success else 1)


