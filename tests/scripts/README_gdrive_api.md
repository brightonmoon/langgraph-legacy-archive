# Google Drive API를 사용한 폴더 다운로드 가이드

## 개요

`download_gdrive_api.py`는 Google Drive API를 사용하여 폴더 및 파일을 다운로드하는 스크립트입니다.
gdown과 달리 공식 API를 사용하므로 더 많은 제어와 기능을 제공합니다.

## 장점

- ✅ **공식 API**: Google의 공식 Drive API 사용
- ✅ **제한 없음**: 파일 수 제한 없이 다운로드 가능
- ✅ **재귀 다운로드**: 하위 폴더까지 자동으로 다운로드
- ✅ **진행 상황 표시**: 다운로드 진행률 표시
- ✅ **권한 관리**: OAuth 2.0을 통한 안전한 인증
- ✅ **Google Workspace 파일**: Docs, Sheets, Slides 등도 처리 가능 (export 필요)

## 설치

### 1. 필요한 패키지 설치

```bash
cd /home/doyamoon/agentic_ai
source .venv/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

또는 uv를 사용하는 경우:

```bash
uv pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. Google Cloud Console 설정

#### 2.1 프로젝트 생성 및 API 활성화

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" > "라이브러리"로 이동
4. "Google Drive API" 검색 후 활성화

#### 2.2 OAuth 2.0 클라이언트 ID 생성

1. "API 및 서비스" > "사용자 인증 정보"로 이동
2. "사용자 인증 정보 만들기" 클릭
3. "OAuth 클라이언트 ID" 선택
4. 애플리케이션 유형: "데스크톱 앱" 선택
5. 이름 입력 후 "만들기" 클릭
6. 클라이언트 ID와 클라이언트 비밀 생성됨
7. **JSON 다운로드** 버튼 클릭하여 `credentials.json` 파일 저장

#### 2.3 credentials.json 파일 배치

다운로드한 `credentials.json` 파일을 다음 중 하나의 위치에 배치:

- 스크립트와 같은 디렉토리 (`tests/scripts/credentials.json`)
- 또는 환경변수 `GOOGLE_DRIVE_CREDENTIALS_PATH`로 경로 지정

## 사용 방법

### 기본 사용법

```bash
cd /home/doyamoon/agentic_ai
source .venv/bin/activate
uv run tests/scripts/download_gdrive_api.py "https://drive.google.com/drive/u/0/folders/1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" -o ./downloads
```

### 옵션

- `-o, --output`: 다운로드할 디렉토리 경로 (기본값: `./downloads`)
- `--credentials`: credentials.json 파일 경로 (기본값: `credentials.json`)
- `--token`: 토큰 파일 경로 (기본값: `token.json`)
- `--no-recursive`: 하위 폴더를 재귀적으로 다운로드하지 않음

### 예제

#### 1. 기본 다운로드 (재귀적)

```bash
uv run tests/scripts/download_gdrive_api.py "1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" -o ./my_downloads
```

#### 2. 하위 폴더 제외

```bash
uv run tests/scripts/download_gdrive_api.py "1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" --no-recursive
```

#### 3. 커스텀 credentials 파일 사용

```bash
uv run tests/scripts/download_gdrive_api.py "1M3czF1-ZtojTB9zeqpWwlHcaEvgyaMwU" --credentials /path/to/my_credentials.json
```

## 첫 실행 시 인증 과정

1. 스크립트 실행 시 브라우저가 자동으로 열림
2. Google 계정으로 로그인
3. 권한 승인 (Google Drive 읽기 권한)
4. 인증 완료 후 `token.json` 파일이 생성됨
5. 이후 실행 시 자동으로 토큰 사용 (만료 시 자동 갱신)

## 주의사항

### Google Workspace 파일

Google Docs, Sheets, Slides 등은 직접 다운로드할 수 없습니다.
이러한 파일들은 PDF나 다른 형식으로 export해야 합니다.

스크립트는 이러한 파일을 감지하고 경고 메시지를 표시합니다.

### 폴더 공유 설정

- 폴더가 공유되어 있어야 합니다
- "링크가 있는 모든 사용자" 또는 특정 사용자에게 공유되어 있어야 합니다
- 본인의 폴더인 경우 자동으로 접근 가능합니다

### 토큰 보안

- `token.json` 파일에는 인증 토큰이 저장됩니다
- 이 파일을 공유하거나 Git에 커밋하지 마세요
- `.gitignore`에 추가하는 것을 권장합니다

## gdown vs Google Drive API 비교

| 기능 | gdown | Google Drive API |
|------|-------|------------------|
| 설치 | 간단 (`pip install gdown`) | 패키지 3개 필요 |
| 설정 | 없음 | OAuth 2.0 설정 필요 |
| 파일 수 제한 | 50개 (기본) | 제한 없음 |
| 재귀 다운로드 | 지원 | 지원 |
| 진행률 표시 | 기본 | 상세 |
| Google Workspace | 제한적 | 지원 (export 필요) |
| 권한 관리 | 공유 링크 필요 | OAuth 2.0 |

## 문제 해결

### "인증 정보 파일을 찾을 수 없습니다"

- `credentials.json` 파일이 올바른 위치에 있는지 확인
- `--credentials` 옵션으로 경로 지정

### "토큰 갱신 실패"

- `token.json` 파일 삭제 후 재인증
- `credentials.json`이 올바른지 확인

### "권한이 없습니다"

- 폴더 공유 설정 확인
- OAuth 2.0 클라이언트 ID가 올바른지 확인
- Google Drive API가 활성화되어 있는지 확인

## 참고 자료

- [Google Drive API 문서](https://developers.google.com/drive/api/v3/about-sdk)
- [OAuth 2.0 설정 가이드](https://developers.google.com/identity/protocols/oauth2)
- [Python 클라이언트 라이브러리](https://github.com/googleapis/google-api-python-client)


