"""
DeepAgent용 커스텀 도구들

추가 도구가 필요한 경우 여기에 구현합니다.
- Brave Search 도구
- CSV 파일 처리 도구
- MCP 도구 로드
- 기타 커스텀 도구들
"""

import os
import sys
import json
import asyncio
from typing import List, Optional, Any, Dict
from pathlib import Path
from langchain.tools import tool
try:
    from langchain.agents.middleware import AgentMiddleware
except ImportError:
    # Fallback: DeepAgents의 AgentMiddleware가 다른 경로에 있을 수 있음
    try:
        from deepagents.middleware import AgentMiddleware
    except ImportError:
        # 기본 구조만 정의 (tools 속성만 사용)
        class AgentMiddleware:
            """AgentMiddleware 기본 클래스"""
            tools = []

# 프로젝트 루트를 Python 경로에 추가 (src/tools 모듈 임포트용)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def create_brave_search_tool(api_key: str = None):
    """Brave Search 도구 생성
    
    Brave Search API를 사용한 웹 검색 도구입니다.
    기존 src/tools/brave_search.py를 참고하여 구현했습니다.
    
    Args:
        api_key: Brave API 키 (None이면 환경변수에서 가져옴)
        
    Returns:
        Brave Search 도구 함수
    """
    try:
        from langchain_community.tools import BraveSearch
        
        api_key = api_key or os.getenv("BRAVE_API_KEY")
        if not api_key:
            print("⚠️  BRAVE_API_KEY가 설정되지 않았습니다.")
            print("   Brave Search 도구를 사용하려면 BRAVE_API_KEY를 설정하세요.")
            return None
        
        # BraveSearch 도구 초기화
        brave_search_instance = BraveSearch.from_api_key(
            api_key=api_key,
            search_kwargs={"count": 5}  # 상위 5개 결과만 가져오기
        )
        
        @tool("brave_search")
        def brave_search(query: str) -> str:
            """Brave Search API를 사용하여 웹에서 정보를 검색합니다.
            
            Args:
                query: 검색할 키워드나 질문
                
            Returns:
                검색 결과 문자열
            """
            try:
                # 검색 실행
                search_results = brave_search_instance.run(query)
                
                # 결과가 문자열인 경우 JSON 파싱 시도
                if isinstance(search_results, str):
                    try:
                        results_data = json.loads(search_results)
                    except json.JSONDecodeError:
                        # JSON이 아닌 경우 그대로 반환
                        return f"🔍 검색 결과:\n{search_results}"
                else:
                    results_data = search_results
                
                # 결과 포맷팅
                if isinstance(results_data, list) and len(results_data) > 0:
                    formatted_results = f"🔍 '{query}' 검색 결과:\n\n"
                    
                    for i, result in enumerate(results_data[:5], 1):  # 상위 5개만 표시
                        if isinstance(result, dict):
                            title = result.get('title', '제목 없음')
                            link = result.get('link', '')
                            snippet = result.get('snippet', '요약 없음')
                            
                            formatted_results += f"{i}. **{title}**\n"
                            formatted_results += f"   📎 {link}\n"
                            formatted_results += f"   📝 {snippet}\n\n"
                        else:
                            formatted_results += f"{i}. {str(result)}\n\n"
                    
                    formatted_results += f"💡 총 {len(results_data)}개의 검색 결과를 찾았습니다."
                    return formatted_results
                
                else:
                    return f"🔍 '{query}'에 대한 검색 결과를 찾을 수 없습니다."
                    
            except Exception as e:
                return f"❌ 검색 중 오류 발생: {str(e)}"
        
        return brave_search
        
    except ImportError:
        print("⚠️  langchain-community 패키지가 설치되지 않았습니다.")
        print("   pip install langchain-community 또는 uv add langchain-community")
        return None
    except Exception as e:
        print(f"⚠️  Brave Search 도구 생성 중 오류: {str(e)}")
        return None


# 추가 커스텀 도구 예시
@tool("calculate")
def calculator_tool(expression: str) -> str:
    """수학 계산을 수행합니다.
    
    Args:
        expression: 계산할 수식 (예: "2 + 2", "10 * 5")
        
    Returns:
        계산 결과
    """
    try:
        # 간단한 계산만 허용 (보안 고려)
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return "❌ 허용되지 않은 문자가 포함되어 있습니다."
        
        result = eval(expression)
        return f"결과: {result}"
    except Exception as e:
        return f"❌ 계산 오류: {str(e)}"


