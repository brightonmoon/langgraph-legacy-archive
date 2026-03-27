#!/usr/bin/env python3
"""
MCP 클라이언트 간단 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.mcp.client.manager import get_mcp_manager

async def test_mcp():
    """MCP 클라이언트 테스트"""
    print("🔧 MCP 클라이언트 테스트 시작")
    print("=" * 50)
    
    manager = get_mcp_manager()
    
    print("\n1️⃣ MCP 클라이언트 초기화 중...")
    try:
        success = await manager.initialize_client()
        
        if success:
            print("✅ 초기화 성공")
            
            print("\n2️⃣ 도구 목록 확인 중...")
            tools = manager.get_tools()
            print(f"📋 로드된 도구: {len(tools)}개")
            
            local_tools = manager.get_local_tools()
            mcp_tools = manager.get_mcp_tools()
            
            print(f"\n   - 로컬 도구: {len(local_tools)}개")
            for tool in local_tools:
                print(f"     • {tool.name}")
            
            print(f"\n   - MCP 도구: {len(mcp_tools)}개")
            for tool in mcp_tools:
                print(f"     • {tool.name}")
            
            print("\n3️⃣ MCP 상태 확인...")
            status = manager.get_status()
            print(f"   - mcp_available: {status.get('mcp_available')}")
            print(f"   - initialized: {status.get('initialized')}")
            print(f"   - total_tools: {status.get('total_tools_count')}")
            
            print("\n✅ 테스트 완료!")
            
        else:
            print("❌ 초기화 실패")
            print("⚠️ 로컬 도구만 사용 가능합니다.")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_mcp())

