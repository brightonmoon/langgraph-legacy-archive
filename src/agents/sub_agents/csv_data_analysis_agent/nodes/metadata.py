"""
CSV 메타데이터 읽기 노드

CSV 파일의 메타데이터를 읽어서 분석에 사용합니다.
"""

from __future__ import annotations

from typing import Callable, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..agent import CSVAnalysisState
else:
    # 런타임에 타입을 사용하지 않으므로 Any로 대체
    CSVAnalysisState = Any
from ..utils import resolve_csv_files, extract_csv_parameters_from_messages
from src.tools.csv_tools import read_csv_metadata_tool


def create_read_csv_metadata_node(orchestrator_model: Any) -> Callable[[CSVAnalysisState], CSVAnalysisState]:
    """CSV 메타데이터 읽기 노드 생성
    
    Args:
        orchestrator_model: Orchestrator LLM 모델 (파라미터 추출용)
        
    Returns:
        CSV 메타데이터 읽기 노드 함수
    """
    def read_csv_metadata_node(state: CSVAnalysisState) -> CSVAnalysisState:
        """노드 1: CSV 파일 메타데이터 읽기
        
        단일 파일 또는 여러 파일을 읽을 수 있도록 개선됨
        파라미터가 없으면 메시지에서 자동으로 추출 (내부 파라미터화)
        
        Phase 2: resolve_csv_files() 통합 함수를 사용하여 단일/다중 파일 모드 통합 처리
        """
        print("📊 [Node 1] CSV 파일 메타데이터 읽기 중...")
        
        CSV_file_path = state.get("CSV_file_path", "")
        CSV_file_paths = state.get("CSV_file_paths", [])
        query = state.get("query", "")
        messages = state.get("messages", [])
        
        # 파라미터가 없으면 메시지에서 자동 추출 (내부 파라미터화)
        if (not CSV_file_path and not CSV_file_paths) or not query:
            print("📥 파라미터 자동 추출 중...")
            extracted_params = extract_csv_parameters_from_messages(
                messages=messages,
                csv_file_path=CSV_file_path,
                csv_file_paths=CSV_file_paths,
                query=query,
                model=orchestrator_model  # Orchestrator LLM 기반 추출 사용
            )
            CSV_file_path = extracted_params.get("CSV_file_path", CSV_file_path)
            CSV_file_paths = extracted_params.get("CSV_file_paths", CSV_file_paths)
            query = extracted_params.get("query", query)
            
            if CSV_file_path:
                print(f"✅ 파라미터 추출 완료 (단일 파일): {CSV_file_path[:50]}...")
            elif CSV_file_paths:
                print(f"✅ 파라미터 추출 완료 (다중 파일): {len(CSV_file_paths)}개 파일")
            else:
                print("⚠️ CSV 파일 경로를 추출할 수 없습니다.")
        
        # Phase 2: 통합 함수를 사용하여 파일 경로 해석
        # state를 업데이트하여 추출된 파라미터 반영
        updated_state = {**state}
        if CSV_file_path:
            updated_state["CSV_file_path"] = CSV_file_path
        if CSV_file_paths:
            updated_state["CSV_file_paths"] = CSV_file_paths
        if query:
            updated_state["query"] = query
        
        # 통합 함수로 파일 경로 리스트 가져오기
        csv_file_paths_list = resolve_csv_files(updated_state)
        
        # CSV 파일이 없으면 에러 반환
        if not csv_file_paths_list:
            return {
                "errors": ["CSV 파일 경로가 제공되지 않았거나 파일을 찾을 수 없습니다. 메시지에 CSV 파일명을 포함해주세요."],
                "status": "error"
            }
        
        try:
            metadata_dict = {}
            errors = []
            
            # 각 파일의 메타데이터 읽기 (단일/다중 파일 모드 통합 처리)
            for file_path in csv_file_paths_list:
                try:
                    # Path 객체를 문자열로 변환하여 메타데이터 읽기
                    file_path_str = str(file_path)
                    metadata = read_csv_metadata_tool.invoke({"filepath": file_path_str})
                    metadata_dict[file_path_str] = metadata
                    print(f"✅ 메타데이터 읽기 완료: {file_path.name}")
                except Exception as e:
                    error_msg = f"파일 읽기 실패 ({file_path.name}): {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            
            if not metadata_dict:
                return {
                    "errors": errors if errors else ["모든 CSV 파일 읽기 실패"],
                    "status": "error"
                }
            
            # 단일 파일 모드인 경우 단순 메타데이터 반환
            if len(metadata_dict) == 1:
                file_path_str = list(metadata_dict.keys())[0]
                metadata = metadata_dict[file_path_str]
                
                print(f"✅ CSV 메타데이터 읽기 완료 (단일 파일)")
                
                # 토큰 사용량 초기화
                token_usage = state.get("token_usage", {})
                if not token_usage:
                    token_usage = {
                        "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "by_model": {}
                    }
                
                # 단일 파일 모드: CSV_file_path 사용
                return {
                    "CSV_file_path": file_path_str,  # 추출된 파라미터 저장
                    "query": query,  # 추출된 파라미터 저장
                    "CSV_metadata": metadata,
                    "status": "metadata_read",
                    "call_count": state.get("call_count", 0),
                    "token_usage": token_usage,
                    "error_count": 0  # 에러 카운트 초기화
                }
            
            # 다중 파일 모드: 통합 메타데이터 생성
            combined_metadata_parts = []
            combined_metadata_parts.append("=== 여러 CSV 파일 메타데이터 ===\n")
            for file_path_str, metadata in metadata_dict.items():
                combined_metadata_parts.append(f"\n📁 파일: {Path(file_path_str).name}")
                combined_metadata_parts.append(f"경로: {file_path_str}")
                combined_metadata_parts.append(f"\n{metadata}\n")
                combined_metadata_parts.append("-" * 60)
            
            combined_metadata = "\n".join(combined_metadata_parts)
            
            print(f"✅ CSV 메타데이터 읽기 완료 (다중 파일: {len(metadata_dict)}개)")
            if errors:
                print(f"⚠️ 일부 파일 읽기 실패: {len(errors)}개")
            
            # 토큰 사용량 초기화
            token_usage = state.get("token_usage", {})
            if not token_usage:
                token_usage = {
                    "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    "by_model": {}
                }
            
            # 다중 파일 모드: CSV_file_paths 사용
            return {
                "CSV_file_paths": list(metadata_dict.keys()),  # 추출된 파라미터 저장
                "query": query,  # 추출된 파라미터 저장
                "CSV_metadata": combined_metadata,  # 통합 메타데이터 (단일/다중 파일 모두 지원)
                "status": "metadata_read",
                "call_count": state.get("call_count", 0),
                "errors": errors if errors else None,
                # Phase 1 개선: 반복적 분석을 위한 초기값 설정
                "analysis_iteration_count": state.get("analysis_iteration_count", 0),
                "max_analysis_iterations": state.get("max_analysis_iterations", 3),
                "accumulated_insights": state.get("accumulated_insights", []),
                "token_usage": token_usage,
                "error_count": 0  # 에러 카운트 초기화
            }
        except Exception as e:
            error_msg = f"CSV 파일 읽기 실패: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                "status": "error"
            }
    
    return read_csv_metadata_node

