#!/usr/bin/env python3
"""
Google Drive API 설정 상태 확인 및 테스트 스크립트
설치된 패키지와 설정 파일의 존재 여부를 확인합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

def check_packages():
    """필요한 패키지 설치 여부 확인"""
    print("=" * 60)
    print("1️⃣ 패키지 설치 확인")
    print("=" * 60)
    
    packages = {
        'google-api-python-client': 'googleapiclient',
        'google-auth-httplib2': 'google_auth_httplib2',
        'google-auth-oauthlib': 'google_auth_oauthlib'
    }
    
    all_installed = True
    for package_name, import_name in packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name} - 설치됨")
        except ImportError:
            print(f"❌ {package_name} - 설치되지 않음")
            all_installed = False
    
    return all_installed

def check_credentials_file():
    """credentials.json 파일 존재 여부 확인"""
    print("\n" + "=" * 60)
    print("2️⃣ 인증 정보 파일 확인")
    print("=" * 60)
    
    # 가능한 경로들 확인
    env_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH', '')
    possible_paths = [
        Path(project_root / 'credentials.json'),
        Path(project_root / 'tests' / 'scripts' / 'credentials.json'),
        Path('credentials.json'),
        Path('tests/scripts/credentials.json'),
    ]
    
    # 환경 변수로 지정된 경로가 있으면 맨 앞에 추가
    if env_path:
        possible_paths.insert(0, Path(env_path))
    
    credentials_path = None
    for path in possible_paths:
        if path and path.exists() and path.is_file():
            credentials_path = path.resolve()
            print(f"✅ credentials.json 파일 발견: {credentials_path}")
            break
    
    if not credentials_path:
        print("❌ credentials.json 파일을 찾을 수 없습니다.")
        print("\n📋 credentials.json 파일 생성 방법:")
        print("1. Google Cloud Console (https://console.cloud.google.com/) 접속")
        print("2. 프로젝트 생성 또는 선택")
        print("3. 'API 및 서비스' > '라이브러리'로 이동")
        print("4. 'Google Drive API' 검색 후 활성화")
        print("5. 'API 및 서비스' > '사용자 인증 정보'로 이동")
        print("6. '사용자 인증 정보 만들기' > 'OAuth 클라이언트 ID' 선택")
        print("7. 애플리케이션 유형: '데스크톱 앱' 선택")
        print("8. 이름 입력 후 '만들기' 클릭")
        print("9. JSON 다운로드 버튼 클릭하여 credentials.json 저장")
        print("\n💡 저장 위치:")
        print("   - tests/scripts/credentials.json (권장)")
        print("   - 또는 프로젝트 루트에 저장 후 환경변수 설정")
        return None
    
    # 파일 내용 확인 (기본 구조만)
    try:
        import json
        with open(credentials_path, 'r') as f:
            creds_data = json.load(f)
            if 'installed' in creds_data or 'web' in creds_data:
                print(f"✅ credentials.json 파일 형식 확인됨")
                return credentials_path
            else:
                print("⚠️ credentials.json 파일 형식이 올바르지 않을 수 있습니다.")
                return credentials_path
    except json.JSONDecodeError:
        print("❌ credentials.json 파일이 유효한 JSON 형식이 아닙니다.")
        return None
    except Exception as e:
        print(f"⚠️ credentials.json 파일 읽기 오류: {e}")
        return credentials_path

def check_token_file():
    """token.json 파일 존재 여부 확인"""
    print("\n" + "=" * 60)
    print("3️⃣ 토큰 파일 확인")
    print("=" * 60)
    
    token_path = Path(os.getenv('GOOGLE_DRIVE_TOKEN_PATH', 'token.json'))
    possible_paths = [
        token_path,
        Path('tests/scripts/token.json'),
        Path(project_root / 'token.json')
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ token.json 파일 발견: {path.absolute()}")
            print("   (이미 인증이 완료된 상태입니다)")
            return path
    
    print("ℹ️ token.json 파일이 없습니다.")
    print("   (첫 실행 시 자동으로 생성됩니다)")
    return None

def check_env_variables():
    """환경 변수 설정 확인"""
    print("\n" + "=" * 60)
    print("4️⃣ 환경 변수 확인")
    print("=" * 60)
    
    credentials_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')
    token_path = os.getenv('GOOGLE_DRIVE_TOKEN_PATH')
    
    if credentials_path:
        print(f"✅ GOOGLE_DRIVE_CREDENTIALS_PATH: {credentials_path}")
        if Path(credentials_path).exists():
            print("   파일 존재 확인됨")
        else:
            print("   ⚠️ 파일이 존재하지 않습니다")
    else:
        print("ℹ️ GOOGLE_DRIVE_CREDENTIALS_PATH: 설정되지 않음 (기본값 사용)")
    
    if token_path:
        print(f"✅ GOOGLE_DRIVE_TOKEN_PATH: {token_path}")
    else:
        print("ℹ️ GOOGLE_DRIVE_TOKEN_PATH: 설정되지 않음 (기본값: token.json)")

def test_api_connection(credentials_path):
    """Google Drive API 연결 테스트"""
    print("\n" + "=" * 60)
    print("5️⃣ API 연결 테스트")
    print("=" * 60)
    
    if not credentials_path:
        print("❌ credentials.json 파일이 없어 테스트를 건너뜁니다.")
        return False
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        creds = None
        token_path = Path(os.getenv('GOOGLE_DRIVE_TOKEN_PATH', 'token.json'))
        
        # 저장된 토큰이 있으면 로드
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            except Exception as e:
                print(f"⚠️ 토큰 파일 로드 실패: {e}")
        
        # 유효한 인증 정보가 없으면 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✅ 토큰 갱신 성공")
                except Exception as e:
                    print(f"⚠️ 토큰 갱신 실패: {e}")
                    creds = None
            
            if not creds:
                print("ℹ️ 첫 인증이 필요합니다.")
                print("   스크립트 실행 시 브라우저가 열리고 인증을 진행합니다.")
                return False
        
        # API 서비스 빌드 및 테스트
        service = build('drive', 'v3', credentials=creds)
        
        # 간단한 API 호출 테스트 (파일 목록 조회)
        results = service.files().list(pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        print("✅ Google Drive API 연결 성공!")
        print(f"   테스트 파일 조회: {len(files)}개 항목 확인")
        return True
        
    except Exception as e:
        print(f"❌ API 연결 테스트 실패: {e}")
        print("\n가능한 원인:")
        print("1. credentials.json 파일이 올바르지 않음")
        print("2. Google Drive API가 활성화되지 않음")
        print("3. 네트워크 연결 문제")
        return False

def main():
    """메인 함수"""
    print("\n" + "=" * 60)
    print("🔍 Google Drive API 설정 상태 확인")
    print("=" * 60 + "\n")
    
    # 1. 패키지 확인
    packages_ok = check_packages()
    
    # 2. credentials 파일 확인
    credentials_path = check_credentials_file()
    
    # 3. token 파일 확인
    token_path = check_token_file()
    
    # 4. 환경 변수 확인
    check_env_variables()
    
    # 5. API 연결 테스트 (credentials가 있는 경우만)
    if credentials_path:
        api_ok = test_api_connection(credentials_path)
    else:
        api_ok = False
    
    # 최종 요약
    print("\n" + "=" * 60)
    print("📊 설정 상태 요약")
    print("=" * 60)
    
    status_items = [
        ("패키지 설치", packages_ok),
        ("credentials.json 파일", credentials_path is not None),
        ("API 연결", api_ok if credentials_path else None)
    ]
    
    for item, status in status_items:
        if status is None:
            print(f"⏸️  {item}: 확인 불가 (credentials.json 필요)")
        elif status:
            print(f"✅ {item}: 완료")
        else:
            print(f"❌ {item}: 미완료")
    
    print("\n" + "=" * 60)
    
    if packages_ok and credentials_path:
        if api_ok:
            print("🎉 모든 설정이 완료되었습니다!")
            print("\n다음 단계:")
            print("  uv run tests/scripts/download_gdrive_api.py <폴더_URL_또는_ID>")
        else:
            print("⚠️ 설정은 완료되었지만 API 연결 테스트가 필요합니다.")
            print("\n다음 단계:")
            print("  1. download_gdrive_api.py 스크립트를 실행하면 브라우저가 열립니다")
            print("  2. Google 계정으로 로그인하고 권한을 승인하세요")
            print("  3. 인증 완료 후 token.json이 생성됩니다")
    elif not packages_ok:
        print("❌ 패키지 설치가 필요합니다.")
        print("\n다음 명령어 실행:")
        print("  uv add google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    elif not credentials_path:
        print("❌ credentials.json 파일이 필요합니다.")
        print("\n위의 '인증 정보 파일 확인' 섹션을 참고하여 설정하세요.")
    
    print("=" * 60 + "\n")
    
    return 0 if (packages_ok and credentials_path) else 1

if __name__ == "__main__":
    sys.exit(main())

