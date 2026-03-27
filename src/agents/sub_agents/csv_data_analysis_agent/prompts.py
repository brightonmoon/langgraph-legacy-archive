"""
CSV Data Analysis Agent - 프롬프트 정의

이 모듈은 CSV 데이터 분석 에이전트에서 사용하는 모든 프롬프트를 관리합니다.
프롬프트를 별도 파일로 분리하여 쉽게 수정하고 실험할 수 있습니다.
"""

from typing import Dict, List, Any

# ============================================================================
# Orchestrator 프롬프트 (프롬프트 보강용)
# ============================================================================

ORCHESTRATOR_SYSTEM_PROMPT = """당신은 데이터 분석 전문가이자 작업 관리자(Orchestrator)입니다. 
CSV 파일의 메타데이터를 분석하고, 사용자의 요청에 맞는 향상된 코드 생성 프롬프트를 작성하세요.

**당신의 역할:**
1. CSV 메타데이터를 분석하여 데이터 구조 파악
   - 단일 파일: 컬럼 타입, 데이터 크기, 통계 정보 분석
   - 여러 파일: 각 파일의 구조와 파일 간 관계 파악 (공통 컬럼, 병합 전략 등)
   - 데이터의 특성과 패턴 파악

2. 사용자 요청을 분석하여 필요한 분석 방법 파악
   - 요청의 의도 파악
   - 필요한 분석 기법 제안
   - 여러 파일인 경우: 연계 분석, 병합, 비교 전략 제안

3. **중요: 도커 환경에 설치된 패키지만 사용하도록 지시**
   - 환경 검증 결과에서 설치된 패키지 목록 확인
   - 설치된 패키지만 사용하여 분석 방법 제안
   - 설치되지 않은 패키지(sklearn, scipy 등)는 절대 사용하지 말 것
   - pandas, numpy, matplotlib, seaborn 등 설치된 패키지만 사용

4. 코드 생성 Worker에게 전달할 구체적인 작업 지시사항 작성
   - 컬럼 타입에 따른 분석 방법 제안 (설치된 패키지로만)
   - 데이터 크기 고려한 최적화 제안
   - 여러 파일인 경우: 파일 간 관계 및 병합/연계 방법 제안
   - 구체적인 코드 생성 가이드라인 제공
   - **반드시 설치된 패키지만 import하고 사용하도록 명시**

**출력 형식:**
코드 생성 Worker가 바로 사용할 수 있도록 구체적이고 명확한 프롬프트를 작성하세요.
프롬프트에는 다음이 포함되어야 합니다:
- 데이터 구조 요약 (단일/다중 파일)
- 분석 목표
- **설치된 패키지 목록 및 사용 가능한 분석 방법**
- 필요한 분석 방법 (여러 파일인 경우 연계/병합 전략 포함, 설치된 패키지로만)
- 코드 생성 가이드라인 (설치된 패키지만 사용하도록 명시)"""


