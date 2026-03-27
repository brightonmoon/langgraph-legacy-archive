#!/usr/bin/env python3
"""
Google Drive API를 사용하여 폴더 및 파일 다운로드 스크립트
gdown 대신 공식 Google Drive API를 사용하여 더 많은 제어와 기능을 제공합니다.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
except ImportError as e:
    print("❌ 필요한 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요:")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)


# Google Drive API 스코프
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveDownloader:
    """Google Drive API를 사용하여 파일 및 폴더를 다운로드하는 클래스"""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Args:
            credentials_path: OAuth 2.0 클라이언트 인증 정보 JSON 파일 경로
            token_path: 저장된 토큰 파일 경로 (기본값: token.json)
        """
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_DRIVE_CREDENTIALS_PATH',
            'credentials.json'
        )
        self.token_path = token_path or os.getenv(
            'GOOGLE_DRIVE_TOKEN_PATH',
            'token.json'
        )
        self.service = None
        self._progress_lock = Lock()  # 진행 상황 추적용 락
        self._download_stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0
        }
        self._authenticate()
    
    def _authenticate(self):
        """Google Drive API 인증 수행"""
        creds = None
        
        # 저장된 토큰이 있으면 로드
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"⚠️ 토큰 파일 로드 실패: {e}")
        
        # 유효한 인증 정보가 없으면 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 토큰 갱신
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"⚠️ 토큰 갱신 실패: {e}")
                    creds = None
            
            if not creds:
                # 새로 인증
                if not os.path.exists(self.credentials_path):
                    print(f"❌ 인증 정보 파일을 찾을 수 없습니다: {self.credentials_path}")
                    print("\n📋 설정 방법:")
                    print("1. Google Cloud Console에서 프로젝트 생성")
                    print("2. Google Drive API 활성화")
                    print("3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 애플리케이션)")
                    print("4. credentials.json 파일을 다운로드하여 이 스크립트와 같은 디렉토리에 저장")
                    print(f"5. 또는 환경변수 GOOGLE_DRIVE_CREDENTIALS_PATH로 경로 지정")
                    sys.exit(1)
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Drive API 서비스 빌드
        self.service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive API 인증 완료")
    
    def extract_folder_id(self, url: str) -> str:
        """Google Drive 폴더 URL에서 폴더 ID를 추출합니다."""
        if 'folders/' in url:
            folder_id = url.split('folders/')[-1].split('?')[0].split('/')[0]
            return folder_id
        elif len(url) == 33 and url.replace('-', '').replace('_', '').isalnum():
            return url
        else:
            raise ValueError(f"유효하지 않은 폴더 URL 또는 ID: {url}")
    
    def list_folder_contents(self, folder_id: str = 'root', drive_id: Optional[str] = None, 
                            max_results: Optional[int] = None, first_page_only: bool = False) -> List[dict]:
        """폴더 내 파일 및 하위 폴더 목록 조회
        
        Args:
            folder_id: 폴더 ID (기본값: 'root' - 내 드라이브 루트)
            drive_id: 공유 드라이브 ID (공유 드라이브 내 폴더 조회 시 필요)
            max_results: 최대 결과 수 (None이면 모든 페이지 조회)
            first_page_only: 첫 페이지만 조회 (빠른 조회용)
        """
        try:
            import time
            results = []
            page_token = None
            page_count = 0
            max_pages = 1 if first_page_only else None
            
            # 공유 드라이브 지원 파라미터
            supports_all_drives = drive_id is not None
            include_items_from_all_drives = drive_id is not None
            
            # 페이지 크기 설정 (API 제한 고려)
            page_size = 100 if max_results is None else min(max_results, 100)
            
            while True:
                # 최대 결과 수 체크
                if max_results and len(results) >= max_results:
                    break
                
                # 폴더 내 항목 조회
                if folder_id == 'root':
                    if drive_id:
                        # 공유 드라이브 루트 - 공유 드라이브의 경우 쿼리를 단순화
                        # 공유 드라이브에서는 루트의 직접적인 부모가 없으므로 다른 방식 사용
                        query = "trashed=false"
                    else:
                        # 내 드라이브 루트
                        query = "'root' in parents and trashed=false"
                else:
                    query = f"'{folder_id}' in parents and trashed=false"
                
                request_params = {
                    'q': query,
                    'spaces': 'drive',
                    'fields': 'nextPageToken, files(id, name, mimeType, size, modifiedTime, shared)',
                    'pageToken': page_token,
                    'pageSize': page_size,
                    'orderBy': 'folder,name',
                    'supportsAllDrives': supports_all_drives,
                    'includeItemsFromAllDrives': include_items_from_all_drives
                }
                
                if drive_id:
                    request_params['corpora'] = 'drive'
                    request_params['driveId'] = drive_id
                
                # API 호출 (rate limit 고려하여 짧은 딜레이)
                if page_count > 0:
                    time.sleep(0.1)  # API rate limit 방지 (초당 100개 제한)
                
                try:
                    response = self.service.files().list(**request_params).execute()
                except Exception as e:
                    error_str = str(e)
                    # 500 에러 또는 internalError 발생 시 재시도
                    if '500' in error_str or 'internalError' in error_str:
                        # 페이지 토큰이 있는 경우 제거하고 재시도
                        if page_token:
                            print(f"  ⚠️ API 오류 발생 (페이지 토큰 문제일 수 있음), 재시도 중...")
                            request_params.pop('pageToken', None)
                            time.sleep(0.5)  # 재시도 전 대기
                            try:
                                response = self.service.files().list(**request_params).execute()
                            except Exception as e2:
                                print(f"  ❌ 재시도 실패: {e2}")
                                raise e
                        else:
                            # 첫 페이지에서 에러 발생 시 재시도
                            print(f"  ⚠️ API 오류 발생, 재시도 중...")
                            time.sleep(1)  # 재시도 전 대기
                            try:
                                response = self.service.files().list(**request_params).execute()
                            except Exception as e2:
                                print(f"  ❌ 재시도 실패: {e2}")
                                raise e
                    else:
                        raise e
                
                page_count += 1
                
                items = response.get('files', [])
                results.extend(items)
                
                # 최대 결과 수에 도달했는지 확인
                if max_results and len(results) >= max_results:
                    results = results[:max_results]
                    break
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                # 첫 페이지만 조회 옵션
                if first_page_only:
                    break
            
            return results
        except Exception as e:
            print(f"❌ 폴더 내용 조회 실패: {e}")
            return []
    
    def list_shared_with_me(self) -> List[dict]:
        """공유 문서함의 파일 및 폴더 목록 조회"""
        try:
            results = []
            page_token = None
            
            while True:
                query = "sharedWithMe=true and trashed=false"
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, modifiedTime, owners)',
                    pageToken=page_token,
                    orderBy='modifiedTime desc'
                ).execute()
                
                items = response.get('files', [])
                results.extend(items)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results
        except Exception as e:
            print(f"❌ 공유 문서함 조회 실패: {e}")
            return []
    
    def list_starred(self) -> List[dict]:
        """별표 표시된 파일 및 폴더 목록 조회"""
        try:
            results = []
            page_token = None
            
            while True:
                query = "starred=true and trashed=false"
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, modifiedTime)',
                    pageToken=page_token,
                    orderBy='modifiedTime desc'
                ).execute()
                
                items = response.get('files', [])
                results.extend(items)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results
        except Exception as e:
            print(f"❌ 별표 표시 항목 조회 실패: {e}")
            return []
    
    def list_shared_drives(self) -> List[dict]:
        """공유 드라이브(Shared Drives) 목록 조회"""
        try:
            import time
            results = []
            page_token = None
            page_count = 0
            
            while True:
                # API rate limit 고려하여 딜레이 추가
                if page_count > 0:
                    time.sleep(0.1)
                
                response = self.service.drives().list(
                    pageSize=100,
                    pageToken=page_token
                ).execute()
                
                page_count += 1
                drives = response.get('drives', [])
                results.extend(drives)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results
        except Exception as e:
            print(f"❌ 공유 드라이브 조회 실패: {e}")
            return []
    
    def list_shared_drive_contents(self, drive_id: str) -> List[dict]:
        """공유 드라이브 내 파일 및 폴더 목록 조회
        
        Args:
            drive_id: 공유 드라이브 ID
        """
        return self.list_folder_contents('root', drive_id=drive_id)
    
    def find_folder_by_path(self, path: str, drive_id: Optional[str] = None, start_folder_id: str = 'root') -> Optional[str]:
        """경로를 따라가며 폴더 ID 찾기
        
        Args:
            path: 경로 문자열 (예: "플랫폼개발팀/논문" 또는 "플랫폼개발팀\\논문")
            drive_id: 공유 드라이브 ID (공유 드라이브 내 경로 탐색 시 필요)
            start_folder_id: 시작 폴더 ID (기본값: 'root')
        
        Returns:
            찾은 폴더 ID, 없으면 None
        """
        # 경로 구분자 정규화 (/, \ 모두 지원)
        path_parts = [p.strip() for p in path.replace('\\', '/').split('/') if p.strip()]
        
        if not path_parts:
            return start_folder_id
        
        current_folder_id = start_folder_id
        
        for i, folder_name in enumerate(path_parts):
            print(f"  🔍 경로 탐색 중: {'/'.join(path_parts[:i+1])}")
            
            # 현재 폴더의 내용 조회 (경로 탐색 시에는 모든 페이지 검색)
            try:
                # 경로 탐색 중이므로 폴더를 찾을 때까지 모든 페이지 검색
                items = self.list_folder_contents(current_folder_id, drive_id=drive_id, first_page_only=False)
            except Exception as e:
                print(f"  ❌ 폴더 내용 조회 실패: {e}")
                # 공유 드라이브 루트에서 에러 발생 시 다른 방법 시도
                if current_folder_id == 'root' and drive_id:
                    print(f"  ⚠️ 공유 드라이브 루트 조회 재시도 중...")
                    try:
                        # 페이지 크기를 줄여서 재시도
                        items = self.list_folder_contents(
                            current_folder_id, 
                            drive_id=drive_id, 
                            max_results=100,
                            first_page_only=False
                        )
                    except Exception as e2:
                        print(f"  ❌ 재시도 실패: {e2}")
                        return None
                else:
                    return None
            
            # 폴더만 필터링
            folders = [item for item in items if item.get('mimeType') == 'application/vnd.google-apps.folder']
            
            # 이름으로 폴더 찾기 (대소문자 구분 없이, 공백 제거 비교도 시도)
            found_folder = None
            folder_name_normalized = folder_name.strip()
            
            for folder in folders:
                folder_name_clean = folder['name'].strip()
                # 정확한 매칭
                if folder_name_clean == folder_name_normalized:
                    found_folder = folder
                    break
                # 대소문자 무시 매칭
                if folder_name_clean.lower() == folder_name_normalized.lower():
                    found_folder = folder
                    break
                # 공백 제거 후 비교 (예: "논문" == "논 문")
                if folder_name_clean.replace(' ', '') == folder_name_normalized.replace(' ', ''):
                    found_folder = folder
                    break
            
            if not found_folder:
                print(f"  ❌ 폴더를 찾을 수 없습니다: '{folder_name}'")
                print(f"     검색된 폴더 수: {len(folders)}개")
                
                # 유사한 이름의 폴더 찾기 (부분 일치)
                similar_folders = []
                for folder in folders:
                    folder_name_clean = folder['name'].strip()
                    if (folder_name_normalized.lower() in folder_name_clean.lower() or 
                        folder_name_clean.lower() in folder_name_normalized.lower()):
                        similar_folders.append(folder)
                
                if similar_folders:
                    print(f"     유사한 이름의 폴더 ({len(similar_folders)}개):")
                    for folder in similar_folders[:10]:
                        print(f"       📁 {folder['name']}")
                
                if folders:
                    print(f"     현재 위치의 폴더 목록 (최대 20개):")
                    for folder in folders[:20]:
                        print(f"       📁 {folder['name']}")
                    if len(folders) > 20:
                        print(f"       ... 외 {len(folders) - 20}개 폴더")
                else:
                    print(f"     현재 위치에 폴더가 없습니다.")
                return None
            
            current_folder_id = found_folder['id']
            print(f"  ✅ 찾음: {folder_name} (ID: {current_folder_id})")
        
        return current_folder_id
    
    def find_shared_drive_by_name(self, drive_name: str) -> Optional[dict]:
        """공유 드라이브 이름으로 찾기
        
        Args:
            drive_name: 공유 드라이브 이름
        
        Returns:
            공유 드라이브 정보 dict, 없으면 None
        """
        shared_drives = self.list_shared_drives()
        for drive in shared_drives:
            if drive.get('name') == drive_name:
                return drive
        return None
    
    def get_folder_info(self, folder_id: str) -> Optional[dict]:
        """폴더 정보 조회 (공유 드라이브 ID 포함)
        
        Args:
            folder_id: 폴더 ID
        
        Returns:
            폴더 정보 dict (driveId 포함), 없으면 None
        """
        try:
            # 먼저 일반 방식으로 시도
            request_params = {
                'fileId': folder_id,
                'fields': 'id, name, mimeType, driveId, parents'
            }
            folder_info = self.service.files().get(**request_params).execute()
            return folder_info
        except Exception as e:
            # 공유 드라이브일 수 있으므로 supportsAllDrives로 재시도
            try:
                request_params = {
                    'fileId': folder_id,
                    'fields': 'id, name, mimeType, driveId, parents',
                    'supportsAllDrives': True
                }
                folder_info = self.service.files().get(**request_params).execute()
                return folder_info
            except Exception as e2:
                print(f"⚠️ 폴더 정보 조회 실패: {e2}")
                return None
    
    def detect_drive_id_from_folder(self, folder_id: str) -> Optional[str]:
        """폴더 ID로부터 공유 드라이브 ID 자동 감지
        
        Args:
            folder_id: 폴더 ID
        
        Returns:
            공유 드라이브 ID, 없으면 None
        """
        folder_info = self.get_folder_info(folder_id)
        if folder_info:
            drive_id = folder_info.get('driveId')
            return drive_id
        return None
    
    def browse_drive_structure(self, show_details: bool = False):
        """Google Drive 구조 탐색 및 표시"""
        print("\n" + "=" * 60)
        print("📂 Google Drive 구조 탐색")
        print("=" * 60)
        
        # 1. 내 드라이브 루트 폴더
        print("\n📁 내 드라이브 (루트 폴더)")
        print("-" * 60)
        root_items = self.list_folder_contents('root')
        folders = [item for item in root_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
        files = [item for item in root_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
        
        print(f"  폴더: {len(folders)}개")
        if folders:
            for folder in folders[:10]:  # 최대 10개만 표시
                print(f"    📁 {folder['name']} (ID: {folder['id']})")
            if len(folders) > 10:
                print(f"    ... 외 {len(folders) - 10}개 폴더")
        
        print(f"  파일: {len(files)}개")
        if files and show_details:
            for file in files[:5]:  # 최대 5개만 표시
                size = file.get('size', 'N/A')
                if size != 'N/A':
                    size = f"{int(size) / 1024:.1f} KB"
                print(f"    📄 {file['name']} ({size})")
        
        # 2. 공유 문서함
        print("\n📥 공유 문서함")
        print("-" * 60)
        shared_items = self.list_shared_with_me()
        shared_folders = [item for item in shared_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
        shared_files = [item for item in shared_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
        
        print(f"  폴더: {len(shared_folders)}개")
        if shared_folders:
            for folder in shared_folders[:10]:
                owner = folder.get('owners', [{}])[0].get('displayName', 'Unknown') if folder.get('owners') else 'Unknown'
                print(f"    📁 {folder['name']} (ID: {folder['id']}, 소유자: {owner})")
            if len(shared_folders) > 10:
                print(f"    ... 외 {len(shared_folders) - 10}개 폴더")
        
        print(f"  파일: {len(shared_files)}개")
        if shared_files and show_details:
            for file in shared_files[:5]:
                owner = file.get('owners', [{}])[0].get('displayName', 'Unknown') if file.get('owners') else 'Unknown'
                size = file.get('size', 'N/A')
                if size != 'N/A':
                    size = f"{int(size) / 1024:.1f} KB"
                print(f"    📄 {file['name']} ({size}, 소유자: {owner})")
        
        # 3. 별표 표시
        print("\n⭐ 별표 표시된 항목")
        print("-" * 60)
        starred_items = self.list_starred()
        print(f"  총 {len(starred_items)}개")
        if starred_items:
            for item in starred_items[:10]:
                item_type = "📁" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "📄"
                print(f"    {item_type} {item['name']} (ID: {item['id']})")
            if len(starred_items) > 10:
                print(f"    ... 외 {len(starred_items) - 10}개 항목")
        
        # 4. 공유 드라이브 (Shared Drives) - 간단한 리스트만 표시
        print("\n🏢 공유 드라이브 (Shared Drives)")
        print("-" * 60)
        shared_drives = self.list_shared_drives()
        print(f"  총 {len(shared_drives)}개 공유 드라이브")
        if shared_drives:
            for drive in shared_drives:
                drive_name = drive.get('name', 'Unknown')
                drive_id = drive.get('id', 'Unknown')
                print(f"    🏢 {drive_name} (ID: {drive_id})")
                
                # 상세 정보가 요청된 경우에만 루트 폴더만 빠르게 조회
                if show_details:
                    try:
                        # 첫 페이지만 빠르게 조회 (API 호출 최소화)
                        root_items = self.list_folder_contents(
                            'root', 
                            drive_id=drive_id,
                            max_results=20,
                            first_page_only=True
                        )
                        root_folders = [item for item in root_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                        root_files = [item for item in root_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                        
                        if root_folders:
                            print(f"       루트 폴더 (최대 20개):")
                            for folder in root_folders[:10]:
                                print(f"         📁 {folder['name']} (ID: {folder['id']})")
                            if len(root_folders) > 10:
                                print(f"         ... 외 {len(root_folders) - 10}개 폴더")
                    except Exception as e:
                        print(f"       ⚠️ 내용 조회 실패: {e}")
        else:
            print("  ℹ️ 접근 가능한 공유 드라이브가 없습니다.")
        
        print("\n" + "=" * 60)
        return {
            'root_folders': folders,
            'root_files': files,
            'shared_folders': shared_folders,
            'shared_files': shared_files,
            'starred': starred_items,
            'shared_drives': shared_drives
        }
    
    def download_file(self, file_id: str, file_name: str, output_path: Path, drive_id: Optional[str] = None, 
                     show_progress: bool = True, max_retries: int = 3) -> Tuple[bool, str]:
        """단일 파일 다운로드
        
        Args:
            file_id: 파일 ID
            file_name: 파일 이름
            output_path: 출력 경로
            drive_id: 공유 드라이브 ID (공유 드라이브 내 파일 다운로드 시 필요)
            show_progress: 진행 상황 표시 여부
            max_retries: 최대 재시도 횟수
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        file_path = output_path / file_name
        
        # 이미 존재하는 파일 체크 (증분 다운로드)
        if file_path.exists():
            if show_progress:
                with self._progress_lock:
                    self._download_stats['skipped'] += 1
            return True, "이미 존재"
        
        for attempt in range(max_retries):
            try:
                request_params = {'fileId': file_id}
                if drive_id:
                    request_params['supportsAllDrives'] = True
                request = self.service.files().get_media(**request_params)
                
                # 디렉토리 생성
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status and show_progress:
                            progress = int(status.progress() * 100)
                            # 진행 상황은 락으로 보호
                            pass  # 병렬 다운로드 시 개별 진행률은 표시하지 않음
                
                with self._progress_lock:
                    self._download_stats['completed'] += 1
                return True, ""
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue
                else:
                    with self._progress_lock:
                        self._download_stats['failed'] += 1
                    return False, str(e)
        
        return False, "최대 재시도 횟수 초과"
    
    def _collect_all_files(self, folder_id: str, output_path: Path, drive_id: Optional[str] = None, 
                          recursive: bool = True) -> List[Dict]:
        """폴더 내 모든 파일 목록 수집 (재귀적)
        
        Returns:
            파일 정보 리스트: [{'id': file_id, 'name': file_name, 'path': relative_path}, ...]
        """
        files_to_download = []
        
        def collect_recursive(current_folder_id: str, current_path: Path):
            items = self.list_folder_contents(current_folder_id, drive_id=drive_id)
            
            for item in items:
                item_id = item['id']
                item_name = item['name']
                mime_type = item.get('mimeType', '')
                
                # Google Workspace 파일은 건너뜀
                if mime_type.startswith('application/vnd.google-apps.'):
                    continue
                
                # 폴더인 경우 재귀적으로 수집
                if mime_type == 'application/vnd.google-apps.folder':
                    if recursive:
                        subfolder_path = current_path / item_name
                        collect_recursive(item_id, subfolder_path)
                else:
                    # 파일인 경우 목록에 추가
                    relative_path = current_path.relative_to(output_path.parent) if current_path != output_path else Path('.')
                    files_to_download.append({
                        'id': item_id,
                        'name': item_name,
                        'path': current_path,
                        'relative_path': relative_path
                    })
        
        collect_recursive(folder_id, output_path)
        return files_to_download
    
    def download_folder_parallel(self, folder_url_or_id: str, output_dir: str = "./downloads", 
                                recursive: bool = True, drive_id: Optional[str] = None,
                                max_workers: int = 10, batch_size: int = 100) -> bool:
        """폴더 전체 다운로드 (병렬 처리)
        
        Args:
            folder_url_or_id: 폴더 URL 또는 ID
            output_dir: 출력 디렉토리
            recursive: 재귀적 다운로드 여부
            drive_id: 공유 드라이브 ID
            max_workers: 최대 동시 다운로드 수
            batch_size: 배치 크기 (진행 상황 표시 주기)
        
        Returns:
            성공 여부
        """
        # 폴더 ID 추출
        try:
            folder_id = self.extract_folder_id(folder_url_or_id)
        except ValueError as e:
            print(f"❌ 오류: {e}")
            return False
        
        # 폴더 정보 조회
        try:
            request_params = {'fileId': folder_id, 'fields': 'id, name'}
            if drive_id:
                request_params['supportsAllDrives'] = True
            folder_info = self.service.files().get(**request_params).execute()
            folder_name = folder_info.get('name', folder_id)
        except Exception as e:
            print(f"⚠️ 폴더 정보 조회 실패: {e}")
            folder_name = folder_id
        
        # 출력 디렉토리 생성
        output_path = Path(output_dir) / folder_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 병렬 다운로드 시작: {output_path.absolute()}")
        print(f"⚙️ 설정: 동시 다운로드 {max_workers}개, 배치 크기 {batch_size}개")
        
        # 모든 파일 목록 수집
        print(f"\n📋 파일 목록 수집 중...")
        files_to_download = self._collect_all_files(folder_id, output_path, drive_id, recursive)
        total_files = len(files_to_download)
        
        if total_files == 0:
            print(f"  ℹ️ 다운로드할 파일이 없습니다.")
            return True
        
        print(f"✅ 총 {total_files}개 파일 발견")
        
        # 통계 초기화
        self._download_stats = {
            'total': total_files,
            'completed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        start_time = time.time()
        
        # 병렬 다운로드 실행
        def download_single_file(file_info: Dict) -> Tuple[str, bool, str]:
            """단일 파일 다운로드 래퍼"""
            result = self.download_file(
                file_info['id'],
                file_info['name'],
                file_info['path'],
                drive_id=drive_id,
                show_progress=False,
                max_retries=3
            )
            return file_info['name'], result[0], result[1]
        
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 작업 제출
            future_to_file = {
                executor.submit(download_single_file, file_info): file_info 
                for file_info in files_to_download
            }
            
            # 진행 상황 추적
            completed = 0
            for future in as_completed(future_to_file):
                completed += 1
                file_info = future_to_file[future]
                
                try:
                    file_name, success, error_msg = future.result()
                    if not success:
                        failed_files.append((file_name, error_msg))
                    
                    # 배치 단위로 진행 상황 표시
                    if completed % batch_size == 0 or completed == total_files:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        remaining = (total_files - completed) / rate if rate > 0 else 0
                        
                        with self._progress_lock:
                            stats = self._download_stats.copy()
                        
                        print(f"\n📊 진행 상황: {completed}/{total_files} ({completed*100//total_files}%)")
                        print(f"   ✅ 완료: {stats['completed']}개")
                        print(f"   ⏭️ 건너뜀: {stats['skipped']}개")
                        print(f"   ❌ 실패: {stats['failed']}개")
                        print(f"   ⏱️ 경과 시간: {elapsed:.1f}초")
                        print(f"   📈 속도: {rate:.1f} 파일/초")
                        print(f"   ⏳ 예상 남은 시간: {remaining:.1f}초")
                        
                except Exception as e:
                    file_name = file_info.get('name', 'Unknown')
                    failed_files.append((file_name, str(e)))
                    with self._progress_lock:
                        self._download_stats['failed'] += 1
        
        # 최종 결과
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ 다운로드 완료!")
        print(f"   총 파일: {total_files}개")
        print(f"   완료: {self._download_stats['completed']}개")
        print(f"   건너뜀: {self._download_stats['skipped']}개")
        print(f"   실패: {self._download_stats['failed']}개")
        print(f"   총 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
        print(f"   평균 속도: {total_files/elapsed:.1f} 파일/초")
        
        if failed_files:
            print(f"\n⚠️ 실패한 파일 ({len(failed_files)}개):")
            for file_name, error in failed_files[:10]:
                print(f"   - {file_name}: {error}")
            if len(failed_files) > 10:
                print(f"   ... 외 {len(failed_files) - 10}개")
        
        return self._download_stats['failed'] == 0
    
    def download_folder(self, folder_url_or_id: str, output_dir: str = "./downloads", recursive: bool = True, drive_id: Optional[str] = None):
        """폴더 전체 다운로드 (재귀적)
        
        Args:
            folder_url_or_id: 폴더 URL 또는 ID
            output_dir: 출력 디렉토리
            recursive: 재귀적 다운로드 여부
            drive_id: 공유 드라이브 ID (공유 드라이브 내 폴더 다운로드 시 필요)
        """
        # 폴더 ID 추출
        try:
            folder_id = self.extract_folder_id(folder_url_or_id)
            print(f"📁 폴더 ID: {folder_id}")
        except ValueError as e:
            print(f"❌ 오류: {e}")
            return False
        
        # 폴더 정보 조회
        try:
            request_params = {'fileId': folder_id, 'fields': 'id, name'}
            if drive_id:
                request_params['supportsAllDrives'] = True
            folder_info = self.service.files().get(**request_params).execute()
            folder_name = folder_info.get('name', folder_id)
            print(f"📂 폴더 이름: {folder_name}")
        except Exception as e:
            print(f"⚠️ 폴더 정보 조회 실패: {e}")
            folder_name = folder_id
        
        # 출력 디렉토리 생성
        output_path = Path(output_dir) / folder_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 다운로드 시작: {output_path.absolute()}")
        
        # 폴더 내용 다운로드
        return self._download_folder_recursive(folder_id, output_path, recursive, drive_id=drive_id)
    
    def _download_folder_recursive(self, folder_id: str, output_path: Path, recursive: bool = True, drive_id: Optional[str] = None):
        """재귀적으로 폴더 다운로드
        
        Args:
            folder_id: 폴더 ID
            output_path: 출력 경로
            recursive: 재귀적 다운로드 여부
            drive_id: 공유 드라이브 ID
        """
        items = self.list_folder_contents(folder_id, drive_id=drive_id)
        
        if not items:
            print(f"  ℹ️ 폴더가 비어있습니다: {output_path.name}")
            return True
        
        print(f"\n📋 항목 수: {len(items)}개")
        
        success_count = 0
        for item in items:
            item_id = item['id']
            item_name = item['name']
            mime_type = item.get('mimeType', '')
            
            # Google Workspace 파일 (Docs, Sheets, Slides 등)은 export 필요
            if mime_type.startswith('application/vnd.google-apps.'):
                print(f"  ⚠️ Google Workspace 파일은 직접 다운로드 불가: {item_name}")
                print(f"     (PDF 또는 다른 형식으로 export 필요)")
                continue
            
            # 폴더인 경우 재귀적으로 다운로드
            if mime_type == 'application/vnd.google-apps.folder':
                if recursive:
                    subfolder_path = output_path / item_name
                    subfolder_path.mkdir(exist_ok=True)
                    if self._download_folder_recursive(item_id, subfolder_path, recursive, drive_id=drive_id):
                        success_count += 1
                else:
                    print(f"  📁 폴더 건너뜀 (재귀 비활성화): {item_name}")
            else:
                # 파일 다운로드
                if self.download_file(item_id, item_name, output_path, drive_id=drive_id):
                    success_count += 1
        
        print(f"\n✅ 다운로드 완료: {success_count}/{len(items)}개 항목")
        return success_count > 0
    
    def list_path_contents(self, path: str, drive_name: Optional[str] = None) -> Optional[List[dict]]:
        """경로의 내용만 조회 (다운로드하지 않음)
        
        Args:
            path: 경로 문자열 (예: "플랫폼개발팀/논문" 또는 "논문/Menin")
            drive_name: 공유 드라이브 이름 (공유 드라이브 내 경로인 경우, None이면 경로에서 자동 감지)
        
        Returns:
            폴더 내용 리스트, 실패 시 None
        """
        drive_id = None
        actual_path = path
        
        # 공유 드라이브 이름이 지정되지 않았으면 경로에서 자동 감지 시도
        if not drive_name:
            path_parts = [p.strip() for p in path.replace('\\', '/').split('/') if p.strip()]
            if path_parts:
                # 첫 번째 경로 부분이 공유 드라이브 이름인지 확인
                potential_drive_name = path_parts[0]
                drive = self.find_shared_drive_by_name(potential_drive_name)
                if drive:
                    print(f"🏢 공유 드라이브 자동 감지: {potential_drive_name}")
                    drive_name = potential_drive_name
                    # 경로에서 공유 드라이브 이름 제거
                    actual_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ''
        
        # 공유 드라이브가 지정된 경우
        if drive_name:
            drive = self.find_shared_drive_by_name(drive_name)
            if not drive:
                print(f"❌ 공유 드라이브를 찾을 수 없습니다: {drive_name}")
                return None
            drive_id = drive.get('id')
            start_folder_id = 'root'
        else:
            start_folder_id = 'root'
        
        # 경로가 비어있으면 루트 조회
        if not actual_path or actual_path.strip() == '':
            return self.list_folder_contents('root', drive_id=drive_id)
        
        # 경로 탐색
        folder_id = self.find_folder_by_path(actual_path, drive_id=drive_id, start_folder_id=start_folder_id)
        
        if not folder_id:
            return None
        
        # 폴더 내용 조회
        return self.list_folder_contents(folder_id, drive_id=drive_id)
    
    def download_by_path(self, path: str, output_dir: str = "./downloads", drive_name: Optional[str] = None, recursive: bool = True) -> bool:
        """경로를 지정하여 폴더 다운로드
        
        Args:
            path: 경로 문자열 (예: "플랫폼개발팀/논문/Menin" 또는 "논문/Menin")
            output_dir: 출력 디렉토리
            drive_name: 공유 드라이브 이름 (공유 드라이브 내 경로인 경우, None이면 경로에서 자동 감지)
            recursive: 재귀적 다운로드 여부
        
        Returns:
            성공 여부
        """
        drive_id = None
        actual_path = path
        
        # 공유 드라이브 이름이 지정되지 않았으면 경로에서 자동 감지 시도
        if not drive_name:
            path_parts = [p.strip() for p in path.replace('\\', '/').split('/') if p.strip()]
            if path_parts:
                # 첫 번째 경로 부분이 공유 드라이브 이름인지 확인
                potential_drive_name = path_parts[0]
                drive = self.find_shared_drive_by_name(potential_drive_name)
                if drive:
                    print(f"🏢 공유 드라이브 자동 감지: {potential_drive_name}")
                    drive_name = potential_drive_name
                    # 경로에서 공유 드라이브 이름 제거
                    actual_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ''
        
        # 공유 드라이브가 지정된 경우
        if drive_name:
            print(f"🏢 공유 드라이브 찾는 중: {drive_name}")
            drive = self.find_shared_drive_by_name(drive_name)
            if not drive:
                print(f"❌ 공유 드라이브를 찾을 수 없습니다: {drive_name}")
                print("\n접근 가능한 공유 드라이브 목록:")
                shared_drives = self.list_shared_drives()
                for d in shared_drives:
                    print(f"  - {d.get('name')}")
                return False
            drive_id = drive.get('id')
            print(f"✅ 공유 드라이브 찾음: {drive_name} (ID: {drive_id})")
            start_folder_id = 'root'
        else:
            # 내 드라이브에서 시작
            start_folder_id = 'root'
        
        # 경로가 비어있으면 루트 다운로드
        if not actual_path or actual_path.strip() == '':
            print(f"\n📥 공유 드라이브 루트 다운로드 중...")
            return self.download_folder('root', output_dir, recursive=recursive, drive_id=drive_id)
        
        # 경로 탐색
        print(f"\n🔍 경로 탐색 중: {actual_path}")
        folder_id = self.find_folder_by_path(actual_path, drive_id=drive_id, start_folder_id=start_folder_id)
        
        if not folder_id:
            print(f"❌ 경로를 찾을 수 없습니다: {actual_path}")
            return False
        
        # 다운로드 실행
        return self.download_folder(folder_id, output_dir, recursive=recursive, drive_id=drive_id)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Google Drive API를 사용하여 폴더 및 파일을 다운로드하거나 Drive 구조를 탐색합니다",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # Drive 구조 탐색
  %(prog)s --browse
  
  # 특정 폴더 다운로드
  %(prog)s "1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" -o ./downloads
  
  # 공유 문서함만 조회
  %(prog)s --list-shared
        """
    )
    parser.add_argument(
        "folder_url",
        nargs='?',
        help="Google Drive 폴더 URL 또는 폴더 ID (선택사항)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./downloads",
        help="다운로드할 디렉토리 경로 (기본값: ./downloads)"
    )
    parser.add_argument(
        "--credentials",
        help="OAuth 2.0 클라이언트 인증 정보 JSON 파일 경로 (기본값: credentials.json)"
    )
    parser.add_argument(
        "--token",
        help="토큰 파일 경로 (기본값: token.json)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="하위 폴더를 재귀적으로 다운로드하지 않음"
    )
    parser.add_argument(
        "--browse",
        action="store_true",
        help="Google Drive 구조 탐색 (내 드라이브, 공유 문서함 등)"
    )
    parser.add_argument(
        "--list-shared",
        action="store_true",
        help="공유 문서함 목록만 조회"
    )
    parser.add_argument(
        "--list-starred",
        action="store_true",
        help="별표 표시된 항목만 조회"
    )
    parser.add_argument(
        "--list-root",
        action="store_true",
        help="내 드라이브 루트 폴더 목록만 조회"
    )
    parser.add_argument(
        "--list-shared-drives",
        action="store_true",
        help="공유 드라이브 목록만 조회"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="상세 정보 표시 (파일 크기, 소유자 등)"
    )
    parser.add_argument(
        "--path",
        help="경로를 지정하여 다운로드 (예: '플랫폼개발팀/논문')"
    )
    parser.add_argument(
        "--drive",
        help="공유 드라이브 이름 (--path와 함께 사용)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="경로의 내용만 조회 (다운로드하지 않음)"
    )
    parser.add_argument(
        "--folder-id",
        help="폴더 ID를 직접 지정 (경로 탐색 없이 바로 사용, 공유 드라이브의 경우 --drive-id와 함께 사용)"
    )
    parser.add_argument(
        "--drive-id",
        help="공유 드라이브 ID (--folder-id와 함께 사용하여 공유 드라이브 내 폴더 접근)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="병렬 다운로드 사용 (대량 파일에 권장)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="병렬 다운로드 최대 동시 작업 수 (기본값: 10)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="진행 상황 표시 배치 크기 (기본값: 100)"
    )
    
    args = parser.parse_args()
    
    try:
        downloader = GoogleDriveDownloader(
            credentials_path=args.credentials,
            token_path=args.token
        )
        
        # 탐색 모드
        if args.browse:
            downloader.browse_drive_structure(show_details=args.details)
            sys.exit(0)
        
        if args.list_shared:
            print("\n📥 공유 문서함")
            print("=" * 60)
            shared_items = downloader.list_shared_with_me()
            for item in shared_items:
                item_type = "📁" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "📄"
                owner = item.get('owners', [{}])[0].get('displayName', 'Unknown') if item.get('owners') else 'Unknown'
                print(f"{item_type} {item['name']} (ID: {item['id']}, 소유자: {owner})")
            print(f"\n총 {len(shared_items)}개 항목")
            sys.exit(0)
        
        if args.list_starred:
            print("\n⭐ 별표 표시된 항목")
            print("=" * 60)
            starred_items = downloader.list_starred()
            for item in starred_items:
                item_type = "📁" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "📄"
                print(f"{item_type} {item['name']} (ID: {item['id']})")
            print(f"\n총 {len(starred_items)}개 항목")
            sys.exit(0)
        
        if args.list_root:
            print("\n📁 내 드라이브 루트 폴더")
            print("=" * 60)
            root_items = downloader.list_folder_contents('root')
            for item in root_items:
                item_type = "📁" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "📄"
                print(f"{item_type} {item['name']} (ID: {item['id']})")
            print(f"\n총 {len(root_items)}개 항목")
            sys.exit(0)
        
        if args.list_shared_drives:
            print("\n🏢 공유 드라이브 (Shared Drives)")
            print("=" * 60)
            shared_drives = downloader.list_shared_drives()
            if shared_drives:
                for drive in shared_drives:
                    drive_name = drive.get('name', 'Unknown')
                    drive_id = drive.get('id', 'Unknown')
                    print(f"🏢 {drive_name} (ID: {drive_id})")
                    
                    # 루트 폴더만 빠르게 조회 (첫 페이지만, 최대 20개)
                    try:
                        # first_page_only=True로 첫 페이지만 빠르게 조회
                        root_items = downloader.list_folder_contents(
                            'root', 
                            drive_id=drive_id, 
                            max_results=20,
                            first_page_only=True
                        )
                        folders = [item for item in root_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                        files = [item for item in root_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                        
                        if folders:
                            print(f"   루트 폴더 (최대 20개 표시):")
                            for folder in folders[:10]:
                                print(f"   📁 {folder['name']} (ID: {folder['id']})")
                            if len(folders) > 10:
                                print(f"   ... 외 {len(folders) - 10}개 폴더")
                        if files:
                            print(f"   파일: {len(files)}개 (표시 생략)")
                    except Exception as e:
                        print(f"   ⚠️ 내용 조회 실패: {e}")
            else:
                print("접근 가능한 공유 드라이브가 없습니다.")
            print(f"\n총 {len(shared_drives)}개 공유 드라이브")
            print("\n💡 특정 경로를 탐색하려면:")
            print("   %s --drive '드라이브이름' --path '경로' --list" % sys.argv[0])
            sys.exit(0)
        
        # 경로 기반 모드
        if args.path:
            # 리스트 모드 (다운로드하지 않음)
            if args.list:
                print(f"\n📋 경로 내용 조회: {args.path}")
                if args.drive:
                    print(f"🏢 공유 드라이브: {args.drive}")
                print("=" * 60)
                
                items = downloader.list_path_contents(args.path, drive_name=args.drive)
                if items is None:
                    print("❌ 경로를 찾을 수 없거나 접근할 수 없습니다.")
                    sys.exit(1)
                
                folders = [item for item in items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                files = [item for item in items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                
                print(f"\n📁 폴더: {len(folders)}개")
                for folder in folders:
                    print(f"  📁 {folder['name']} (ID: {folder['id']})")
                
                print(f"\n📄 파일: {len(files)}개")
                for file in files:
                    size = file.get('size', 'N/A')
                    if size != 'N/A':
                        size = f"{int(size) / 1024 / 1024:.2f} MB" if int(size) > 1024*1024 else f"{int(size) / 1024:.1f} KB"
                    else:
                        size = "N/A"
                    print(f"  📄 {file['name']} ({size})")
                
                print(f"\n총 {len(items)}개 항목")
                sys.exit(0)
            else:
                # 다운로드 모드
                if args.parallel:
                    # 경로에서 폴더 ID 찾기
                    drive_id = None
                    if args.drive:
                        drive = downloader.find_shared_drive_by_name(args.drive)
                        if drive:
                            drive_id = drive.get('id')
                    
                    folder_id = downloader.find_folder_by_path(
                        args.path, 
                        drive_id=drive_id, 
                        start_folder_id='root'
                    )
                    
                    if folder_id:
                        success = downloader.download_folder_parallel(
                            folder_id,
                            args.output,
                            recursive=not args.no_recursive,
                            drive_id=drive_id,
                            max_workers=args.max_workers,
                            batch_size=args.batch_size
                        )
                    else:
                        print("❌ 경로를 찾을 수 없습니다.")
                        sys.exit(1)
                else:
                    success = downloader.download_by_path(
                        path=args.path,
                        output_dir=args.output,
                        drive_name=args.drive,
                        recursive=not args.no_recursive
                    )
                sys.exit(0 if success else 1)
        
        # 폴더 ID 직접 지정 모드 (가장 빠름)
        if args.folder_id:
            folder_id = downloader.extract_folder_id(args.folder_id)
            
            # 공유 드라이브 ID 자동 감지 (지정되지 않은 경우)
            drive_id = args.drive_id
            if not drive_id:
                print(f"🔍 폴더 정보 확인 중...")
                folder_info = downloader.get_folder_info(folder_id)
                if folder_info:
                    detected_drive_id = folder_info.get('driveId')
                    folder_name = folder_info.get('name', folder_id)
                    if detected_drive_id:
                        drive_id = detected_drive_id
                        print(f"✅ 공유 드라이브 자동 감지: {drive_id}")
                        print(f"📁 폴더 이름: {folder_name}")
                    else:
                        print(f"📁 폴더 이름: {folder_name} (내 드라이브)")
                else:
                    print(f"⚠️ 폴더 정보를 가져올 수 없습니다. 공유 드라이브일 수 있습니다.")
            
            if args.list:
                # 리스트 모드
                print(f"\n📋 폴더 내용 조회 (ID: {folder_id})")
                if drive_id:
                    print(f"🏢 공유 드라이브 ID: {drive_id}")
                print("=" * 60)
                
                try:
                    items = downloader.list_folder_contents(folder_id, drive_id=drive_id)
                    folders = [item for item in items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                    files = [item for item in items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                    
                    print(f"\n📁 폴더: {len(folders)}개")
                    for folder in folders:
                        print(f"  📁 {folder['name']} (ID: {folder['id']})")
                    
                    print(f"\n📄 파일: {len(files)}개")
                    for file in files:
                        size = file.get('size', 'N/A')
                        if size != 'N/A':
                            size = f"{int(size) / 1024 / 1024:.2f} MB" if int(size) > 1024*1024 else f"{int(size) / 1024:.1f} KB"
                        else:
                            size = "N/A"
                        print(f"  📄 {file['name']} ({size})")
                    
                    print(f"\n총 {len(items)}개 항목")
                    sys.exit(0)
                except Exception as e:
                    print(f"❌ 폴더 조회 실패: {e}")
                    print(f"\n💡 공유 드라이브인 경우 --drive-id 옵션을 추가해보세요:")
                    print(f"   %s --folder-id '{folder_id}' --drive-id '드라이브ID' --list" % sys.argv[0])
                    sys.exit(1)
            else:
                # 다운로드 모드
                print(f"📥 폴더 ID로 다운로드 시작: {folder_id}")
                if drive_id:
                    print(f"🏢 공유 드라이브 ID: {drive_id}")
                
                # 병렬 다운로드 옵션
                if args.parallel:
                    success = downloader.download_folder_parallel(
                        folder_id,
                        args.output,
                        recursive=not args.no_recursive,
                        drive_id=drive_id,
                        max_workers=args.max_workers,
                        batch_size=args.batch_size
                    )
                else:
                    success = downloader.download_folder(
                        folder_id,
                        args.output,
                        recursive=not args.no_recursive,
                        drive_id=drive_id
                    )
                sys.exit(0 if success else 1)
        
        # 다운로드 모드 (folder_url이 제공된 경우)
        if args.folder_url:
            if args.parallel:
                success = downloader.download_folder_parallel(
                    args.folder_url,
                    args.output,
                    recursive=not args.no_recursive,
                    drive_id=None,
                    max_workers=args.max_workers,
                    batch_size=args.batch_size
                )
            else:
                success = downloader.download_folder(
                    args.folder_url,
                    args.output,
                    recursive=not args.no_recursive
                )
            sys.exit(0 if success else 1)
        else:
            # 인자가 없으면 구조 탐색
            print("ℹ️ 폴더 URL/ID 또는 경로가 제공되지 않았습니다. Drive 구조를 탐색합니다.\n")
            downloader.browse_drive_structure(show_details=args.details)
            print("\n💡 사용 방법:")
            print("   1. 폴더 ID로 다운로드 (가장 빠름):")
            print("      %s --folder-id '1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU' -o ./downloads" % sys.argv[0])
            print("   2. 병렬 다운로드 (대량 파일 권장):")
            print("      %s --folder-id '폴더ID' --parallel --max-workers 10 -o ./downloads" % sys.argv[0])
            print("   3. 경로로 다운로드:")
            print("      %s --path '플랫폼개발팀/논문' -o ./downloads" % sys.argv[0])
            print("   4. 공유 드라이브 경로:")
            print("      %s --drive '드라이브이름' --path '논문' -o ./downloads" % sys.argv[0])
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

