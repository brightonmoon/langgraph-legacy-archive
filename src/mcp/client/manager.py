"""
MCP Client Manager - Model Context Protocol 클라이언트 관리 모듈 (개선된 버전)
"""

# 표준 라이브러리
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# 서드파티
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ langchain-mcp-adapters가 설치되지 않았습니다. MCP 기능을 사용하려면 설치하세요: pip install langchain-mcp-adapters")

# 로컬 (같은 패키지 내 - 상대 import 허용)
from ..config.manager import get_config_manager

# 로컬 (다른 패키지 - 절대 import)
from src.tools.factory import ToolFactory


class MCPClientManager:
    """MCP 클라이언트 관리자 클래스 (개선된 버전)"""
    
    def __init__(self):
        """MCP 클라이언트 관리자 초기화"""
        self.mcp_client: Optional[MultiServerMCPClient] = None
        self.mcp_tools: List[Any] = []
        self.local_tools = ToolFactory.get_all_tools()
        self.all_tools: List[Any] = []
        self.is_initialized = False
        self.config_manager = get_config_manager()
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
    def get_enabled_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """활성화된 서버 설정 반환"""
        return self.config_manager.get_enabled_servers()
        
    async def initialize_client(self) -> bool:
        """MCP 클라이언트 초기화 (설정 파일 기반)"""
        if not MCP_AVAILABLE:
            self.logger.error("❌ MCP 라이브러리가 설치되지 않았습니다.")
            return False
            
        # 활성화된 서버 설정 가져오기
        server_configs = self.get_enabled_server_configs()
        
        if not server_configs:
            self.logger.warning("⚠️ 활성화된 MCP 서버가 없습니다. 로컬 도구만 사용합니다.")
            self.all_tools = self.local_tools.copy()
            self.is_initialized = True
            return True
            
        try:
            self.logger.info(f"🔧 MCP 클라이언트 초기화 중... ({len(server_configs)}개 서버)")
            
            # 설정 유효성 검사
            errors = self.config_manager.validate_config()
            if errors:
                self.logger.error("❌ MCP 설정에 오류가 있습니다:")
                for error in errors:
                    self.logger.error(f"  - {error}")
                return False
            
            # MultiServerMCPClient 생성
            self.mcp_client = MultiServerMCPClient(server_configs)
            
            # MCP 도구들 로드 (타임아웃 및 재시도 추가)
            import asyncio
            raw_mcp_tools = []
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"🔧 MCP 도구 로드 시도 {attempt + 1}/{max_retries}...")
                    raw_mcp_tools = await asyncio.wait_for(
                        self.mcp_client.get_tools(),
                        timeout=30.0  # 30초 타임아웃
                    )
                    self.logger.info(f"✅ MCP 도구 로드 성공 ({len(raw_mcp_tools)}개)")
                    break  # 성공 시 루프 종료
                    
                except asyncio.TimeoutError:
                    self.logger.error(f"❌ MCP 도구 로드 타임아웃 (시도 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 2초 후 재시도...")
                        await asyncio.sleep(2)
                    else:
                        self.logger.error("❌ MCP 도구 로드 최종 실패")
                        self.logger.warning("⚠️ 로컬 도구만 사용합니다.")
                        self.all_tools = self.local_tools.copy()
                        self.is_initialized = True
                        return False
                        
                except Exception as e:
                    error_type = type(e).__name__
                    self.logger.error(f"❌ MCP 도구 로드 실패 (시도 {attempt + 1}/{max_retries}): {error_type}")
                    if "UnboundLocalError" in str(type(e)):
                        self.logger.error("⚠️ 알려진 버그 발견: UnboundLocalError (GitHub Issue #314)")
                    if attempt < max_retries - 1:
                        self.logger.info("⏳ 2초 후 재시도...")
                        await asyncio.sleep(2)
                    else:
                        self.logger.error("❌ MCP 도구 로드 최종 실패")
                        self.logger.warning("⚠️ 로컬 도구만 사용합니다.")
                        self.all_tools = self.local_tools.copy()
                        self.is_initialized = True
                        return False
            
            # MCP 도구에 접두사 추가하여 이름 충돌 방지
            self.mcp_tools = []
            for tool in raw_mcp_tools:
                # 도구 이름에 mcp_ 접두사 추가
                original_name = tool.name
                tool.name = f"mcp_{original_name}"
                # 도구 설명에도 MCP 표시 추가
                tool.description = f"[MCP] {tool.description}"
                self.mcp_tools.append(tool)
            
            # 모든 도구 통합 (로컬 도구 + MCP 도구)
            self.all_tools = self.local_tools + self.mcp_tools
            
            self.is_initialized = True
            
            self.logger.info(f"✅ MCP 클라이언트 초기화 완료")
            self.logger.info(f"   - 로컬 도구: {len(self.local_tools)}개")
            self.logger.info(f"   - MCP 도구: {len(self.mcp_tools)}개")
            self.logger.info(f"   - 총 도구: {len(self.all_tools)}개")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MCP 클라이언트 초기화 실패: {str(e)}")
            # 실패 시 로컬 도구만 사용
            self.all_tools = self.local_tools.copy()
            self.is_initialized = True
            return False
            
    def get_tools(self) -> List[Any]:
        """사용 가능한 모든 도구 반환"""
        if not self.is_initialized:
            self.logger.warning("⚠️ MCP 클라이언트가 초기화되지 않았습니다.")
            return self.local_tools
            
        return self.all_tools
        
    def get_local_tools(self) -> List[Any]:
        """로컬 도구만 반환"""
        return self.local_tools
        
    def get_mcp_tools(self) -> List[Any]:
        """MCP 도구만 반환"""
        return self.mcp_tools
        
    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """이름으로 도구 찾기"""
        for tool in self.all_tools:
            if tool.name == name:
                return tool
        return None
        
    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """도구 실행"""
        if not self.is_initialized:
            return f"❌ MCP 클라이언트가 초기화되지 않았습니다."
            
        # 로컬 도구인지 확인
        local_tool = None
        for tool in self.local_tools:
            if tool.name == tool_name:
                local_tool = tool
                break
                
        if local_tool:
            # 로컬 도구 실행
            try:
                result = local_tool.invoke(tool_args)
                self.logger.info(f"✅ 로컬 도구 '{tool_name}' 실행 완료")
                return result
            except Exception as e:
                error_msg = f"❌ 로컬 도구 '{tool_name}' 실행 실패: {str(e)}"
                self.logger.error(error_msg)
                return error_msg
        else:
            # MCP 도구 실행
            if not self.mcp_client:
                return f"❌ MCP 클라이언트가 초기화되지 않았습니다."
                
            try:
                # MCP 도구 이름에서 접두사 제거
                original_tool_name = tool_name
                if tool_name.startswith("mcp_"):
                    original_tool_name = tool_name[4:]  # "mcp_" 제거
                
                # MCP 도구는 클라이언트를 통해 실행
                result = await self._execute_mcp_tool(original_tool_name, tool_args)
                self.logger.info(f"✅ MCP 도구 '{tool_name}' 실행 완료")
                return result
            except Exception as e:
                error_msg = f"❌ MCP 도구 '{tool_name}' 실행 실패: {str(e)}"
                self.logger.error(error_msg)
                return error_msg
                
    async def _execute_mcp_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """MCP 도구 실행 (내부 메서드)"""
        try:
            # 실제 MCP 도구 찾기
            tool = None
            for mcp_tool in self.mcp_tools:
                # mcp_ 접두사 제거하여 비교
                clean_name = mcp_tool.name[4:] if mcp_tool.name.startswith("mcp_") else mcp_tool.name
                if clean_name == tool_name:
                    tool = mcp_tool
                    break
            
            if not tool:
                raise ValueError(f"MCP 도구 '{tool_name}'을 찾을 수 없습니다.")
            
            # 실제 도구 실행
            result = await tool.ainvoke(tool_args)
            
            # 결과를 문자열로 변환
            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return str(result)
            else:
                return str(result)
                
        except Exception as e:
            raise Exception(f"MCP 도구 실행 중 오류: {str(e)}")
            
    def get_status(self) -> Dict[str, Any]:
        """MCP 클라이언트 상태 반환"""
        server_status = self.config_manager.get_server_status()
        
        return {
            "mcp_available": MCP_AVAILABLE,
            "initialized": self.is_initialized,
            "local_tools_count": len(self.local_tools),
            "mcp_tools_count": len(self.mcp_tools),
            "total_tools_count": len(self.all_tools),
            "server_status": server_status
        }
        
    def show_tools_info(self) -> None:
        """도구 정보 표시"""
        print(f"\n📚 사용 가능한 도구 정보:")
        print("=" * 50)
        
        # 로컬 도구
        print(f"\n🔧 로컬 도구 ({len(self.local_tools)}개):")
        for tool in self.local_tools:
            print(f"   • {tool.name}: {tool.description}")
            
        # MCP 도구
        if self.mcp_tools:
            print(f"\n🌐 MCP 도구 ({len(self.mcp_tools)}개):")
            for tool in self.mcp_tools:
                print(f"   • {tool.name}: {tool.description}")
        else:
            print(f"\n🌐 MCP 도구: 없음")
            
        print("=" * 50)
        
    def show_server_status(self) -> None:
        """서버 상태 표시"""
        self.config_manager.show_status()
        
    async def cleanup(self) -> None:
        """리소스 정리"""
        if self.mcp_client:
            # MCP 클라이언트 정리 로직
            pass
        self.logger.info("🧹 MCP 클라이언트 정리 완료")


# 전역 MCP 클라이언트 관리자 인스턴스
mcp_manager = MCPClientManager()


def get_mcp_manager() -> MCPClientManager:
    """MCP 클라이언트 관리자 인스턴스 반환"""
    return mcp_manager


if __name__ == "__main__":
    # 테스트 코드
    async def test_mcp_manager():
        manager = get_mcp_manager()
        
        # 서버 상태 표시
        manager.show_server_status()
        
        # 클라이언트 초기화
        await manager.initialize_client()
        
        # 상태 확인
        status = manager.get_status()
        print(f"\n📊 MCP 클라이언트 상태:")
        for key, value in status.items():
            print(f"   {key}: {value}")
            
        # 도구 정보 표시
        manager.show_tools_info()
        
        # 정리
        await manager.cleanup()
        
    # 테스트 실행
    asyncio.run(test_mcp_manager())