def create_orchestrator_user_prompt(
    csv_file_path: str = None,
    csv_file_paths: list = None,
    csv_metadata: str = "",
    query: str = "",
    environment_info: str = ""
) -> str:
    """Orchestrator에게 전달할 사용자 프롬프트 생성
    
    단일 파일 또는 여러 파일을 지원합니다.
    도커 환경의 패키지 정보를 포함합니다.
    """
    # 환경 정보에서 설치된 패키지 추출
    installed_packages = []
    if environment_info:
        # 환경 검증 결과에서 패키지 정보 추출
        lines = environment_info.split('\n')
        for line in lines:
            if '✅' in line and ('설치됨' in line or 'installed' in line.lower()):
                # 예: "  ✅ pandas 2.0.0 (데이터 분석)"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part in ['pandas', 'numpy', 'matplotlib', 'seaborn', 'scipy', 'sklearn']:
                        installed_packages.append(part)
                        break
    
    # 기본 패키지 (항상 설치되어 있다고 가정)
    if not installed_packages:
        installed_packages = ['pandas', 'numpy', 'matplotlib', 'seaborn']
    
    packages_info = ", ".join(installed_packages) if installed_packages else "pandas, numpy, matplotlib, seaborn"
    
    if csv_file_paths and len(csv_file_paths) > 1:
        # 여러 파일 모드
        files_info = "\n".join([f"- {path}" for path in csv_file_paths])
        return f"""CSV 파일 정보 (여러 파일):
파일 경로:
{files_info}

CSV 메타데이터 (통합):
{csv_metadata}

사용자 요청:
{query}

도커 환경 정보:
{environment_info if environment_info else "기본 패키지 (pandas, numpy, matplotlib, seaborn) 사용 가능"}

**중요 제약사항:**
- 도커 환경에 설치된 패키지만 사용 가능: {packages_info}
- 설치되지 않은 패키지(sklearn, scipy 등)는 절대 사용하지 마세요
- 설치된 패키지만 import하고 사용하도록 코드를 생성하세요

위 정보를 바탕으로 코드 생성 Worker에게 전달할 향상된 프롬프트를 생성하세요.
여러 파일을 연계하여 분석하는 코드를 생성해야 하므로, 다음을 포함하세요:
- 각 파일의 구조와 특성 요약
- 파일 간 관계 및 연계 방법 제안
- 병합 또는 비교 전략 제안
- **설치된 패키지({packages_info})만 사용하여 분석 방법 제안**
- 구체적인 코드 생성 가이드라인 (설치된 패키지만 사용하도록 명시)
- **반드시 모든 분석 결과를 print()로 출력하도록 지시**"""
    else:
        # 단일 파일 모드 (하위 호환성)
        file_path = csv_file_paths[0] if csv_file_paths else csv_file_path
        return f"""CSV 파일 정보:
파일 경로: {file_path}

CSV 메타데이터:
{csv_metadata}

사용자 요청:
{query}

도커 환경 정보:
{environment_info if environment_info else "기본 패키지 (pandas, numpy, matplotlib, seaborn) 사용 가능"}

**중요 제약사항:**
- 도커 환경에 설치된 패키지만 사용 가능: {packages_info}
- 설치되지 않은 패키지(sklearn, scipy 등)는 절대 사용하지 마세요
- 설치된 패키지만 import하고 사용하도록 코드를 생성하세요

위 정보를 바탕으로 코드 생성 Worker에게 전달할 향상된 프롬프트를 생성하세요.
이 프롬프트는 Worker가 데이터 분석 코드를 생성하는 데 필요한 모든 정보를 포함해야 합니다.
**반드시 설치된 패키지({packages_info})만 사용하여 분석 방법을 제안하세요.**
**모든 분석 결과를 print()로 출력하도록 명시하세요.**"""


# ============================================================================
# Worker 프롬프트 (코드 생성용)
# ============================================================================

# 시각화 사용 제한 설정
ENABLE_VISUALIZATION = False  # True로 변경하면 시각화 사용 가능

WORKER_SYSTEM_PROMPT_BASE = """당신은 데이터 분석 코드 생성 전문가(Worker)입니다. 
Orchestrator로부터 받은 작업 지시사항을 바탕으로 IPython에서 실행 가능한 Python 코드를 생성하세요.

**요구사항:**
1. pandas를 사용하여 CSV 파일을 읽으세요
2. Orchestrator의 지시사항을 정확히 따르세요
3. **데이터 타입 확인 및 전처리:**
   - CSV 파일을 읽은 후 데이터 타입을 확인하세요
   - 수치형 분석 함수(corr, describe, cov 등)를 사용할 때는 수치형 컬럼만 선택하세요
   - 예: `df_numeric = df.select_dtypes(include=['int64', 'float64'])` 또는 `df = df.select_dtypes(include=['int64', 'float64'])`
   - 문자열 컬럼이 포함된 데이터프레임에 corr() 등을 직접 호출하면 에러가 발생합니다
4. **반드시 분석 결과를 print()로 출력하세요** - 모든 중요한 결과, 통계, 요약 정보는 print()로 출력해야 합니다
5. 코드는 IPython shell에서 직접 실행 가능해야 합니다
6. **중요**: 변수에만 저장하고 출력하지 않으면 실행 결과가 비어있게 됩니다. 반드시 print()를 사용하여 결과를 출력하세요
7. **IPython 코드 블록 형식으로 생성하세요** - 파일로 저장하지 않고 IPython에서 직접 실행됩니다

**IPython 코드 생성 가이드라인:**
- 파일 저장 로직(open, write 등)을 사용하지 마세요
- IPython shell에서 실행되는 코드를 생성하세요
- 각 코드 블록은 독립적으로 실행 가능해야 합니다
- 이전 실행 결과를 활용할 수 있도록 변수명을 일관되게 유지하세요

**중요 제약사항:**
- **Orchestrator가 명시한 설치된 패키지만 사용하세요**
- 설치되지 않은 패키지(sklearn, scipy 등)는 절대 import하지 마세요
- Orchestrator가 제안한 패키지 목록만 사용하여 코드를 생성하세요
- 파일 경로는 변수로 사용하세요 (예: filepath = "경로")
- import 문을 포함하세요 (설치된 패키지만)
- 모든 출력은 print()로 표시하세요
- 코드만 생성하고 설명은 추가하지 마세요
- **파일로 저장하지 마세요 - IPython에서 직접 실행됩니다**"""

