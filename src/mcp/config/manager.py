"""
MCP 설정 관리자 - mcp_config.json 파일을 활용한 설정 관리
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging


class MCPConfigManager:
    """MCP 설정 관리자 클래스"""
    
    def __init__(self, config_path: str = None):
        """MCP 설정 관리자 초기화"""
        if config_path:
            self.config_path = config_path
        else:
            # 프로젝트 루트 찾기 (mcp_config.json이 있는 디렉토리)
            current_dir = os.path.dirname(__file__)
            # src/mcp/config -> src/mcp -> src -> 프로젝트 루트
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            self.config_path = os.path.join(project_root, "mcp_config.json")
        
        self.config_data: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # 설정 파일 로드
        self.load_config()
    
    def load_config(self) -> bool:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                self.logger.info(f"✅ MCP 설정 파일 로드 완료: {self.config_path}")
                return True
            else:
                self.logger.warning(f"⚠️ MCP 설정 파일이 존재하지 않습니다: {self.config_path}")
                self.config_data = {"servers": {}}
                return False
        except Exception as e:
            self.logger.error(f"❌ 설정 파일 로드 실패: {str(e)}")
            self.config_data = {"servers": {}}
            return False
    
    def save_config(self) -> bool:
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"✅ MCP 설정 파일 저장 완료: {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 파일 저장 실패: {str(e)}")
            return False
    
    def get_enabled_servers(self) -> Dict[str, Dict[str, Any]]:
        """활성화된 서버 설정 반환"""
        servers = self.config_data.get("servers", {})
        enabled_servers = {}
        
        for name, config in servers.items():
            if config.get("enabled", False):
                # enabled 필드를 제거한 설정만 반환
                clean_config = {k: v for k, v in config.items() if k != "enabled"}
                enabled_servers[name] = clean_config
        
        return enabled_servers
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """특정 서버 설정 반환"""
        servers = self.config_data.get("servers", {})
        return servers.get(server_name)
    
    def enable_server(self, server_name: str) -> bool:
        """서버 활성화"""
        if "servers" not in self.config_data:
            self.config_data["servers"] = {}
        
        if server_name not in self.config_data["servers"]:
            self.logger.error(f"❌ 서버 '{server_name}'이 설정에 없습니다.")
            return False
        
        self.config_data["servers"][server_name]["enabled"] = True
        self.logger.info(f"✅ 서버 '{server_name}' 활성화")
        return self.save_config()
    
    def disable_server(self, server_name: str) -> bool:
        """서버 비활성화"""
        if "servers" not in self.config_data:
            return True
        
        if server_name not in self.config_data["servers"]:
            self.logger.error(f"❌ 서버 '{server_name}'이 설정에 없습니다.")
            return False
        
        self.config_data["servers"][server_name]["enabled"] = False
        self.logger.info(f"✅ 서버 '{server_name}' 비활성화")
        return self.save_config()
    
    def add_server(self, server_name: str, config: Dict[str, Any]) -> bool:
        """새 서버 추가"""
        if "servers" not in self.config_data:
            self.config_data["servers"] = {}
        
        # 기본값 설정
        default_config = {
            "enabled": False,
            "transport": "stdio",
            "command": "",
            "args": [],
            "env": {}
        }
        
        # 기본값과 사용자 설정 병합
        merged_config = {**default_config, **config}
        
        self.config_data["servers"][server_name] = merged_config
        self.logger.info(f"✅ 서버 '{server_name}' 추가")
        return self.save_config()
    
    def remove_server(self, server_name: str) -> bool:
        """서버 제거"""
        if "servers" not in self.config_data:
            return True
        
        if server_name not in self.config_data["servers"]:
            self.logger.error(f"❌ 서버 '{server_name}'이 설정에 없습니다.")
            return False
        
        del self.config_data["servers"][server_name]
        self.logger.info(f"✅ 서버 '{server_name}' 제거")
        return self.save_config()
    
    def get_all_servers(self) -> Dict[str, Dict[str, Any]]:
        """모든 서버 설정 반환"""
        return self.config_data.get("servers", {})
    
    def get_server_status(self) -> Dict[str, Any]:
        """서버 상태 정보 반환"""
        servers = self.config_data.get("servers", {})
        status = {
            "total_servers": len(servers),
            "enabled_servers": 0,
            "disabled_servers": 0,
            "servers": {}
        }
        
        for name, config in servers.items():
            is_enabled = config.get("enabled", False)
            status["servers"][name] = {
                "enabled": is_enabled,
                "transport": config.get("transport", "stdio"),
                "command": config.get("command", ""),
                "args": config.get("args", [])
            }
            
            if is_enabled:
                status["enabled_servers"] += 1
            else:
                status["disabled_servers"] += 1
        
        return status
    
    def validate_config(self) -> List[str]:
        """설정 유효성 검사"""
        errors = []
        servers = self.config_data.get("servers", {})
        
        for name, config in servers.items():
            if not config.get("transport"):
                errors.append(f"서버 '{name}': transport 필드가 필요합니다.")
            
            # transport 타입별 검사
            transport = config.get("transport", "stdio")
            if transport == "stdio":
                if not config.get("command"):
                    errors.append(f"서버 '{name}': stdio transport는 command 필드가 필요합니다.")
                if not config.get("args"):
                    errors.append(f"서버 '{name}': stdio transport는 args 필드가 필요합니다.")
            elif transport == "streamable_http":
                if not config.get("url"):
                    errors.append(f"서버 '{name}': streamable_http transport는 url 필드가 필요합니다.")
        
        return errors
    
    def show_status(self) -> None:
        """서버 상태 표시"""
        status = self.get_server_status()
        
        print(f"\n📊 MCP 서버 상태:")
        print("=" * 50)
        print(f"총 서버 수: {status['total_servers']}")
        print(f"활성화된 서버: {status['enabled_servers']}")
        print(f"비활성화된 서버: {status['disabled_servers']}")
        
        if status['servers']:
            print(f"\n📋 서버 목록:")
            for name, info in status['servers'].items():
                status_icon = "✅" if info['enabled'] else "❌"
                print(f"  {status_icon} {name}")
                print(f"     Transport: {info['transport']}")
                print(f"     Command: {info['command']}")
                if info['args']:
                    print(f"     Args: {' '.join(info['args'])}")
                print()
        
        print("=" * 50)
    
    def create_sample_config(self) -> bool:
        """샘플 설정 파일 생성"""
        sample_config = {
            "servers": {
                "math": {
                    "command": "python",
                    "args": ["src/mcp/servers/math_server.py"],
                    "enabled": True,
                    "transport": "stdio",
                    "env": {}
                },
                "brave_search": {
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-brave-search"],
                    "enabled": False,
                    "transport": "stdio",
                    "env": {
                        "BRAVE_API_KEY": "your_api_key_here"
                    }
                }
            }
        }
        
        self.config_data = sample_config
        return self.save_config()


# 전역 설정 관리자 인스턴스
config_manager = MCPConfigManager()


def get_config_manager() -> MCPConfigManager:
    """MCP 설정 관리자 인스턴스 반환"""
    return config_manager


if __name__ == "__main__":
    # 테스트 코드
    manager = get_config_manager()
    
    print("📋 MCP 설정 관리자 테스트")
    print("=" * 40)
    
    # 현재 설정 표시
    manager.show_status()
    
    # 설정 유효성 검사
    errors = manager.validate_config()
    if errors:
        print("\n❌ 설정 오류:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ 설정이 유효합니다.")
    
    # 활성화된 서버 목록
    enabled_servers = manager.get_enabled_servers()
    print(f"\n🔧 활성화된 서버: {list(enabled_servers.keys())}")
