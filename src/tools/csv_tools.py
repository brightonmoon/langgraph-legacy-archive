"""
CSV 파일 처리 전용 도구

대용량 CSV 파일을 효율적으로 처리하기 위한 도구 모음
- 메타데이터 조회
- 청크 기반 읽기
- 필터링 및 컷오프 조건 적용
"""
import pandas as pd
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain.tools import tool

# 프로젝트 루트 및 경로 설정 (범용 경로 유틸리티 사용)
try:
    from src.utils.paths import get_project_root, get_data_directory
    _project_root = get_project_root()
    _allowed_path = get_data_directory().resolve()
except ImportError:
    # 하위 호환성: 경로 유틸리티가 없는 경우 기본값 사용
    _current_file = Path(__file__).resolve()
    _project_root = _current_file.parent.parent.parent
    _allowed_path = (_project_root / "data").resolve()
    # 디렉토리가 없으면 생성
    _allowed_path.mkdir(parents=True, exist_ok=True)


def _is_path_allowed(filepath: Path) -> bool:
    """파일 경로가 허용된 경로 내에 있는지 확인

    Args:
        filepath: 확인할 파일 경로

    Returns:
        허용된 경로 내에 있으면 True, 아니면 False
    """
    try:
        resolved_path = filepath.resolve()
        # 허용된 경로 내에 있는지 확인
        return resolved_path.is_relative_to(_allowed_path)
    except Exception:
        return False


def _sanitize_query(query: str) -> str:
    """pandas query 문자열을 검증하여 코드 인젝션 방지

    Args:
        query: 검증할 query 문자열

    Returns:
        검증된 query 문자열

    Raises:
        ValueError: 위험한 패턴이 발견된 경우
    """
    # 위험한 패턴 목록
    dangerous_patterns = [
        r'__\w+__',  # __import__, __builtins__ 등
        r'\bimport\b',
        r'\bexec\b',
        r'\beval\b',
        r'\bopen\b',
        r'\blambda\b',
        r'\bos\.',
        r'\bsys\.',
        r'\bsubprocess\b',
        r'\b__',
        r'__\b',
    ]

    query_lower = query.lower()

    # 위험한 패턴 검사
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError(
                f"보안: 쿼리에 허용되지 않는 패턴이 포함되어 있습니다. "
                f"쿼리는 컬럼명, 비교 연산자(>, <, ==, !=, >=, <=), "
                f"논리 연산자(and, or, not), 문자열, 숫자만 사용 가능합니다."
            )

    return query