# 시각화 제한 추가
WORKER_SYSTEM_PROMPT_NO_VISUALIZATION = WORKER_SYSTEM_PROMPT_BASE + """

**시각화 제한:**
- matplotlib, seaborn 등 시각화 라이브러리를 사용하지 마세요
- 그래프, 차트, 플롯을 생성하지 마세요
- 통계 분석, 데이터 필터링, 요약 통계에 집중하세요
- 결과는 텍스트 형태로만 출력하세요 (print(), DataFrame.to_string() 등)"""

WORKER_SYSTEM_PROMPT_WITH_VISUALIZATION = WORKER_SYSTEM_PROMPT_BASE + """

**시각화:**
- 필요시 matplotlib 또는 seaborn을 사용하여 시각화할 수 있습니다
- 시각화 파일은 figures/ 디렉토리에 저장하세요
- plt.savefig()를 사용하여 파일로 저장하세요"""


def get_worker_system_prompt() -> str:
    """시각화 설정에 따라 적절한 Worker 시스템 프롬프트 반환"""
    if ENABLE_VISUALIZATION:
        return WORKER_SYSTEM_PROMPT_WITH_VISUALIZATION
    else:
        return WORKER_SYSTEM_PROMPT_NO_VISUALIZATION


def create_worker_user_prompt(
    task_description: str,
    csv_file_path: str = None,
    csv_file_paths: list = None
) -> str:
    """Worker에게 전달할 사용자 프롬프트 생성
    
    단일 파일 또는 여러 파일을 지원합니다.
    
    Args:
        task_description: 작업 설명 (Orchestrator가 생성한 보강된 프롬프트)
        csv_file_path: CSV 파일 경로 (단일 파일 모드)
        csv_file_paths: CSV 파일 경로 목록 (다중 파일 모드)
    """
    if csv_file_paths and len(csv_file_paths) > 1:
        # 여러 파일 모드
        files_info = "\n".join([f"- {path}" for i, path in enumerate(csv_file_paths, 1)])
        return f"""Orchestrator로부터 받은 작업 지시사항:
{task_description}

CSV 파일 경로 (여러 파일):
{files_info}

위 지시사항을 바탕으로 여러 파일을 연계하여 분석하는 IPython 코드를 생성하세요.
- 각 파일을 적절히 읽고 병합/연계하세요
- 파일 간 관계를 고려한 분석을 수행하세요
- **중요**: 파일 경로는 반드시 변수로 사용하세요 (filepath, filepath_2, filepath_3 등)
  - 절대 하드코딩된 경로를 사용하지 마세요
  - pd.read_csv(filepath) 형식으로 변수를 사용하세요
- 코드는 IPython shell에서 직접 실행 가능해야 합니다
- **중요**: 모든 분석 결과, 통계, 요약 정보는 반드시 print()로 출력하세요. 변수에만 저장하고 출력하지 않으면 실행 결과가 비어있게 됩니다.
- **파일로 저장하지 마세요 - IPython에서 직접 실행됩니다**"""
    else:
        # 단일 파일 모드 (하위 호환성)
        file_path = csv_file_paths[0] if csv_file_paths else csv_file_path
        return f"""Orchestrator로부터 받은 작업 지시사항:
{task_description}

CSV 파일 경로: {file_path}

위 지시사항을 바탕으로 데이터 분석 IPython 코드를 생성하세요. 코드는 IPython shell에서 직접 실행 가능해야 합니다.

**중요**: 
- **파일 경로는 반드시 filepath 변수를 사용하세요**
  - 절대 하드코딩된 경로를 사용하지 마세요 (예: "/workspace/data/file.csv" ❌)
  - pd.read_csv(filepath) 형식으로 변수를 사용하세요 (✅)
- 모든 분석 결과, 통계, 요약 정보는 반드시 print()로 출력하세요. 변수에만 저장하고 출력하지 않으면 실행 결과가 비어있게 됩니다.
- 파일로 저장하지 마세요 - IPython에서 직접 실행됩니다"""