# ============================================
# MCP 도구 로드 함수
# ============================================

def load_mcp_config() -> dict:
    """mcp_config.json 파일 로드"""
    config_path = Path(project_root) / "mcp_config.json"
    
    if not config_path.exists():
        return {"servers": {}}
    
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ mcp_config.json 로드 실패: {e}")
        return {"servers": {}}


def get_enabled_mcp_server_configs() -> dict:
    """활성화된 MCP 서버 설정만 반환 (enabled 필드 제거)"""
    config = load_mcp_config()
    servers = config.get("servers", {})
    
    enabled_configs = {}
    for name, server_config in servers.items():
        if server_config.get("enabled", False):
            # enabled 필드는 MultiServerMCPClient에 전달하지 않음
            cleaned_config = {k: v for k, v in server_config.items() if k != "enabled"}
            enabled_configs[name] = cleaned_config
    
    return enabled_configs


async def load_mcp_tools_async() -> List[Any]:
    """비동기로 MCP 도구 로드
    
    Returns:
        MCP 도구 리스트 (LangChain 도구 형식)
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        server_configs = get_enabled_mcp_server_configs()
        
        if not server_configs:
            print("⚠️ 활성화된 MCP 서버가 없습니다.")
            return []
        
        # MultiServerMCPClient 생성
        mcp_client = MultiServerMCPClient(server_configs)
        
        # MCP 도구 가져오기
        tools = await mcp_client.get_tools()
        
        print(f"✅ MCP 도구 로드 완료: {len(tools)}개")
        return tools
        
    except ImportError:
        print("⚠️ langchain-mcp-adapters가 설치되지 않았습니다.")
        print("   MCP 도구를 사용하려면 설치하세요: pip install langchain-mcp-adapters")
        return []
    except Exception as e:
        print(f"⚠️ MCP 도구 로드 실패: {e}")
        return []


def load_mcp_tools_sync() -> List[Any]:
    """동기로 MCP 도구 로드 (비동기 함수 래핑)
    
    Returns:
        MCP 도구 리스트 (LangChain 도구 형식)
    """
    try:
        # 이벤트 루프가 실행 중인지 확인
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프에서는 경고
                print("⚠️ 비동기 컨텍스트에서는 load_mcp_tools_async()를 사용하세요.")
                return []
        except RuntimeError:
            # 루프가 없는 경우 새로 생성
            pass
        
        # 새 루프에서 실행
        return asyncio.run(load_mcp_tools_async())
    except Exception as e:
        print(f"⚠️ MCP 도구 로드 실패: {e}")
        return []


def _get_allowed_directories() -> List[str]:
    """MCP 설정에서 허용된 디렉토리 목록 가져오기
    
    CSV 도구는 Filesystem MCP와 동일한 허용 디렉토리를 사용합니다.
    또한 프로젝트 루트도 항상 허용합니다 (CSV 파일이 프로젝트 루트에 있을 수 있음).
    
    Returns:
        허용된 디렉토리 경로 리스트
    """
    allowed_dirs = []
    
    try:
        # MCP 설정에서 허용된 디렉토리 읽기
        config = load_mcp_config()
        filesystem_config = config.get("servers", {}).get("filesystem", {})
        args = filesystem_config.get("args", [])
        
        # args에서 디렉토리 경로 추출 (서버 이름 이후의 인자들)
        # 형식: ["-y", "@modelcontextprotocol/server-filesystem", "/path1", "/path2"]
        for arg in args:
            if arg.startswith("/") or arg.startswith(os.path.expanduser("~")):
                allowed_dirs.append(Path(arg).expanduser().resolve())
    except Exception:
        pass
    
    # 프로젝트 루트도 항상 허용 (CSV 파일이 프로젝트 루트에 있을 수 있음)
    project_root_path = Path(project_root).resolve()
    if project_root_path not in allowed_dirs:
        allowed_dirs.append(project_root_path)
    
    # 중복 제거 및 정규화
    unique_dirs = []
    seen = set()
    for d in allowed_dirs:
        d_path = Path(d).resolve()
        d_str = str(d_path)
        if d_str not in seen:
            seen.add(d_str)
            unique_dirs.append(d_str)
    
    # 프로젝트 루트 추가 (중복 체크)
    project_root_str = str(project_root_path)
    if project_root_str not in seen:
        unique_dirs.append(project_root_str)
    
    return unique_dirs if unique_dirs else [project_root_str]


def _is_csv_path_allowed(filepath: Path) -> bool:
    """CSV 파일 경로가 허용된 디렉토리 내에 있는지 확인
    
    Args:
        filepath: 확인할 파일 경로
        
    Returns:
        허용된 디렉토리 내에 있으면 True, 아니면 False
    """
    try:
        resolved_path = filepath.resolve()
        resolved_path_str = str(resolved_path)
        allowed_dirs = _get_allowed_directories()
        
        # 허용된 디렉토리 중 하나라도 경로의 시작 부분과 일치하는지 확인
        for allowed_dir in allowed_dirs:
            allowed_dir_resolved = str(Path(allowed_dir).resolve())
            # 경로가 허용된 디렉토리로 시작하는지 확인
            if resolved_path_str.startswith(allowed_dir_resolved):
                return True
        return False
    except Exception as e:
        # 디버깅을 위해 예외 정보 출력
        print(f"⚠️ 경로 검사 오류: {e}")
        return False


def get_csv_tools() -> List[Any]:
    """CSV 분석에 필요한 도구 목록 반환 (내부 구현)
    
    Returns:
        CSV 도구 리스트 (read_csv_metadata, read_csv_chunk, filter_csv, csv_summary_stats)
    """
    try:
        import pandas as pd
    except ImportError:
        print("⚠️ pandas가 설치되지 않았습니다.")
        print("   pip install pandas 또는 uv add pandas")
        return []
    
    @tool("read_csv_metadata")
    def read_csv_metadata_tool(filepath: str) -> str:
        """[CSV 파일 전용 도구] CSV 파일(.csv)의 메타데이터를 조회합니다. 파일명이 .csv로 끝나거나 CSV 파일이라고 언급되면 이 도구를 사용하세요.
        
        ⚠️🚨 매우 중요: CSV 파일을 읽을 때는 반드시 이 도구를 사용하세요!
        ❌ read_file, mcp_read_file, mcp_read_text_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
        ❌ CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생합니다!
        
        파일 크기, 행 수, 컬럼 정보 등을 빠르게 파악할 수 있습니다.
        대용량 파일의 경우 샘플 데이터만 읽어 구조를 파악합니다.
        
        Args:
            filepath: CSV 파일 경로 (예: "DESeq2_counts.csv", "data/sales.csv", "/path/to/file.csv")
                     상대 경로 또는 절대 경로 모두 지원합니다.
            
        Returns:
            파일 크기, 컬럼 정보, 샘플 데이터를 포함한 메타데이터 문자열
            
        예시:
            read_csv_metadata("DESeq2_counts.csv")  # CSV 파일의 구조 확인
            read_csv_metadata("/path/to/data.csv")  # 절대 경로도 지원
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
            if not path.exists():
                return f"❌ 파일이 존재하지 않습니다: {filepath}"
            
            if not path.is_file():
                return f"❌ 경로가 파일이 아닙니다: {filepath}"
            
            # 파일 크기 확인
            file_size = path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # 첫 100행만 읽어서 구조 파악 (메모리 효율적)
            try:
                df_sample = pd.read_csv(path, nrows=100)
                
                metadata_info = f"""📊 CSV 파일 메타데이터: {filepath}

📏 파일 정보:
- 파일 크기: {file_size_mb:.2f} MB ({file_size:,} bytes)
- 샘플 행 수: {len(df_sample)} 행

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
                numeric_cols = df_sample.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_cols) > 0:
                    metadata_info += f"\n\n📈 수치형 컬럼 통계:\n"
                    metadata_info += df_sample[numeric_cols].describe().to_string()
                
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
        """[CSV 파일 전용 도구] CSV 파일(.csv)의 일부만 읽어 반환합니다. 파일명이 .csv로 끝나거나 CSV 파일이라고 언급되면 이 도구를 사용하세요.
        
        ⚠️🚨 매우 중요: CSV 파일을 읽을 때는 반드시 이 도구를 사용하세요!
        ❌ read_file, mcp_read_file, mcp_read_text_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
        ❌ CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생합니다!
        
        대용량 파일의 경우 메모리 효율적으로 특정 부분만 읽을 수 있습니다.
        
        Args:
            filepath: CSV 파일 경로 (예: "DESeq2_counts.csv", "/path/to/file.csv")
                     상대 경로 또는 절대 경로 모두 지원합니다.
            nrows: 읽을 행 수 (None이면 전체, 그러나 표시는 max_display_rows로 제한)
            skiprows: 건너뛸 행 수 (시작 위치)
            usecols: 읽을 컬럼 목록 (None이면 전체 컬럼)
            max_display_rows: 실제로 표시할 최대 행 수 (기본값: 50)
            
        Returns:
            CSV 데이터의 문자열 표현 (표시 행 수는 max_display_rows로 제한됨)
            
        예시:
            read_csv_chunk("DESeq2_counts.csv", nrows=100)  # 상위 100행 읽기
            read_csv_chunk("/path/to/data.csv", nrows=50)  # 절대 경로도 지원
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
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
        """[CSV 파일 전용 도구] CSV 파일(.csv)에 필터 조건을 적용합니다. 파일명이 .csv로 끝나거나 CSV 파일이라고 언급되면 이 도구를 사용하세요.
        
        ⚠️🚨 매우 중요: CSV 파일을 필터링할 때는 반드시 이 도구를 사용하세요!
        ❌ read_file, mcp_read_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
        ❌ CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생합니다!
        
        pandas query 문자열을 사용하여 복잡한 필터링을 수행할 수 있습니다.
        대용량 파일의 경우 청크 단위로 처리하여 메모리 효율적으로 동작합니다.
        
        Args:
            filepath: 입력 CSV 파일 경로 (예: "DESeq2_counts.csv", "/path/to/file.csv")
                     상대 경로 또는 절대 경로 모두 지원합니다.
            filter_query: pandas query 문자열 (예: "column1 > 100 and column2 == 'value'")
            output_filepath: 필터링된 결과를 저장할 파일 경로 (None이면 새 파일 생성하지 않음)
            max_results: 최대 반환/표시 행 수 (기본값: 1000)
            
        Returns:
            필터링 결과 요약 및 샘플 데이터
            
        예시:
            filter_csv("DESeq2_counts.csv", "value > 1000")  # 값이 1000보다 큰 행 필터링
            filter_csv("/path/to/data.csv", "column > 100")  # 절대 경로도 지원
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
            if not path.exists():
                return f"❌ 파일이 존재하지 않습니다: {filepath}"
            
            # 파일 크기 확인하여 처리 전략 결정
            file_size = path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # 파일 크기에 따라 처리 전략 선택
            if file_size_mb < 10:
                # 소형 파일: 전체 읽기
                df = pd.read_csv(path)
                filtered_df = df.query(filter_query)
                matched_count = len(filtered_df)
                display_df = filtered_df.head(max_results)
            else:
                # 대형 파일: 청크 단위 처리
                chunks = []
                total_matched = 0
                
                for chunk in pd.read_csv(path, chunksize=10000):
                    try:
                        filtered_chunk = chunk.query(filter_query)
                        if len(filtered_chunk) > 0:
                            total_matched += len(filtered_chunk)
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
                
                # 보안: 허용된 디렉토리 외부 접근 제한
                if not _is_csv_path_allowed(output_path):
                    allowed_dirs = _get_allowed_directories()
                    result += f"\n⚠️ 출력 파일 경로가 허용된 디렉토리 외부여서 저장하지 않았습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
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
        """[CSV 파일 전용 도구] CSV 파일(.csv)의 요약 통계를 계산합니다. 파일명이 .csv로 끝나거나 CSV 파일이라고 언급되면 이 도구를 사용하세요.
        
        ⚠️🚨 매우 중요: CSV 파일의 통계를 계산할 때는 반드시 이 도구를 사용하세요!
        ❌ read_file, mcp_read_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
        ❌ CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생합니다!
        
        수치형 컬럼에 대한 기본 통계 정보를 제공합니다.
        
        Args:
            filepath: CSV 파일 경로 (예: "DESeq2_counts.csv", "/path/to/file.csv")
                     상대 경로 또는 절대 경로 모두 지원합니다.
            columns: 통계를 계산할 컬럼 목록 (None이면 모든 수치형 컬럼)
            
        Returns:
            요약 통계 정보 (mean, std, min, max, quartiles 등)
            
        예시:
            csv_summary_stats("DESeq2_counts.csv")  # 모든 수치형 컬럼의 통계 계산
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
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
    
    return [
        read_csv_metadata_tool,
        read_csv_chunk_tool,
        filter_csv_tool,
        csv_summary_stats_tool
    ]


