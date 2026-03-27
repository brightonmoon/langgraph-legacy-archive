"""
Tool 팩토리 모듈 - Tool 생성 및 관리
"""

from typing import List
from .calculator import calculator_tool
from .brave_search import brave_search_tool
from .planning import write_todos_tool
from .filesystem import ls_tool, read_file_tool, write_file_tool, edit_file_tool
from .task_tool import task_tool
from .csv_tools import (
    read_csv_metadata_tool,
    read_csv_chunk_tool,
    filter_csv_tool,
    csv_summary_stats_tool
)
from .code_execution import (
    execute_python_code_tool,
    execute_python_file_tool
)


class ToolFactory:
    """Tool 생성 팩토리 클래스"""
    
    @classmethod
    def get_all_tools(cls) -> List:
        """모든 사용 가능한 Tool 목록 반환"""
        return [calculator_tool, brave_search_tool]
    
    @classmethod
    def get_deep_agent_tools(cls) -> List:
        """DeepAgent 전용 도구 목록 반환"""
        filesystem_tools = [ls_tool, read_file_tool, write_file_tool, edit_file_tool]
        return [write_todos_tool] + filesystem_tools + [task_tool]
    
    @classmethod
    def get_all_tools_with_deep(cls) -> List:
        """모든 도구 (DeepAgent 도구 포함) 반환"""
        return cls.get_all_tools() + cls.get_deep_agent_tools()
    
    @classmethod
    def get_csv_tools(cls) -> List:
        """CSV 처리 전용 도구 목록 반환"""
        return [
            read_csv_metadata_tool,
            read_csv_chunk_tool,
            filter_csv_tool,
            csv_summary_stats_tool
        ]
    
    @classmethod
    def get_all_tools_with_csv(cls) -> List:
        """모든 도구 (CSV 도구 포함) 반환"""
        return cls.get_all_tools() + cls.get_deep_agent_tools() + cls.get_csv_tools()
    
    @classmethod
    def get_code_execution_tools(cls) -> List:
        """코드 실행 도구 목록 반환"""
        return [
            execute_python_code_tool,
            execute_python_file_tool
        ]
    
    @classmethod
    def get_csv_analysis_tools(cls) -> List:
        """CSV 분석에 필요한 모든 도구 반환 (CSV + 코드 실행)"""
        return cls.get_csv_tools() + cls.get_code_execution_tools()
    
    @classmethod
    def get_tool_names(cls) -> List[str]:
        """사용 가능한 Tool 이름 목록 반환"""
        return [tool.name for tool in cls.get_all_tools()]
    
    @classmethod
    def get_tool_info(cls) -> dict:
        """Tool 정보 반환"""
        tools_info = {}
        for tool in cls.get_all_tools():
            tools_info[tool.name] = {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema
            }
        return tools_info
    
    @classmethod
    def get_tools_description(cls) -> str:
        """사용 가능한 도구들의 설명 문자열을 동적으로 생성"""
        tools = cls.get_all_tools()
        
        if not tools:
            return "- 사용 가능한 로컬 도구가 없습니다."
        
        description_lines = []
        for tool in tools:
            # 도구 이름과 설명 추출
            tool_name = tool.name
            tool_description = tool.description
            
            # args_schema에서 파라미터 정보 추출
            params_info = ""
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema = tool.args_schema.schema() if hasattr(tool.args_schema, 'schema') else tool.args_schema
                if 'properties' in schema:
                    required_params = schema.get('required', [])
                    params = schema['properties']
                    param_descriptions = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', '')
                        param_desc = param_info.get('description', '')
                        is_required = param_name in required_params
                        if param_desc:
                            param_descriptions.append(f"{param_name} ({param_type}): {param_desc}")
                        else:
                            param_descriptions.append(f"{param_name} ({param_type})")
                    if param_descriptions:
                        params_info = f" - 파라미터: {', '.join(param_descriptions)}"
            
            # 각 도구 설명 라인 생성
            description_lines.append(f"- {tool_name}: {tool_description}{params_info}")
        
        return "\n".join(description_lines)