@tool("read_csv_metadata")
def read_csv_metadata_tool(filepath: str) -> str:
    """CSV 파일의 메타데이터를 조회합니다.
    
    파일 크기, 행 수, 컬럼 정보 등을 빠르게 파악할 수 있습니다.
    대용량 파일의 경우 샘플 데이터만 읽어 구조를 파악합니다.
    
    Args:
        filepath: CSV 파일 경로
        
    Returns:
        파일 크기, 컬럼 정보, 샘플 데이터를 포함한 메타데이터 문자열
    """
    try:
        path = Path(filepath).expanduser().resolve()
        
        # 보안: 허용된 경로 외부 접근 제한
        if not _is_path_allowed(path):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다. (허용 경로: {_allowed_path})"
        
        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        if not path.is_file():
            return f"❌ 경로가 파일이 아닙니다: {filepath}"
        
        # 파일 크기 확인
        file_size = path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        # 전체 행 수 효율적으로 계산 (파일을 끝까지 읽지 않고)
        total_rows = None
        try:
            # 방법 1: wc -l 사용 (가장 빠름, Linux/Mac)
            import subprocess
            result = subprocess.run(
                ['wc', '-l', str(path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # wc -l은 헤더를 포함하므로 -1 (헤더 제외)
                total_rows = int(result.stdout.strip().split()[0]) - 1
                if total_rows < 0:
                    total_rows = 0
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
            # 방법 2: 파일을 청크로 읽어서 행 수 계산 (대용량 파일에 효율적)
            try:
                chunk_size = 10000
                total_rows = 0
                for chunk in pd.read_csv(path, chunksize=chunk_size):
                    total_rows += len(chunk)
                # 헤더는 첫 청크에 포함되므로 이미 계산됨
            except Exception as e:
                # 방법 3: 파일 크기와 샘플 행 크기로 추정
                try:
                    # 파일의 처음 부분을 읽어서 평균 행 크기 추정
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        sample_lines = []
                        for i, line in enumerate(f):
                            if i >= 1000:  # 처음 1000행 샘플
                                break
                            sample_lines.append(line)
                    
                    if len(sample_lines) > 0:
                        sample_text = ''.join(sample_lines)
                        sample_size = len(sample_text.encode('utf-8'))
                        avg_row_size = sample_size / len(sample_lines) if len(sample_lines) > 0 else 0
                        if avg_row_size > 0:
                            total_rows = int(file_size / avg_row_size)
                except Exception:
                    pass
        
        # 첫 100행만 읽어서 구조 파악 (메모리 효율적)
        try:
            df_sample = pd.read_csv(path, nrows=100)
            
            # 전체 행 수 표시
            total_rows_str = f"{total_rows:,} 행" if total_rows else "계산 실패 (샘플만 확인됨)"
            
            metadata_info = f"""📊 CSV 파일 메타데이터: {filepath}

📏 파일 정보:
- 파일 크기: {file_size_mb:.2f} MB ({file_size:,} bytes)
- 전체 행 수: {total_rows_str}
- 샘플 행 수: {len(df_sample)} 행 (구조 파악용)

📋 컬럼 정보:
- 컬럼 수: {len(df_sample.columns)}
- 컬럼 목록: {', '.join(df_sample.columns.tolist())}

📝 데이터 타입:
"""
            for col, dtype in df_sample.dtypes.items():
                metadata_info += f"  - {col}: {dtype}\n"
            
            metadata_info += f"\n📄 샘플 데이터 (상위 5행):\n"
            metadata_info += df_sample.head(5).to_string(index=False)
            
            # 데이터 통계 정보 (수치형 컬럼만)
            # 주의: 샘플 100행의 통계이므로 전체 데이터 통계와 다를 수 있음
            numeric_cols = df_sample.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                metadata_info += f"\n\n📈 수치형 컬럼 통계 (샘플 {len(df_sample)}행 기준):\n"
                metadata_info += df_sample[numeric_cols].describe().to_string()
                if total_rows and total_rows > len(df_sample):
                    metadata_info += f"\n\n⚠️ 주의: 통계는 샘플 {len(df_sample)}행 기준입니다. 전체 {total_rows:,}행의 통계와 다를 수 있습니다."
            
            return metadata_info
            
        except pd.errors.EmptyDataError:
            return f"❌ CSV 파일이 비어있습니다: {filepath}"
        except Exception as e:
            return f"❌ CSV 파일 읽기 오류: {str(e)}"
            
    except PermissionError:
        return f"❌ 권한이 없어 {filepath} 파일을 읽을 수 없습니다."
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@tool("read_csv_chunk")
def read_csv_chunk_tool(
    filepath: str,
    nrows: Optional[int] = None,
    skiprows: Optional[int] = None,
    usecols: Optional[List[str]] = None,
    max_display_rows: int = 50
) -> str:
    """CSV 파일의 일부만 읽어 반환합니다.
    
    대용량 파일의 경우 메모리 효율적으로 특정 부분만 읽을 수 있습니다.
    
    Args:
        filepath: CSV 파일 경로
        nrows: 읽을 행 수 (None이면 전체, 그러나 표시는 max_display_rows로 제한)
        skiprows: 건너뛸 행 수 (시작 위치)
        usecols: 읽을 컬럼 목록 (None이면 전체 컬럼)
        max_display_rows: 실제로 표시할 최대 행 수 (기본값: 50)
        
    Returns:
        CSV 데이터의 문자열 표현 (표시 행 수는 max_display_rows로 제한됨)
    """
    try:
        path = Path(filepath).expanduser().resolve()
        
        # 보안: 허용된 경로 외부 접근 제한
        if not _is_path_allowed(path):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다. (허용 경로: {_allowed_path})"
        
        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        # 읽기 파라미터 구성
        read_params = {}
        if nrows:
            read_params['nrows'] = nrows
        if skiprows:
            read_params['skiprows'] = skiprows
        if usecols:
            read_params['usecols'] = usecols
        
        # CSV 읽기
        df = pd.read_csv(path, **read_params)
        
        total_rows = len(df)
        
        # 표시할 행 수 결정
        display_rows = min(max_display_rows, total_rows)
        
        result = f"""📊 CSV 데이터 조회 결과:

📏 데이터 정보:
- 조회된 행 수: {total_rows:,} 행
- 컬럼 수: {len(df.columns)} 컬럼
- 표시 행 수: {display_rows} 행 (최대 {max_display_rows}행으로 제한)

📋 컬럼: {', '.join(df.columns.tolist())}

📄 데이터 (상위 {display_rows}행):
"""
        result += df.head(display_rows).to_string(index=False)
        
        if total_rows > display_rows:
            result += f"\n\n... (총 {total_rows:,} 행 중 {display_rows} 행만 표시됨)"
        
        return result
        
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"


@tool("filter_csv")
def filter_csv_tool(
    filepath: str,
    filter_query: str,
    output_filepath: Optional[str] = None,
    max_results: int = 1000
) -> str:
    """CSV 파일에 필터 조건을 적용합니다.
    
    pandas query 문자열을 사용하여 복잡한 필터링을 수행할 수 있습니다.
    대용량 파일의 경우 청크 단위로 처리하여 메모리 효율적으로 동작합니다.
    
    Args:
        filepath: 입력 CSV 파일 경로
        filter_query: pandas query 문자열 (예: "column1 > 100 and column2 == 'value'")
                     또는 간단한 조건 (예: "column1 > 100")
        output_filepath: 필터링된 결과를 저장할 파일 경로 (None이면 새 파일 생성하지 않음)
        max_results: 최대 반환/표시 행 수 (기본값: 1000)
        
    Returns:
        필터링 결과 요약 및 샘플 데이터
    """
    try:
        path = Path(filepath).expanduser().resolve()
        
        # 보안: 허용된 경로 외부 접근 제한
        if not _is_path_allowed(path):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다. (허용 경로: {_allowed_path})"
        
        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        # 파일 크기 확인하여 처리 전략 결정
        file_size = path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        # 쿼리 검증
        try:
            sanitized_query = _sanitize_query(filter_query)
        except ValueError as e:
            return f"❌ {str(e)}"

        # 파일 크기에 따라 처리 전략 선택
        if file_size_mb < 10:
            # 소형 파일: 전체 읽기
            df = pd.read_csv(path)
            filtered_df = df.query(sanitized_query)
            
            matched_count = len(filtered_df)
            display_df = filtered_df.head(max_results)
            
        else:
            # 대형 파일: 청크 단위 처리
            chunks = []
            total_matched = 0
            
            for chunk in pd.read_csv(path, chunksize=10000):
                try:
                    filtered_chunk = chunk.query(sanitized_query)
                    if len(filtered_chunk) > 0:
                        total_matched += len(filtered_chunk)
                        # 메모리 절약을 위해 필요한 만큼만 저장
                        if len(chunks) == 0 or total_matched <= max_results:
                            chunks.append(filtered_chunk)
                except Exception as e:
                    return f"❌ 필터 조건 오류: {str(e)}\n필터 쿼리: {filter_query}"
            
            if not chunks:
                return f"✅ 필터링 완료: 필터 조건에 맞는 데이터가 없습니다.\n필터 쿼리: {filter_query}"
            
            filtered_df = pd.concat(chunks, ignore_index=True)
            matched_count = len(filtered_df)
            display_df = filtered_df.head(max_results)
        
        # 결과 생성
        result = f"""✅ 필터링 완료:

📊 필터 조건: {filter_query}
📏 매칭된 행 수: {matched_count:,} 행
"""
        
        if matched_count > max_results:
            result += f"📄 표시 행 수: {max_results} 행 (상위 {max_results} 행만 표시)\n\n"
        else:
            result += f"\n"
        
        if matched_count > 0:
            result += f"📄 샘플 데이터:\n{display_df.to_string(index=False)}\n"
        else:
            result += "❌ 필터 조건에 맞는 데이터가 없습니다.\n"
        
        # 결과 파일 저장
        if output_filepath:
            output_path = Path(output_filepath).expanduser().resolve()
            
            # 보안: 허용된 경로 외부 접근 제한
            if not _is_path_allowed(output_path):
                result += f"\n⚠️ 출력 파일 경로가 허용된 경로 외부여서 저장하지 않았습니다. (허용 경로: {_allowed_path})"
            else:
                try:
                    display_df.to_csv(output_filepath, index=False)
                    result += f"\n💾 결과가 저장되었습니다: {output_filepath} ({matched_count:,} 행)"
                except Exception as e:
                    result += f"\n⚠️ 파일 저장 실패: {str(e)}"
        
        return result
        
    except pd.errors.EmptyDataError:
        return f"❌ CSV 파일이 비어있습니다: {filepath}"
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}\n필터 쿼리: {filter_query}"


@tool("csv_summary_stats")
def csv_summary_stats_tool(
    filepath: str,
    columns: Optional[List[str]] = None
) -> str:
    """CSV 파일의 요약 통계를 계산합니다.
    
    수치형 컬럼에 대한 기본 통계 정보를 제공합니다.
    
    Args:
        filepath: CSV 파일 경로
        columns: 통계를 계산할 컬럼 목록 (None이면 모든 수치형 컬럼)
        
    Returns:
        요약 통계 정보
    """
    try:
        path = Path(filepath).expanduser().resolve()
        
        # 보안: 허용된 경로 외부 접근 제한
        if not _is_path_allowed(path):
            return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다. (허용 경로: {_allowed_path})"
        
        if not path.exists():
            return f"❌ 파일이 존재하지 않습니다: {filepath}"
        
        # 파일 크기에 따라 처리 전략 선택
        file_size = path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb < 50:
            # 소형/중형 파일: 전체 읽기
            df = pd.read_csv(path)
        else:
            # 대형 파일: 샘플 사용
            df = pd.read_csv(path, nrows=100000)  # 최대 10만 행 샘플
        
        # 통계 계산할 컬럼 선택
        if columns:
            stats_df = df[columns]
        else:
            # 수치형 컬럼만 선택
            stats_df = df.select_dtypes(include=['int64', 'float64'])
        
        if len(stats_df.columns) == 0:
            return f"❌ 통계를 계산할 수치형 컬럼이 없습니다."
        
        result = f"""📊 CSV 파일 요약 통계: {filepath}

📏 데이터 정보:
- 행 수: {len(df):,} 행
- 통계 컬럼 수: {len(stats_df.columns)} 컬럼

📈 통계 정보:
{stats_df.describe().to_string()}
"""
        
        return result
        
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}"