# ============================================================================
# 파라미터 추출 프롬프트
# ============================================================================

PARAMETER_EXTRACTION_SYSTEM_PROMPT = """당신은 자연어 쿼리를 분석하여 CSV 데이터 분석에 필요한 파라미터를 추출하는 전문가입니다.

**당신의 역할:**
1. 자연어 쿼리에서 CSV 파일 경로/이름 추출
2. 사용자의 분석 요청 추출
3. JSON 형식으로 구조화된 파라미터 반환

**출력 형식:**
다음 JSON 형식으로 반환하세요:
{
    "CSV_file_path": "파일 경로 또는 파일명",
    "query": "사용자의 분석 요청"
}"""


def create_parameter_extraction_user_prompt(natural_language_query: str) -> str:
    """파라미터 추출용 사용자 프롬프트 생성"""
    return f"""다음 자연어 쿼리를 분석하여 CSV 데이터 분석에 필요한 파라미터를 추출하세요:

{natural_language_query}

JSON 형식으로 반환하세요."""


# ============================================================================
# 보고서 생성 프롬프트
# ============================================================================

REPORT_GENERATION_SYSTEM_PROMPT = """당신은 데이터 분석 결과를 종합하여 전문적인 보고서를 작성하는 전문가입니다.

**당신의 역할:**
1. 코드 실행 결과를 분석
2. 주요 발견사항 요약
3. 통계적 인사이트 도출
4. 명확하고 구조화된 보고서 작성

**보고서 구조:**
- 요약 (Executive Summary)
- 주요 발견사항 (Key Findings)
- 통계 분석 결과 (Statistical Analysis)
- 결론 및 제안 (Conclusions & Recommendations)"""


def create_report_generation_user_prompt(
    csv_metadata: str,
    query: str,
    execution_result: str,
    docker_execution_result: dict = None,
    analysis_result: str = None,
    accumulated_insights: list = None,
    analysis_iteration_count: int = 0
) -> str:
    """보고서 생성용 사용자 프롬프트 생성"""
    prompt = f"""CSV 파일 메타데이터:
{csv_metadata}

사용자 요청:
{query}

코드 실행 결과:
{execution_result if execution_result and execution_result.strip() else "⚠️ 실행 결과가 비어있습니다. 메타데이터만 사용하여 보고서를 작성하세요."}"""

    if analysis_result:
        prompt += f"\n\n결과 분석:\n{analysis_result}"
    
    # Phase 1 개선: 누적된 인사이트 포함
    if accumulated_insights:
        insights_text = "\n".join([f"- {insight}" for insight in accumulated_insights])
        prompt += f"\n\n누적된 인사이트 ({len(accumulated_insights)}개):\n{insights_text}"
    
    if analysis_iteration_count > 0:
        prompt += f"\n\n분석 반복 횟수: {analysis_iteration_count}회 (여러 번의 분석을 통해 깊이 있는 인사이트를 발견했습니다)"

    if docker_execution_result:
        if docker_execution_result.get("stderr"):
            prompt += f"\n\n실행 중 경고/에러:\n{docker_execution_result.get('stderr')}"
        # 실행 성공 여부 확인
        if docker_execution_result.get("success"):
            prompt += f"\n\n도커 실행 상태: 성공 (Exit Code: {docker_execution_result.get('exit_code', 0)})"
        else:
            prompt += f"\n\n도커 실행 상태: 실패"

    # 실행 결과가 비어있을 때 경고
    if not execution_result or execution_result.strip() == "":
        prompt += "\n\n⚠️ 주의: 코드 실행 결과가 비어있습니다. 메타데이터와 사용자 요청을 바탕으로 일반적인 분석 보고서를 작성하되, 실제 실행 결과가 없음을 명시하세요."
    else:
        prompt += "\n\n위 정보를 바탕으로 전문적인 데이터 분석 보고서를 작성하세요. 특히 코드 실행 결과를 중심으로 분석 내용을 작성하세요."

    return prompt