def get_plan_tools() -> List[Any]:
    """Plan 저장/로드 도구 반환
    
    Manus, Anthropic 등에서 사용하는 offload context 패턴을 구현합니다.
    Plan을 MD 파일로 저장하고 불러올 수 있습니다.
    
    Returns:
        Plan 도구 리스트 (save_plan, load_plan, format_plan)
    """
    from datetime import datetime
    
    @tool("save_plan")
    def save_plan_tool(plan_content: str, filepath: str = "plan.md") -> str:
        """Plan을 MD 파일로 저장합니다. 복잡한 작업의 계획을 파일로 저장하여 세션 간 공유하거나 컨텍스트를 오프로드할 수 있습니다.
        
        ⚠️ 중요: 복잡한 멀티 스텝 작업의 경우, write_todos로 작업을 분해한 후 이 도구를 사용하여 plan을 저장하세요.
        
        Args:
            plan_content: 저장할 plan 내용 (마크다운 형식)
            filepath: 저장할 파일 경로 (기본값: plan.md)
                     상대 경로 또는 절대 경로 모두 지원합니다.
        
        Returns:
            저장 완료 메시지 및 파일 경로
        
        예시:
            save_plan("# 작업 계획\\n- [ ] 작업 1\\n- [ ] 작업 2", "my_plan.md")
            save_plan(plan_content, "plan.md")  # 기본 경로 사용
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):  # CSV 도구와 동일한 보안 체크 사용
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
            # 타임스탬프 추가 (선택적)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"<!-- Plan saved at: {timestamp} -->\n\n"
            full_content = header + plan_content
            
            # 파일 저장
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(full_content, encoding='utf-8')
            
            file_size = path.stat().st_size
            return f"✅ Plan이 저장되었습니다:\n📄 파일: {filepath}\n📏 크기: {file_size:,} bytes\n💾 저장 시간: {timestamp}"
            
        except PermissionError:
            return f"❌ 권한이 없어 {filepath} 파일을 저장할 수 없습니다."
        except Exception as e:
            return f"❌ Plan 저장 중 오류 발생: {str(e)}"
    
    @tool("load_plan")
    def load_plan_tool(filepath: str = "plan.md") -> str:
        """MD 파일에서 plan을 로드합니다. 이전 세션의 plan을 불러와서 작업을 계속할 수 있습니다.
        
        ⚠️ 중요: 이전 세션에서 저장한 plan을 불러와서 작업을 계속하려면 이 도구를 사용하세요.
        
        Args:
            filepath: 로드할 파일 경로 (기본값: plan.md)
                     상대 경로 또는 절대 경로 모두 지원합니다.
        
        Returns:
            Plan 내용 (마크다운 형식)
        
        예시:
            load_plan("my_plan.md")
            load_plan("plan.md")  # 기본 경로 사용
        """
        try:
            path = Path(filepath).expanduser().resolve()
            
            # 보안: 허용된 디렉토리 외부 접근 제한
            if not _is_csv_path_allowed(path):
                allowed_dirs = _get_allowed_directories()
                return f"❌ 보안: {filepath} 파일에 접근할 수 없습니다.\n허용된 디렉토리: {', '.join(allowed_dirs)}"
            
            if not path.exists():
                return f"❌ 파일이 존재하지 않습니다: {filepath}"
            
            if not path.is_file():
                return f"❌ 경로가 파일이 아닙니다: {filepath}"
            
            # 파일 읽기
            content = path.read_text(encoding='utf-8')
            file_size = path.stat().st_size
            modified_time = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            return f"""✅ Plan이 로드되었습니다:

📄 파일: {filepath}
📏 크기: {file_size:,} bytes
🕒 수정 시간: {modified_time}

📋 Plan 내용:
{content}
"""
            
        except PermissionError:
            return f"❌ 권한이 없어 {filepath} 파일을 읽을 수 없습니다."
        except Exception as e:
            return f"❌ Plan 로드 중 오류 발생: {str(e)}"
    
    @tool("format_plan")
    def format_plan_tool(todos: str) -> str:
        """write_todos 도구의 결과를 MD 형식으로 변환합니다. Plan을 저장하기 전에 형식화하는 데 사용합니다.
        
        ⚠️ 중요: write_todos 도구를 사용한 후, 이 도구를 사용하여 plan을 마크다운 형식으로 변환한 다음 save_plan 도구로 저장하세요.
        
        Args:
            todos: write_todos 도구의 결과 (JSON 문자열 또는 문자열)
                   JSON 형식: [{"task": "작업 1", "status": "pending"}, ...]
                   또는 일반 문자열 형식도 지원
        
        Returns:
            마크다운 형식의 plan 문자열
        
        예시:
            format_plan('[{"task": "작업 1", "status": "pending"}, {"task": "작업 2", "status": "completed"}]')
        """
        try:
            import json
            
            # JSON 파싱 시도
            try:
                todos_data = json.loads(todos) if isinstance(todos, str) else todos
            except json.JSONDecodeError:
                # JSON이 아닌 경우 일반 문자열로 처리
                return f"""# 작업 계획

