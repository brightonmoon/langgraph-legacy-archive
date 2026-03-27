# MinerU LMDeploy 사용 가이드

이 문서는 MinerU를 사용하여 PDF를 Markdown으로 변환할 때 LMDeploy 백엔드를 활용하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [사전 요구사항](#사전-요구사항)
3. [설치](#설치)
4. [기본 사용법](#기본-사용법)
5. [고급 설정](#고급-설정)
6. [Python 코드 사용법](#python-코드-사용법)
7. [문제 해결](#문제-해결)
8. [성능 비교](#성능-비교)

---

## 개요

MinerU는 복잡한 PDF 문서를 고품질 Markdown으로 변환하는 도구입니다. LMDeploy 백엔드를 사용하면 Vision-Language Model(VLM)을 효율적으로 활용하여 더 정확한 문서 파싱이 가능합니다.

### 백엔드 비교

| 백엔드 | 설명 | 장점 | 단점 |
|--------|------|------|------|
| `pipeline` | 기본 파이프라인 백엔드 | 안정적, 다양한 옵션 | 상대적으로 느림 |
| `vlm-lmdeploy-engine` | LMDeploy 기반 VLM 엔진 | 빠른 추론, 효율적 메모리 사용 | 초기 설정 필요 |
| `vlm-vllm-engine` | vLLM 기반 VLM 엔진 | 매우 빠른 추론 | 더 많은 메모리 필요 |

---

## 사전 요구사항

### 시스템 요구사항

- **OS**: Linux (WSL2 포함), macOS, Windows (WSL2 권장)
- **Python**: 3.10 이상 (Windows + LMDeploy는 3.10-3.12만 지원)
- **GPU**: CUDA 지원 GPU (권장, CPU도 가능하지만 느림)
- **메모리**: 최소 8GB RAM (GPU 메모리 별도)

### 필수 소프트웨어

1. **CUDA Toolkit** (GPU 사용 시)
   ```bash
   # CUDA 버전 확인
   nvidia-smi
   ```

2. **Python 가상환경** (권장)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # 또는
   .venv\Scripts\activate  # Windows
   ```

---

## 설치

### 1. MinerU 설치 (LMDeploy 포함)

```bash
# pip를 사용한 설치
pip install --upgrade pip
pip install uv
uv pip install -U "mineru[core,lmdeploy]"
```

또는 `pyproject.toml`에 이미 포함되어 있다면:

```bash
uv pip install -e ".[core,lmdeploy]"
```

### 2. 설치 확인

```bash
# MinerU 버전 확인
mineru --version

# LMDeploy 백엔드 사용 가능 여부 확인
python -c "import mineru; print('MinerU 설치 완료')"
```

---

## 기본 사용법

### 명령줄 인터페이스 (CLI)

#### 기본 명령어 구조

```bash
mineru -p <PDF_파일_경로> -o <출력_디렉토리> -b vlm-lmdeploy-engine
```

#### 실제 사용 예시

```bash
# 단일 PDF 변환
mineru -p "document.pdf" -o "./output" -b vlm-lmdeploy-engine

# 전체 디렉토리 변환
mineru -p "./pdfs/" -o "./output" -b vlm-lmdeploy-engine

# 특정 페이지 범위만 변환 (0-based 인덱스)
mineru -p "document.pdf" -o "./output" -b vlm-lmdeploy-engine -s 0 -e 2
```

#### 배치 처리 시 주의사항

전체 디렉토리를 변환할 때는 다음 사항을 주의하세요:

**⚠️ 중요**: 배치 처리는 시간이 오래 걸릴 수 있으며, 많은 경고 메시지가 출력될 수 있습니다. 이것은 정상입니다.

**경고 메시지 예시**:
```
Cannot set gray non-stroke color because /'P1' is an invalid float value
```
- 이것은 PDF 파싱 라이브러리(pypdfium2)의 경고입니다
- 실제 처리를 막지는 않으며 무시해도 됩니다
- 많은 PDF 파일을 처리할 때 이런 경고가 반복될 수 있습니다

1. **에러 처리**: 일부 파일에서 에러가 발생해도 전체 작업은 계속 진행됩니다. 작업 완료 후 출력 파일을 확인하세요.

2. **Transformers 버전**: 배치 처리 전에 transformers 버전을 확인하고 필요시 다운그레이드하세요:
   ```bash
   pip show transformers
   # 버전이 4.57.0 이상이면 다운그레이드 권장
   pip install "transformers>=4.33.0,<4.57.0"
   ```

3. **에러 발생 파일 확인**: 작업 완료 후 다음 명령으로 에러가 발생한 파일을 확인할 수 있습니다:
   ```bash
   # 출력 디렉토리에서 빈 마크다운 파일 찾기
   find ./output -name "*.md" -size 0
   
   # 또는 파일 크기가 매우 작은 파일 확인
   find ./output -name "*.md" -size -100c
   ```

4. **단계적 처리**: 많은 파일을 처리할 때는 작은 배치로 나눠서 처리하는 것이 안정적입니다:
   ```bash
   # 첫 10개 파일
   ls ./pdfs/*.pdf | head -10 | xargs -I {} mineru -p {} -o ./output -b pipeline
   ```

5. **경고 메시지 필터링**: 경고 메시지가 너무 많으면 필터링할 수 있습니다:
   ```bash
   # 경고 메시지 숨기고 진행 상황만 보기
   mineru -p "./pdfs/" -o "./output" -b pipeline 2>&1 | grep -v "Cannot set gray"
   
   # 또는 백그라운드 실행
   nohup mineru -p "./pdfs/" -o "./output" -b pipeline > mineru.log 2>&1 &
   tail -f mineru.log
   ```

6. **단일 파일 테스트**: 배치 처리 전에 단일 파일로 먼저 테스트:
   ```bash
   # 하나의 파일로 테스트
   mineru -p "./pdfs/sample.pdf" -o "./output" -b pipeline
   
   # 성공하면 배치 처리 진행
   mineru -p "./pdfs/" -o "./output" -b pipeline
   ```

#### 주요 옵션

| 옵션 | 설명 | 기본값 | 예시 |
|------|------|--------|------|
| `-p, --path` | 입력 PDF 파일 또는 디렉토리 | 필수 | `-p document.pdf` |
| `-o, --output` | 출력 디렉토리 | 필수 | `-o ./output` |
| `-b, --backend` | 백엔드 선택 | `pipeline` | `-b vlm-lmdeploy-engine` |
| `-s, --start-page` | 시작 페이지 (0-based) | 전체 | `-s 0` |
| `-e, --end-page` | 종료 페이지 (0-based) | 전체 | `-e 10` |
| `-d, --device` | 디바이스 (cuda, cpu 등) | 자동 | `-d cuda:0` |

**참고**: `vlm-lmdeploy-engine` 백엔드는 `-m`, `-l`, `-f`, `-t` 옵션을 지원하지 않습니다. VLM이 자동으로 최적의 방법을 선택합니다.

#### Reference 섹션이 제외되는 문제

**증상**:
- Reference 섹션의 헤더(`# References`)는 나타나지만 내용이 비어있음
- JSON 파일에는 Reference 내용이 `discarded_blocks`에 포함되어 있음

**원인**:
MinerU는 기본적으로 페이지 하단 30% 영역에 있는 블록을 **footnote(각주)**로 인식하고 제외합니다. Reference 섹션이 페이지 하단에 위치하면 이 로직에 의해 제외됩니다.

**제외 로직** (MinerU 내부):
```python
# 페이지 하단 30% 영역 + 너비 1/3 이상 + 높이 10 이상 = footnote로 인식
if (x1 - x0) > (page_w / 3) and (y1 - y0) > 10 and y0 > (page_h * 0.7):
    # footnote로 인식하여 제외
```

**해결 방법**:

1. **JSON 파일에서 Reference 추출** (가장 확실한 방법):
   ```python
   import json
   from pathlib import Path
   
   def extract_references_from_json(json_path: Path) -> str:
       """JSON 파일에서 Reference 섹션 추출"""
       with open(json_path, 'r', encoding='utf-8') as f:
           data = json.load(f)
       
       pdf_info = data['pdf_info'][0]
       discarded_blocks = pdf_info.get('discarded_blocks', [])
       
       references = []
       for block in discarded_blocks:
           if 'lines' in block:
               for line in block['lines']:
                   if 'spans' in line:
                       content = ' '.join([s.get('content', '') for s in line['spans']])
                       # Reference 패턴 확인 (숫자로 시작하는 참고문헌)
                       if any(keyword in content.lower() for keyword in 
                              ['1.', '2.', 'et al', 'doi', 'journal', 'nature', 'cell']):
                           references.append(content)
       
       return '\n'.join(references)
   
   # 사용 예시
   json_file = Path("output/.../document_middle.json")
   references = extract_references_from_json(json_file)
   print(references)
   ```

2. **마크다운 파일에 Reference 추가** (권장):
   
   프로젝트에 제공된 스크립트 사용:
   ```bash
   # 단일 파일 처리
   python tests/scripts/extract_references_from_mineru.py \
       "output/.../document.md" \
       "output/.../document_middle.json"
   
   # 또는 JSON 파일 자동 찾기
   python tests/scripts/extract_references_from_mineru.py \
       "output/.../document.md"
   
   # 전체 출력 디렉토리 처리
   python tests/scripts/extract_references_from_mineru.py \
       --output-dir "./output"
   ```
   
   또는 Python 코드로 직접 사용:
   ```python
   from pathlib import Path
   from tests.scripts.extract_references_from_mineru import add_references_to_markdown
   
   md_file = Path("output/.../document.md")
   json_file = Path("output/.../document_middle.json")
   
   add_references_to_markdown(md_file, json_file, backup=True)
   ```

3. **페이지 범위 조정** (Reference가 별도 페이지에 있는 경우):
   ```bash
   # 전체 페이지 변환
   mineru -p "document.pdf" -o "./output" -b pipeline
   
   # Reference가 마지막 페이지에 있다면, 해당 페이지만 추가로 변환
   mineru -p "document.pdf" -o "./output" -b pipeline -s <reference_start_page> -e <reference_end_page>
   ```

4. **MinerU 소스 코드 수정** (고급 사용자):
   - `block_pre_proc.py`의 footnote 인식 로직 수정
   - `y0 > (page_h * 0.7)` 조건을 완화하거나 비활성화
   - ⚠️ **주의**: MinerU 업데이트 시 변경사항이 덮어씌워질 수 있음

**권장 해결책**:
- **즉시 해결**: JSON 파일에서 Reference를 추출하여 마크다운에 추가하는 스크립트 사용
- **장기 해결**: MinerU 개발팀에 이슈 제기하여 설정 옵션 추가 요청

---

## 고급 설정

### 환경 변수 설정

LMDeploy 백엔드는 다음 환경 변수를 지원합니다:

```bash
# LMDeploy 백엔드 타입 설정 (pytorch 또는 turbomind)
export LM_DEPLOY_BACKEND=pytorch  # 또는 turbomind

# GPU 디바이스 설정
export CUDA_VISIBLE_DEVICES=0

# 메모리 최적화
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### LMDeploy 백엔드 타입

#### 1. PyTorch 백엔드 (기본, 권장)

```bash
# 환경 변수로 설정
export LM_DEPLOY_BACKEND=pytorch

# 또는 코드에서 설정
# (Python API 사용 시)
```

**특징**:
- 모든 플랫폼 지원 (Linux, macOS, Windows)
- 유연한 설정
- 상대적으로 느림

#### 2. TurboMind 백엔드 (Windows 제한)

```bash
# Linux/macOS에서만 사용 가능
export LM_DEPLOY_BACKEND=turbomind
```

**특징**:
- 더 빠른 추론 속도
- Windows에서는 사용 불가
- 메모리 효율적

### GPU 메모리 최적화

큰 PDF 파일을 처리할 때 GPU 메모리 부족이 발생할 수 있습니다:

```bash
# 배치 크기 조정 (환경 변수)
export MINERU_BATCH_SIZE=4

# 또는 Python 코드에서 설정
# (Python API 사용 시)
```

---

## Python 코드 사용법

### 기본 사용 예시

```python
from pathlib import Path
from datetime import datetime
import subprocess

def convert_pdf_with_lmdeploy(
    pdf_path: Path,
    output_dir: Path,
    device: str = "cuda:0",
    start_page: int = None,
    end_page: int = None
) -> dict:
    """
    LMDeploy 백엔드를 사용하여 PDF를 Markdown으로 변환
    
    Args:
        pdf_path: 변환할 PDF 파일 경로
        output_dir: 출력 디렉토리
        device: 사용할 디바이스 (cuda:0, cpu 등)
        start_page: 시작 페이지 (0-based, 선택사항)
        end_page: 종료 페이지 (0-based, 선택사항)
    
    Returns:
        실행 결과 딕셔너리
    """
    # 출력 디렉토리 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"mineru_{timestamp}_lmdeploy"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # MinerU 명령어 구성
    cmd = [
        "mineru",
        "-p", str(pdf_path),
        "-o", str(output_path),
        "-b", "vlm-lmdeploy-engine",
        "-d", device,
    ]
    
    # 페이지 범위 지정 (선택사항)
    if start_page is not None:
        cmd.extend(["-s", str(start_page)])
    if end_page is not None:
        cmd.extend(["-e", str(end_page)])
    
    print(f"🔄 MinerU LMDeploy 실행 중...")
    print(f"📄 입력: {pdf_path.name}")
    print(f"📁 출력: {output_path}")
    print(f"⚙️  디바이스: {device}")
    print(f"\n명령어: {' '.join(cmd)}\n")
    
    # 실행
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    
    # 결과 확인
    if result.returncode == 0:
        # 출력 파일 찾기
        md_files = list(output_path.rglob("*.md"))
        json_files = list(output_path.rglob("*.json"))
        
        return {
            "success": True,
            "output_dir": str(output_path),
            "markdown_files": [str(f) for f in md_files],
            "json_files": [str(f) for f in json_files],
            "stdout": result.stdout,
        }
    else:
        return {
            "success": False,
            "error": result.stderr,
            "returncode": result.returncode,
        }


# 사용 예시
if __name__ == "__main__":
    pdf_path = Path("document.pdf")
    output_dir = Path("./output")
    
    result = convert_pdf_with_lmdeploy(
        pdf_path=pdf_path,
        output_dir=output_dir,
        device="cuda:0",
        start_page=0,  # 첫 페이지부터
        end_page=5     # 5페이지까지 (0-based이므로 실제로는 6페이지)
    )
    
    if result["success"]:
        print("✅ 변환 성공!")
        print(f"📄 Markdown 파일: {result['markdown_files']}")
    else:
        print(f"❌ 변환 실패: {result['error']}")
```

### 클래스 기반 래퍼 (프로젝트 코드 참고)

프로젝트의 `tests/test_mineru_cli.py` 파일을 참고하여 더 구조화된 코드를 작성할 수 있습니다:

```python
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, Optional

class MinerUWithLMDeploy:
    """MinerU LMDeploy 백엔드 래퍼 클래스"""
    
    def __init__(
        self,
        pdf_path: Path,
        output_base_dir: Path,
        device: str = "cuda:0"
    ):
        self.pdf_path = Path(pdf_path)
        self.output_base_dir = Path(output_base_dir)
        self.device = device
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {self.pdf_path}")
    
    def convert(
        self,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None
    ) -> Dict:
        """PDF를 Markdown으로 변환"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.output_base_dir / f"mineru_{timestamp}_lmdeploy"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "mineru",
            "-p", str(self.pdf_path),
            "-o", str(output_dir),
            "-b", "vlm-lmdeploy-engine",
            "-d", self.device,
        ]
        
        if start_page is not None:
            cmd.extend(["-s", str(start_page)])
        if end_page is not None:
            cmd.extend(["-e", str(end_page)])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        return {
            "success": result.returncode == 0,
            "output_dir": str(output_dir),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }


# 사용 예시
converter = MinerUWithLMDeploy(
    pdf_path=Path("document.pdf"),
    output_base_dir=Path("./output"),
    device="cuda:0"
)

result = converter.convert(start_page=0, end_page=10)
```

---

## 문제 해결

### ⚠️ 중요: LMDeploy 백엔드 배치 처리 이슈

**실제 테스트 결과 (2025-01-27 기준)**:
- **배치 처리**: 10개 파일 중 9개 실패 (90% 실패율)
- **단일 파일 처리**: 정상 작동 (100% 성공률)

**핵심 발견**:
- ✅ **단일 파일 처리 시 LMDeploy는 정상적으로 작동합니다**
- ❌ **배치 처리(디렉토리 전체) 시 대부분의 파일에서 실패합니다**
- 문제는 **배치 처리 시 세션 관리 버그**로 추정됨

**현재 상황**:
- 배치 처리 시 출력 파일이 생성되지만 **내용이 비어있습니다** (0바이트, 0줄)
- `HANDLER_NOT_EXIST` 에러가 발생하거나 에러 없이 빈 파일만 생성됨
- transformers 버전을 다운그레이드해도 배치 처리 문제가 지속됩니다
- "Two Step Extraction: 100%"로 표시되어도 실제 변환은 실패했을 수 있습니다

**권장 사항**:
- ✅ **단일 파일 처리 시**: LMDeploy 사용 가능 (정상 작동)
- ❌ **배치 처리 시**: Pipeline 또는 vLLM 백엔드 사용 권장

**즉시 해결 방법**:
```bash
# Pipeline 백엔드 사용 (가장 안정적, 권장)
mineru -p "./pdfs/" -o "./output" -b pipeline
```

**출력 파일 검증**:
```bash
# 빈 파일 확인
find ./output -name "*.md" -size 0

# 작은 파일 확인 (100바이트 미만)
find ./output -name "*.md" -size -100c
```

---

### 일반적인 문제

#### 1. "LMDeploy backend not found" 오류

**원인**: LMDeploy가 제대로 설치되지 않음

**해결 방법**:
```bash
# 재설치
pip uninstall mineru
pip install "mineru[core,lmdeploy]"

# 또는 uv 사용
uv pip install -U "mineru[core,lmdeploy]"
```

#### 2. GPU 메모리 부족 (OOM)

**원인**: PDF가 너무 크거나 GPU 메모리가 부족

**해결 방법**:
- 페이지 범위를 나눠서 처리:
  ```bash
  # 첫 10페이지
  mineru -p doc.pdf -o output -b vlm-lmdeploy-engine -s 0 -e 9
  
  # 다음 10페이지
  mineru -p doc.pdf -o output -b vlm-lmdeploy-engine -s 10 -e 19
  ```

- CPU 사용 (느리지만 메모리 제한 없음):
  ```bash
  mineru -p doc.pdf -o output -b vlm-lmdeploy-engine -d cpu
  ```

#### 3. Windows에서 TurboMind 백엔드 사용 불가

**원인**: Windows는 TurboMind를 지원하지 않음

**해결 방법**:
- PyTorch 백엔드 사용 (기본값)
- WSL2를 통해 Linux 환경에서 실행

#### 4. "Ray" 관련 오류 (Windows)

**원인**: Windows에서 Ray가 Python 3.13을 지원하지 않음

**해결 방법**:
- Python 3.10-3.12 사용
- 또는 WSL2 사용

#### 5. "HANDLER_NOT_EXIST" 에러 (배치 처리 시)

**증상**:
```
lmdeploy - ERROR - async_engine.py:987 - session XXX finished, ResponseType.HANDLER_NOT_EXIST, reason "error"
Warning: line does not match layout format: internal error happened, status code ResponseType.HANDLER_NOT_EXIST
```

**원인**:
- LMDeploy의 async engine에서 세션 핸들러가 제대로 등록되지 않음
- Transformers 버전 불일치 (LMDeploy는 4.33.0~4.56.1 필요, 현재 4.57.3 설치됨)
- 배치 처리 시 세션 관리 문제
- 일부 PDF 파일의 레이아웃이 복잡하거나 손상된 경우

**영향**:
- 일부 파일에서 에러가 발생하지만, 전체 작업은 계속 진행됨
- 에러가 발생한 파일의 일부 페이지는 변환되지 않을 수 있음
- 최종 출력 파일은 생성되지만 내용이 불완전할 수 있음

**해결 방법** (우선순위 순):

#### 1순위: Pipeline 백엔드 사용 (가장 확실, 강력 권장)
```bash
# Pipeline 백엔드 사용 (100% 성공률)
mineru -p "./pdfs/" -o "./output" -b pipeline
```
- ✅ 100% 성공률 (실제 테스트 기준)
- ✅ 가장 안정적
- ✅ 모든 기능 지원

#### 2순위: vLLM 백엔드 사용
```bash
# vLLM 백엔드 사용 (100% 성공률)
mineru -p "./pdfs/" -o "./output" -b vlm-vllm-engine
```
- ✅ 100% 성공률 (실제 테스트 기준)
- ✅ 더 빠른 추론 (대량 처리 시)
- ⚠️ 더 많은 GPU 메모리 필요

#### 3순위: LMDeploy 단일 파일 처리 (작동 확인됨!)
```bash
# 각 파일을 개별적으로 처리
for pdf in ./pdfs/*.pdf; do
    mineru -p "$pdf" -o "./output" -b vlm-lmdeploy-engine
    sleep 2  # 세션 정리 시간 (권장)
done
```
- ✅ **실제 테스트 결과: 단일 파일 처리 시 정상 작동 확인**
- ✅ 배치 처리 문제를 우회하는 실용적인 해결책
- ⚠️ 시간이 오래 걸릴 수 있음 (파일당 개별 처리)
- ⚠️ 배치 처리보다 느리지만, LMDeploy를 사용해야 하는 경우 유용

#### 4순위: Transformers 버전 다운그레이드 (효과 불확실)
```bash
# 호환되는 transformers 버전으로 다운그레이드
pip install "transformers>=4.33.0,<4.57.0"
```
- ⚠️ 실제 테스트에서도 문제가 지속됨
- ⚠️ 근본적인 해결책이 아님

4. **에러 발생 파일 재처리**:
   ```bash
   # 에러가 발생한 특정 파일만 재처리
   mineru -p "problematic_file.pdf" -o "./output" -b vlm-lmdeploy-engine
   ```

5. **환경 변수로 세션 타임아웃 조정**:
   ```bash
   # 세션 타임아웃 증가 (초 단위)
   export LM_DEPLOY_SESSION_TIMEOUT=300
   
   # 배치 크기 감소
   export LM_DEPLOY_BATCH_SIZE=1
   ```

**중요 발견**:
- transformers 버전을 다운그레이드해도 문제가 지속되는 경우, 이는 LMDeploy async engine의 세션 관리 버그일 가능성이 높습니다
- 에러가 발생하면 출력 파일이 생성되지만 **내용이 비어있을 수 있습니다** (0줄)
- "Two Step Extraction: 100%"로 표시되어도 실제 변환이 실패했을 수 있으므로 **반드시 출력 파일을 확인**해야 합니다

**근본 원인 분석**:
1. **배치 처리 시 세션 관리 버그**: LMDeploy의 async engine이 여러 파일을 동시에 처리할 때 세션 핸들러가 제대로 등록되지 않음
2. **단일 파일 처리 시 정상 작동**: 각 파일을 개별적으로 처리하면 세션 충돌이 없어 정상 작동
3. 배치 처리 시 세션 ID 충돌 또는 세션 관리 문제
4. LMDeploy 버전과 MinerU 버전 간의 호환성 문제

**중요 발견**:
- ✅ **단일 파일 처리로 문제 해결 가능**: 배치 처리 대신 단일 파일을 순차적으로 처리하면 정상 작동
- ❌ **배치 처리만 문제**: 디렉토리 전체를 한 번에 처리할 때만 실패

**추가 해결 방법**:

1. **Pipeline 백엔드로 전환** (가장 권장):
   ```bash
   # LMDeploy 대신 pipeline 백엔드 사용
   mineru -p "./pdfs/" -o "./output" -b pipeline
   ```
   - 가장 안정적이고 에러가 거의 없음
   - 모든 기능 지원 (method, lang, formula, table 옵션)

2. **vLLM 백엔드 사용**:
   ```bash
   # vLLM 백엔드 시도
   mineru -p "./pdfs/" -o "./output" -b vlm-vllm-engine
   ```
   - LMDeploy보다 안정적일 수 있음
   - 더 많은 GPU 메모리 필요

3. **LMDeploy 재설치**:
   ```bash
   # LMDeploy 완전 재설치
   pip uninstall lmdeploy
   pip install lmdeploy
   
   # 또는 특정 버전 설치
   pip install lmdeploy==0.4.0
   ```

4. **단일 파일씩 순차 처리** (✅ 작동 확인됨!):
   ```bash
   # 각 파일을 개별적으로 처리 (배치 처리 문제 우회)
   for pdf in ./pdfs/*.pdf; do
       echo "Processing: $pdf"
       mineru -p "$pdf" -o "./output" -b vlm-lmdeploy-engine
       sleep 2  # 세션 정리 시간 (권장)
   done
   ```
   - ✅ **실제 테스트 결과: 단일 파일 처리 시 정상 작동 확인**
   - ✅ 배치 처리 문제를 완전히 우회하는 해결책
   - ⚠️ 배치 처리보다 느리지만, LMDeploy를 사용해야 하는 경우 실용적

5. **출력 파일 검증 스크립트**:
   ```bash
   # 빈 마크다운 파일 찾기
   find ./output -name "*.md" -size 0
   
   # 작은 파일 찾기 (100바이트 미만)
   find ./output -name "*.md" -size -100c
   ```

#### 6. 빈 출력 파일 생성 (HANDLER_NOT_EXIST 에러 후)

**증상**:
- 변환이 완료되었다고 표시되지만 마크다운 파일이 비어있음 (0줄)
- 모든 파일에서 동일한 문제 발생

**원인**:
- HANDLER_NOT_EXIST 에러로 인해 실제 변환이 실패했지만, MinerU가 이를 감지하지 못함
- LMDeploy async engine의 세션 관리 버그

**해결 방법**:
1. **즉시 Pipeline 백엔드로 전환** (가장 확실한 방법):
   ```bash
   mineru -p "./pdfs/" -o "./output" -b pipeline
   ```

2. **에러 발생 파일 재처리**:
   ```bash
   # 빈 파일 찾기
   empty_files=$(find ./output -name "*.md" -size 0)
   
   # 각 파일의 원본 PDF 찾아서 재처리
   for md_file in $empty_files; do
       # 원본 PDF 경로 추출 및 재처리
       pdf_name=$(basename "$md_file" .md)
       pdf_path="./pdfs/${pdf_name}.pdf"
       if [ -f "$pdf_path" ]; then
           mineru -p "$pdf_path" -o "./output" -b pipeline
       fi
   done
   ```

3. **출력 검증 자동화**:
   ```python
   from pathlib import Path
   
   def validate_output(output_dir: Path):
       """출력 파일 검증"""
       md_files = list(output_dir.rglob("*.md"))
       empty_files = [f for f in md_files if f.stat().st_size == 0]
       
       if empty_files:
           print(f"⚠️  {len(empty_files)}개의 빈 파일 발견:")
           for f in empty_files:
               print(f"  - {f}")
           return False
       else:
           print("✅ 모든 파일이 정상적으로 변환되었습니다")
           return True
   ```

#### 7. Transformers 버전 경고

**증상**:
```
LMDeploy requires transformers version: [4.33.0 ~ 4.56.1], but found version: 4.57.3
```

**원인**: LMDeploy가 특정 transformers 버전 범위를 요구하지만, 더 최신 버전이 설치됨

**해결 방법**:
```bash
# 호환되는 버전으로 다운그레이드
pip install "transformers>=4.33.0,<4.57.0"

# 또는 정확한 버전 설치
pip install transformers==4.56.1

# 설치 확인
pip show transformers
```

**주의사항**:
- 다른 패키지가 최신 transformers를 요구할 수 있으므로, 의존성 충돌을 확인하세요
- 가상환경을 사용하여 격리하는 것을 권장합니다

### 로그 확인

상세한 로그를 확인하려면:

```bash
# 환경 변수로 로그 레벨 설정
export MINERU_LOG_LEVEL=DEBUG

# 또는 Python 코드에서
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 성능 비교

### 실제 테스트 결과 (2025-01-27 기준)

**테스트 환경**:
- 파일 수: 10개 PDF 문서 (의학 논문)
- 백엔드: pipeline, vlm-lmdeploy-engine, vlm-vllm-engine

**성공률 및 파일 크기**:

| 백엔드 | 성공률 | 평균 파일 크기 | 최대 파일 크기 | 비고 |
|--------|--------|---------------|---------------|------|
| `pipeline` | **100%** (10/10) | 60KB | 116KB | 가장 안정적 |
| `vlm-lmdeploy-engine` | **10%** (1/10) | 71KB | 71KB | **대부분 실패** |
| `vlm-vllm-engine` | **100%** (10/10) | 70KB | 132KB | 안정적, 더 많은 내용 추출 |

**참고**: 
- 실행 시간은 하드웨어와 PDF 복잡도에 따라 달라질 수 있습니다
- LMDeploy는 초기 모델 로딩 시간이 있지만, **현재는 대부분의 파일에서 실패**합니다
- 메모리 사용량은 GPU 메모리를 의미합니다
- **결론**: Pipeline 또는 vLLM 백엔드 사용을 강력히 권장합니다

### 언제 어떤 백엔드를 사용할까?

- **`pipeline`** (가장 권장): 
  - ✅ 가장 안정적이고 신뢰할 수 있음
  - ✅ 다양한 옵션 (method, lang, formula, table 등)
  - ✅ 단일 문서 및 배치 처리 모두 적합
  - ✅ 에러 발생률이 매우 낮음
  - ⚠️ 상대적으로 느릴 수 있음

- **`vlm-lmdeploy-engine`**: 
  - ⚠️ **배치 처리 시 문제** (실제 테스트: 90% 실패율)
  - ✅ **단일 파일 처리 시 정상 작동** (실제 테스트 확인)
  - 🚨 배치 처리(디렉토리 전체) 시 대부분의 파일에서 빈 출력 파일 생성
  - ✅ 단일 파일씩 순차 처리하면 정상 작동
  - ⚠️ transformers 버전 호환성 문제
  - ✅ 메모리 효율적 (단일 파일 처리 시)
  - ✅ 복잡한 레이아웃 처리에 우수 (단일 파일 처리 시)
  - **권장**: 
    - 배치 처리 시: pipeline 또는 vLLM 백엔드 사용
    - 단일 파일 처리 시: LMDeploy 사용 가능 (정상 작동)

- **`vlm-vllm-engine`**: 
  - ✅ LMDeploy보다 안정적
  - ✅ 매우 빠른 추론 (대량 처리 시)
  - ⚠️ 더 많은 GPU 메모리 필요
  - ⚠️ 초기 설정이 복잡할 수 있음

**현재 상황 요약** (2025-01-27 실제 테스트 기준):
- **배치 처리**: LMDeploy 백엔드는 세션 관리 버그로 인해 **배치 처리 시 90%의 파일에서 빈 파일을 생성**하는 문제가 있습니다 (10개 파일 중 9개 실패)
- **단일 파일 처리**: ✅ **단일 파일 처리 시 정상 작동 확인** (100% 성공률)
- **해결책**:
  - 배치 처리 시: `pipeline` 백엔드 (100% 성공률) 또는 `vlm-vllm-engine` (100% 성공률) 사용
  - 단일 파일 처리 시: LMDeploy 사용 가능 (정상 작동)
  - LMDeploy 배치 처리 우회: 단일 파일씩 순차 처리

**배치 처리 성능 및 제한사항**:
- 배치 처리는 **시간이 오래 걸릴 수 있습니다** (파일당 수십 초 ~ 수분)
- 많은 경고 메시지가 출력될 수 있지만, 이것은 정상이며 처리에 영향을 주지 않습니다
- **단일 파일 테스트를 먼저 권장**합니다
- 배치 처리 중에는 프로세스가 실행 중인지 확인:
  ```bash
  ps aux | grep mineru | grep -v grep
  ```
- 출력 파일이 생성되는지 주기적으로 확인:
  ```bash
  watch -n 5 'find output -name "*.md" | wc -l'
  ```

---

## 출력 파일 구조

MinerU는 `-m` (method) 옵션에 따라 다른 디렉토리 구조를 생성합니다.

### 출력 디렉토리 구조

```
output/
└── document_name/              # PDF 파일명 (확장자 제외)
    ├── auto/                   # -m auto 사용 시 (기본값)
    │   ├── document_name.md
    │   ├── document_name_middle.json
    │   ├── document_name_layout.pdf
    │   └── images/
    ├── txt/                    # -m txt 사용 시
    │   ├── document_name.md
    │   ├── document_name_middle.json
    │   └── images/
    ├── ocr/                    # -m ocr 사용 시
    │   ├── document_name.md
    │   ├── document_name_middle.json
    │   └── images/
    └── vlm/                    # VLM 백엔드 사용 시 (vlm-lmdeploy-engine, vlm-vllm-engine 등)
        ├── document_name.md
        ├── document_name_middle.json
        ├── document_name_layout.pdf
        └── images/
```

### Method 옵션별 디렉토리

| Method 옵션 | 디렉토리명 | 설명 |
|------------|----------|------|
| `-m auto` (기본값) | `auto/` | 파일 타입에 따라 자동으로 방법 선택 |
| `-m txt` | `txt/` | 텍스트 추출 방법 사용 |
| `-m ocr` | `ocr/` | OCR 방법 사용 (이미지 기반 PDF용) |
| VLM 백엔드 | `vlm/` | VLM 백엔드 사용 시 (method 옵션 무시) |

**참고**:
- `-m` 옵션은 **pipeline 백엔드에서만** 사용 가능합니다
- VLM 백엔드(`vlm-lmdeploy-engine`, `vlm-vllm-engine` 등)를 사용하면 항상 `vlm/` 디렉토리가 생성됩니다
- 같은 PDF를 다른 method로 변환하면 각각 별도의 디렉토리에 저장됩니다

### 주요 출력 파일

1. **`.md` 파일**: 최종 Markdown 변환 결과
2. **`_middle.json`**: 구조화된 JSON 데이터 (프로그래밍 처리용)
3. **`_layout.pdf`**: 레이아웃 분석 결과 시각화 (pipeline, vlm 백엔드)
4. **`images/`**: PDF에서 추출된 이미지 파일들

---

## 추가 리소스

- [MinerU 공식 문서](https://opendatalab.github.io/MinerU/)
- [MinerU GitHub 저장소](https://github.com/opendatalab/MinerU)
- [LMDeploy 문서](https://lmdeploy.readthedocs.io/)

---

## 참고사항

1. **날짜 처리**: 이 프로젝트의 날짜 처리 규칙에 따라, 모든 로그와 출력 파일명에는 동적 날짜가 사용됩니다.

2. **환경 변수**: `.env` 파일에 설정을 저장하는 것을 권장합니다.

3. **가상환경**: `uv` 환경을 사용하는 경우, `.venv` 내에서 실행해야 합니다:
   ```bash
   uv run mineru -p document.pdf -o output -b vlm-lmdeploy-engine
   ```

---

**작성일**: 2025-01-27  
**버전**: 1.0  
**작성자**: Agentic AI Team