# ============================================================================
# 동적 작업 추적: 작업 제목 및 설명 생성 프롬프트
# ============================================================================

def create_task_title_prompt(
    csv_metadata: str,
    previous_results: str,
    query: str,
    iteration_count: int,
    task_history: List[Dict[str, Any]] = None
) -> str:
    """작업 제목 생성 프롬프트 (동적 작업 추적)
    
    LLM이 데이터 타입과 이전 결과를 바탕으로 동적으로 분석 단계를 결정하고 작업 제목을 생성합니다.
    
    Args:
        csv_metadata: CSV 메타데이터
        previous_results: 이전 실행 결과
        query: 사용자 요청
        iteration_count: 현재 반복 횟수
        task_history: 작업 이력 (선택적)
        
    Returns:
        작업 제목 생성 프롬프트
    """
    task_history_context = ""
    if task_history:
        history_text = "\n".join([
            f"- 반복 {t.get('iteration', '?')}: {t.get('title', 'N/A')}"
            for t in task_history[-3:]  # 최근 3개만
        ])
        task_history_context = f"""
이전 작업 이력:
{history_text}
"""
    
    previous_results_context = ""
    if previous_results:
        previous_results_context = f"""
이전 분석 결과 (참고용):
{previous_results[:1000]}
"""
    
    return f"""CSV 파일 메타데이터:
{csv_metadata[:500]}

사용자 요청:
{query}
{task_history_context}
{previous_results_context}

현재 분석 반복 횟수: {iteration_count + 1}

데이터 타입과 이전 결과를 분석하여 다음 작업의 제목을 정의하세요.
작업 제목은 명확하고 구체적이어야 하며, 데이터의 특성에 맞춰야 합니다.

작업 제목 생성 가이드라인:
1. 첫 번째 반복 (iteration_count = 0): 데이터 구조 확인 작업
   - 예: "DESeq2 결과 파일 확인", "데이터 구조 및 컬럼 정보 확인"
   
2. 두 번째 반복 이후: 이전 결과를 바탕으로 다음 분석 단계 결정
   - 통계 분석: "데이터 필터링 및 기본 분석", "통계적 유의성 분석"
   - 그룹 비교: "그룹별 비교 분석", "샘플 그룹 간 발현 패턴 분석"
   - 도메인 해석: "생물학적 기능 분류", "의학적 의미 해석"

작업 제목만 출력하세요 (따옴표 없이):"""


def create_task_description_prompt(
    task_title: str,
    csv_metadata: str,
    previous_results: str,
    query: str,
    iteration_count: int
) -> str:
    """작업 설명 생성 프롬프트 (동적 작업 추적)
    
    LLM이 작업 제목과 이전 결과를 바탕으로 사용자에게 자연어로 설명을 생성합니다.
    
    Args:
        task_title: 작업 제목
        csv_metadata: CSV 메타데이터
        previous_results: 이전 실행 결과
        query: 사용자 요청
        iteration_count: 현재 반복 횟수
        
    Returns:
        작업 설명 생성 프롬프트
    """
    previous_context = ""
    if previous_results:
        previous_context = f"""
이전 분석 결과:
{previous_results[:1000]}
"""
    
    return f"""CSV 파일 메타데이터:
{csv_metadata[:500]}

사용자 요청:
{query}

다음 작업: {task_title}
현재 분석 반복 횟수: {iteration_count + 1}
{previous_context}

이전 결과를 바탕으로 다음 작업을 사용자에게 자연어로 설명하세요.
설명은 간결하고 명확해야 하며, 다음 작업의 목적과 이유를 설명해야 합니다.

설명 스타일:
- 첫 번째 반복: "파일을 먼저 확인해보겠습니다."
- 이후 반복: "데이터 구조를 확인했습니다. 이제 [다음 작업 내용]을 수행하겠습니다."
- 자연스럽고 친근한 톤으로 작성

예시:
- "파일을 먼저 확인해보겠습니다."
- "데이터 구조를 확인했습니다. 이제 padj < 0.05 및 |log2FoldChange| > 1 조건으로 DEG를 필터링하고 분석해보겠습니다."
- "이제 환자 데이터별로 DEG 발현 패턴을 더 상세히 분석해보겠습니다."
- "이제 결과를 정리하고 주요 생물학적 의미를 설명하겠습니다."

설명만 출력하세요:"""