{todos}

💡 Tip: write_todos 도구의 결과를 JSON 형식으로 전달하면 더 구조화된 plan을 생성할 수 있습니다.
"""
            
            # 마크다운 형식으로 변환
            if not isinstance(todos_data, list):
                return f"❌ 잘못된 형식입니다. todos는 리스트여야 합니다.\n받은 데이터: {type(todos_data)}"
            
            md_content = "# 작업 계획\n\n"
            
            pending_count = 0
            completed_count = 0
            
            for i, todo in enumerate(todos_data, 1):
                if isinstance(todo, dict):
                    task = todo.get("task", todo.get("description", f"작업 {i}"))
                    status = todo.get("status", "pending")
                    is_completed = status == "completed" or status == "done" or todo.get("completed", False)
                    
                    checkbox = "- [x]" if is_completed else "- [ ]"
                    md_content += f"{checkbox} {task}\n"
                    
                    if is_completed:
                        completed_count += 1
                    else:
                        pending_count += 1
                elif isinstance(todo, str):
                    md_content += f"- [ ] {todo}\n"
                    pending_count += 1
                else:
                    md_content += f"- [ ] {str(todo)}\n"
                    pending_count += 1
            
            md_content += f"\n## 진행 상황\n\n"
            md_content += f"- ✅ 완료: {completed_count}개\n"
            md_content += f"- ⏳ 진행 중: {pending_count}개\n"
            md_content += f"- 📊 전체: {len(todos_data)}개\n"
            
            return md_content
            
        except Exception as e:
            return f"❌ Plan 형식화 중 오류 발생: {str(e)}\n원본 데이터: {str(todos)[:200]}"
    
    return [
        save_plan_tool,
        load_plan_tool,
        format_plan_tool
    ]


def get_all_tools(include_mcp: bool = False, include_csv: bool = False, include_plan: bool = True) -> List[Any]:
    """모든 도구 가져오기 (커스텀 도구 + CSV 도구 + MCP 도구 + Plan 도구)
    
    Args:
        include_mcp: MCP 도구 포함 여부
        include_csv: CSV 도구 포함 여부
        include_plan: Plan 도구 포함 여부 (기본값: True)
        
    Returns:
        도구 리스트
    """
    tools = []
    
    # Brave Search 도구 추가
    brave_tool = create_brave_search_tool()
    if brave_tool:
        tools.append(brave_tool)
    
    # Plan 도구 추가 (기본적으로 포함)
    if include_plan:
        plan_tools = get_plan_tools()
        tools.extend(plan_tools)
        if plan_tools:
            print(f"   Plan 도구: {len(plan_tools)}개 추가됨 (save_plan, load_plan, format_plan)")
    
    # CSV 도구 추가
    if include_csv:
        csv_tools = get_csv_tools()
        tools.extend(csv_tools)
        if csv_tools:
            print(f"   CSV 도구: {len(csv_tools)}개 추가됨")
    
    # MCP 도구 추가
    if include_mcp:
        mcp_tools = load_mcp_tools_sync()
        tools.extend(mcp_tools)
    
    return tools


# ============================================
# CSV Middleware 클래스
# ============================================

# ============================================
# Subagent 정의 헬퍼 함수
# ============================================

def create_research_subagent(
    search_tool=None,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """연구 전용 서브에이전트 생성
    
    웹 검색을 통한 심층 연구 작업을 수행하는 서브에이전트입니다.
    컨텍스트 격리를 통해 메인 에이전트의 컨텍스트를 깨끗하게 유지합니다.
    
    Args:
        search_tool: 검색 도구 (None이면 자동으로 Brave Search 도구 생성)
        model: 서브에이전트용 모델 (None이면 메인 에이전트 모델 사용)
        api_key: API 키 (검색 도구 생성 시 필요)
        
    Returns:
        연구 서브에이전트 딕셔너리
        
    예시:
        from deepagent.tools import create_research_subagent
        
        research_subagent = create_research_subagent()
        agent = DeepAgentLibrary(subagents=[research_subagent])
    """
    # 검색 도구가 없으면 자동 생성
    if search_tool is None:
        search_tool = create_brave_search_tool(api_key=api_key)
        if not search_tool:
            print("⚠️ 검색 도구를 생성할 수 없습니다. BRAVE_API_KEY를 확인하세요.")
            return None
    
    return {
        "name": "research-agent",
        "description": "웹 검색을 통한 심층 연구 작업을 수행합니다. 복잡한 연구 질문이나 여러 검색이 필요한 경우 이 서브에이전트를 사용하세요.",
        "system_prompt": """당신은 전문 연구원입니다. 웹 검색을 통해 정보를 수집하고 종합적인 보고서를 작성합니다.

