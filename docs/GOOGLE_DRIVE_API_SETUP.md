# Google Drive API 설정 가이드

## ✅ 완료된 작업

1. **패키지 설치 완료**
   - `google-api-python-client`
   - `google-auth-httplib2`
   - `google-auth-oauthlib`

## 📋 추가로 해야 할 작업

### 1. Google Cloud Console 설정

#### 1.1 프로젝트 생성 및 API 활성화

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
   - 프로젝트 이름 예: "My Drive API Project"
3. **API 및 서비스** > **라이브러리**로 이동
4. 검색창에 "Google Drive API" 입력
5. **Google Drive API** 선택 후 **사용 설정** 클릭

#### 1.2 OAuth 2.0 클라이언트 ID 생성

1. **API 및 서비스** > **사용자 인증 정보**로 이동
2. 상단의 **+ 사용자 인증 정보 만들기** 클릭
3. **OAuth 클라이언트 ID** 선택
4. **동의 화면 구성**이 필요하면 먼저 완료
   - 사용자 유형: **외부** 선택 (개인 Google 계정 사용 시)
   - 앱 이름, 사용자 지원 이메일 등 입력
   - 범위: 기본값 사용 또는 "https://www.googleapis.com/auth/drive.readonly" 추가
   - 테스트 사용자: 본인 이메일 추가
5. **OAuth 클라이언트 ID** 다시 선택
6. 애플리케이션 유형: **데스크톱 앱** 선택
7. 이름 입력 (예: "Drive API Desktop Client")
8. **만들기** 클릭
9. **JSON 다운로드** 버튼 클릭하여 `credentials.json` 파일 저장

### 2. credentials.json 파일 배치

다운로드한 `credentials.json` 파일을 다음 위치 중 하나에 저장:

**권장 위치:**
```bash
/home/doyamoon/agentic_ai/tests/scripts/credentials.json
```

**또는 프로젝트 루트:**
```bash
/home/doyamoon/agentic_ai/credentials.json
```

### 3. 환경 변수 설정 (선택사항)

`.env` 파일이 있다면 다음 변수를 추가할 수 있습니다:

```bash
# Google Drive API 설정
GOOGLE_DRIVE_CREDENTIALS_PATH=tests/scripts/credentials.json
GOOGLE_DRIVE_TOKEN_PATH=tests/scripts/token.json
```

### 4. 설정 확인

설정 상태를 확인하려면:

```bash
cd /home/doyamoon/agentic_ai
source .venv/bin/activate
uv run tests/scripts/test_gdrive_setup.py
```

### 5. 첫 인증 실행

첫 실행 시 브라우저가 자동으로 열리고 Google 계정 인증을 진행합니다:

```bash
# 테스트용 (폴더 ID 또는 URL 필요)
uv run tests/scripts/download_gdrive_api.py <폴더_ID_또는_URL> -o ./downloads

# 예시
uv run tests/scripts/download_gdrive_api.py "1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" -o ./downloads
```

**인증 과정:**
1. 스크립트 실행 시 브라우저가 자동으로 열림
2. Google 계정 선택 및 로그인
3. 권한 승인 화면에서 "허용" 클릭
4. 인증 완료 후 `token.json` 파일이 자동 생성됨
5. 이후 실행 시 자동으로 토큰 사용 (만료 시 자동 갱신)

## 🔒 보안 주의사항

### Git에 커밋하지 말아야 할 파일들

다음 파일들은 `.gitignore`에 추가되어 있어야 합니다:

```
credentials.json
token.json
*.json (credentials, token 관련)
```

### credentials.json 보안

- 이 파일에는 OAuth 2.0 클라이언트 ID와 비밀키가 포함되어 있습니다
- 절대 공개 저장소에 업로드하지 마세요
- 필요시 Google Cloud Console에서 클라이언트 ID를 삭제하고 재생성할 수 있습니다

### token.json 보안

- 이 파일에는 사용자의 인증 토큰이 저장됩니다
- 다른 사람과 공유하지 마세요
- 토큰이 유출되면 Google Cloud Console에서 클라이언트 ID를 삭제하세요

## 🧪 테스트 방법

### 1. 설정 확인

```bash
uv run tests/scripts/test_gdrive_setup.py
```

### 2. 간단한 API 테스트

```bash
# 폴더 다운로드 테스트
uv run tests/scripts/download_gdrive_api.py <폴더_ID> -o ./test_downloads
```

### 3. Python 코드에서 직접 사용

```python
from tests.scripts.download_gdrive_api import GoogleDriveDownloader

# 다운로더 생성 (자동 인증)
downloader = GoogleDriveDownloader()

# 폴더 다운로드
downloader.download_folder(
    folder_url_or_id="<폴더_ID_또는_URL>",
    output_dir="./downloads",
    recursive=True
)
```

## ❓ 문제 해결

### "인증 정보 파일을 찾을 수 없습니다"

- `credentials.json` 파일이 올바른 위치에 있는지 확인
- `--credentials` 옵션으로 경로 지정:
  ```bash
  uv run tests/scripts/download_gdrive_api.py <폴더_ID> --credentials /path/to/credentials.json
  ```

### "토큰 갱신 실패"

- `token.json` 파일 삭제 후 재인증:
  ```bash
  rm token.json  # 또는 tests/scripts/token.json
  # 스크립트 다시 실행
  ```

### "권한이 없습니다"

- Google Cloud Console에서 Google Drive API가 활성화되어 있는지 확인
- OAuth 동의 화면이 올바르게 구성되어 있는지 확인
- 폴더가 공유되어 있는지 확인 (본인 폴더는 자동 접근 가능)

### "API가 활성화되지 않았습니다"

- Google Cloud Console > API 및 서비스 > 라이브러리에서 "Google Drive API" 검색
- "사용 설정" 버튼 클릭

## 📚 참고 자료

- [Google Drive API 문서](https://developers.google.com/drive/api/v3/about-sdk)
- [OAuth 2.0 설정 가이드](https://developers.google.com/identity/protocols/oauth2)
- [Python 클라이언트 라이브러리](https://github.com/googleapis/google-api-python-client)
- [기존 README](tests/scripts/README_gdrive_api.md)

## ✅ 체크리스트

설정 완료를 확인하기 위한 체크리스트:

- [ ] 패키지 설치 완료 (이미 완료됨)
- [ ] Google Cloud Console에서 프로젝트 생성
- [ ] Google Drive API 활성화
- [ ] OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
- [ ] credentials.json 파일 다운로드
- [ ] credentials.json 파일을 올바른 위치에 배치
- [ ] 설정 확인 스크립트 실행 (`test_gdrive_setup.py`)
- [ ] 첫 인증 실행 및 token.json 생성
- [ ] 테스트 다운로드 실행