**작업 절차:**
1. 연구 질문을 검색 가능한 쿼리로 분해하세요
2. brave_search 도구를 사용하여 관련 정보를 수집하세요
3. 수집한 정보를 종합하여 간결한 요약을 작성하세요
4. 출처를 명시하세요

**출력 형식:**
- 요약 (2-3 문단)
- 주요 발견사항 (불릿 포인트)
- 출처 (URL 포함)

**중요:** 응답은 500단어 이하로 유지하여 컨텍스트를 깨끗하게 유지하세요. 원시 검색 결과를 모두 포함하지 마세요.""",
        "tools": [search_tool] if search_tool else [],
        "model": model  # None이면 메인 에이전트 모델 사용
    }


def create_csv_analysis_subagent(model: Optional[str] = None) -> Dict[str, Any]:
    """CSV 분석 전용 서브에이전트 생성
    
    CSV 파일 분석 작업을 전문적으로 수행하는 서브에이전트입니다.
    CSV 전용 도구만 사용하여 안전하게 데이터를 분석합니다.
    
    Args:
        model: 서브에이전트용 모델 (None이면 메인 에이전트 모델 사용)
        
    Returns:
        CSV 분석 서브에이전트 딕셔너리
        
    예시:
        from deepagent.tools import create_csv_analysis_subagent
        
        csv_subagent = create_csv_analysis_subagent()
        agent = DeepAgentLibrary(subagents=[csv_subagent])
    """
    csv_tools = get_csv_tools()
    if not csv_tools:
        print("⚠️ CSV 도구를 사용할 수 없습니다. pandas가 설치되어 있는지 확인하세요.")
        return None
    
    return {
        "name": "csv-analyzer",
        "description": "CSV 파일 분석을 전문적으로 수행합니다. CSV 파일의 메타데이터 조회, 데이터 필터링, 통계 계산 등을 수행합니다.",
        "system_prompt": """당신은 데이터 분석 전문가입니다. CSV 파일을 효율적으로 분석하고 인사이트를 도출합니다.

**⚠️ 매우 중요 - CSV 파일 처리 규칙:**
- CSV 파일(.csv)을 읽을 때는 반드시 CSV 전용 도구만 사용하세요!
- read_csv_metadata: 파일 구조 확인
- read_csv_chunk: 데이터 일부 읽기 (대용량 파일 처리)
- filter_csv: 조건에 맞는 데이터 필터링
- csv_summary_stats: 통계 정보 계산

**❌ 절대 사용 금지:**
- read_file, mcp_read_file 등의 일반 파일 읽기 도구는 CSV 파일에 사용 금지!
- CSV 파일에 일반 파일 읽기 도구를 사용하면 오류가 발생합니다!

**작업 절차:**
1. read_csv_metadata로 파일 구조를 먼저 확인하세요
2. 필요한 경우 read_csv_chunk로 데이터를 읽으세요
3. 필터링이 필요하면 filter_csv를 사용하세요
4. 통계가 필요하면 csv_summary_stats를 사용하세요

**출력 형식:**
- 분석 결과 요약 (3-5 불릿 포인트)
- 주요 통계 정보
- 발견사항 및 권장사항

**중요:** 응답은 300단어 이하로 유지하고, 원시 데이터를 모두 포함하지 마세요.""",
        "tools": csv_tools,
        "model": model  # None이면 메인 에이전트 모델 사용
    }


def create_data_collector_subagent(
    search_tool=None,
    mcp_tools: Optional[List] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """데이터 수집 전용 서브에이전트 생성
    
    다양한 소스에서 데이터를 수집하는 서브에이전트입니다.
    웹 검색, MCP 도구 등을 활용하여 데이터를 수집합니다.
    
    Args:
        search_tool: 검색 도구 (None이면 자동 생성)
        mcp_tools: MCP 도구 리스트 (선택사항)
        model: 서브에이전트용 모델
        api_key: API 키 (검색 도구 생성 시 필요)
        
    Returns:
        데이터 수집 서브에이전트 딕셔너리
    """
    tools = []
    
    # 검색 도구 추가
    if search_tool is None:
        search_tool = create_brave_search_tool(api_key=api_key)
    if search_tool:
        tools.append(search_tool)
    
    # MCP 도구 추가
    if mcp_tools:
        tools.extend(mcp_tools)
    
    return {
        "name": "data-collector",
        "description": "다양한 소스에서 데이터를 수집합니다. 웹 검색, API 호출, 데이터베이스 쿼리 등을 통해 필요한 데이터를 수집합니다.",
        "system_prompt": """당신은 데이터 수집 전문가입니다. 다양한 소스에서 필요한 데이터를 효율적으로 수집합니다.

**작업 절차:**
1. 수집할 데이터의 요구사항을 명확히 파악하세요
2. 적절한 도구를 선택하여 데이터를 수집하세요
3. 수집한 데이터를 정리하고 요약하세요

**출력 형식:**
- 수집된 데이터 요약
- 데이터 소스 정보
- 다음 단계 제안

**중요:** 응답은 400단어 이하로 유지하고, 원시 데이터를 모두 포함하지 마세요.""",
        "tools": tools,
        "model": model
    }


def create_report_writer_subagent(model: Optional[str] = None) -> Dict[str, Any]:
    """보고서 작성 전용 서브에이전트 생성
    
    분석 결과를 바탕으로 전문적인 보고서를 작성하는 서브에이전트입니다.
    
    Args:
        model: 서브에이전트용 모델
        
    Returns:
        보고서 작성 서브에이전트 딕셔너리
    """
    return {
        "name": "report-writer",
        "description": "분석 결과를 바탕으로 전문적인 보고서를 작성합니다. 데이터 분석 결과, 연구 결과 등을 구조화된 보고서로 변환합니다.",
        "system_prompt": """당신은 전문 보고서 작성자입니다. 분석 결과를 바탕으로 명확하고 구조화된 보고서를 작성합니다.

**보고서 구조:**
1. 요약 (Executive Summary)
2. 주요 발견사항
3. 상세 분석
4. 결론 및 권장사항

**작성 규칙:**
- 명확하고 간결한 문체 사용
- 데이터와 사실에 기반한 분석
- 시각적 요소(표, 리스트) 활용
- 한글로 작성

**중요:** 보고서는 1000단어 이하로 유지하세요.""",
        "tools": [],  # 보고서 작성에는 특별한 도구가 필요 없음
        "model": model
    }


class CSVMiddleware(AgentMiddleware):
    """CSV 파일 분석을 위한 Middleware
    
    CSV 전용 도구만 제공하여 subagent가 CSV 파일을 안전하게 분석할 수 있도록 합니다.
    DeepAgents의 AgentMiddleware 패턴을 따릅니다.
    
    사용 예시:
        from deepagent.tools import CSVMiddleware
        
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            middleware=[CSVMiddleware()]
        )
    """
    # CSV 도구를 클래스 레벨 속성으로 정의
    # get_csv_tools()가 반환하는 도구들을 사용
    tools = []  # 동적으로 로드됨
    
    def __init__(self):
        """CSVMiddleware 초기화
        
        CSV 도구를 동적으로 로드하여 tools 속성에 설정합니다.
        """
        super().__init__()
        # CSV 도구 동적 로드
        csv_tools = get_csv_tools()
        if csv_tools:
            # 클래스 레벨 속성 업데이트 (인스턴스별로 사용 가능)
            self.tools = csv_tools
        else:
            self.tools = []

