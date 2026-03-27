#!/usr/bin/env python3
"""
DeepAgent 테스트 스크립트

deepagents 라이브러리를 사용하는 Deep Agent의 기능을 테스트합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import DeepAgentLibrary
from tools import create_brave_search_tool, load_mcp_tools_sync


def test_basic_query():
    """기본 쿼리 테스트"""
    print("=" * 60)
    print("테스트 1: 기본 쿼리 테스트")
    print("=" * 60)
    
    try:
        agent = DeepAgentLibrary(use_ollama=True)
        
        query = "LangGraph란 무엇인가요?"
        print(f"\n📝 쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return False
        
        if result.get("messages"):
            response = result["messages"][-1].content
            print(f"✅ 응답:\n{response}\n")
            return True
        else:
            print("❌ 응답이 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        return False


def test_planning():
    """작업 분해 테스트"""
    print("\n" + "=" * 60)
    print("테스트 2: 작업 분해 테스트")
    print("=" * 60)
    
    try:
        agent = DeepAgentLibrary(use_ollama=True)
        
        query = "웹 애플리케이션을 개발하는 작업을 단계별로 분해해주세요."
        print(f"\n📝 쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return False
        
        if result.get("messages"):
            response = result["messages"][-1].content
            print(f"✅ 응답:\n{response}\n")
            return True
        else:
            print("❌ 응답이 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        return False


def test_with_search_tool():
    """검색 도구 포함 테스트 (Brave Search 사용)"""
    print("\n" + "=" * 60)
    print("테스트 3: 검색 도구 포함 테스트 (Brave Search)")
    print("=" * 60)
    print("💡 참고: 이 테스트는 Brave Search API 키가 필요합니다.")
    
    try:
        # API 키 확인
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            print("\n⚠️  BRAVE_API_KEY가 설정되지 않았습니다.")
            print("   검색 도구 테스트를 건너뜁니다.")
            print("   환경변수에 BRAVE_API_KEY를 설정하면 검색 기능을 테스트할 수 있습니다.")
            return None  # 스킵 (None 반환)
        
        # Brave Search 도구 생성
        print(f"\n✅ API 키 확인됨: {api_key[:10]}...")
        search_tool = create_brave_search_tool()
        
        if not search_tool:
            print("⚠️  검색 도구를 생성할 수 없습니다.")
            return False
        
        print("✅ Brave Search 도구 생성 성공")
        
        agent = DeepAgentLibrary(
            use_ollama=True,
            tools=[search_tool],
            system_prompt="""당신은 전문 연구원입니다. 웹 검색을 통해 정보를 수집하고 
            정리된 보고서를 작성하세요."""
        )
        
        query = "최신 AI 트렌드에 대해 조사해주세요."
        print(f"\n📝 쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return False
        
        if result.get("messages"):
            response = result["messages"][-1].content
            print(f"✅ 응답:\n{response}\n")
            return True
        else:
            print("❌ 응답이 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_with_mcp_tools():
    """MCP 도구 포함 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: MCP 도구 포함 테스트")
    print("=" * 60)
    
    try:
        # MCP 도구 로드
        print("\n🔧 MCP 도구 로드 중...")
        mcp_tools = load_mcp_tools_sync()
        
        if not mcp_tools:
            print("\n⚠️  MCP 도구를 로드할 수 없습니다.")
            print("   mcp_config.json 파일을 확인하거나 활성화된 서버가 있는지 확인하세요.")
            return None  # 스킵
        
        print(f"✅ MCP 도구 로드 성공: {len(mcp_tools)}개")
        for tool in mcp_tools[:5]:  # 처음 5개만 표시
            print(f"   - {tool.name}")
        if len(mcp_tools) > 5:
            print(f"   ... 외 {len(mcp_tools) - 5}개")
        
        agent = DeepAgentLibrary(
            use_ollama=True,
            use_mcp=True,  # MCP 도구 포함
            system_prompt="당신은 MCP 도구를 사용하여 작업을 수행하는 전문가입니다."
        )
        
        query = "MCP 도구를 사용하여 파일 시스템을 탐색해보세요."
        print(f"\n📝 쿼리: {query}\n")
        
        result = agent.invoke(query)
        
        if "error" in result:
            print(f"❌ 오류: {result['error']}")
            return False
        
        if result.get("messages"):
            response = result["messages"][-1].content
            print(f"✅ 응답:\n{response[:500]}...\n")  # 처음 500자만 표시
            return True
        else:
            print("❌ 응답이 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n🧪 DeepAgent 테스트 시작\n")
    
    tests = [
        ("기본 쿼리", test_basic_query),
        ("작업 분해", test_planning),
        ("검색 도구 포함", test_with_search_tool),
    ]
    
    # MCP 테스트 추가 (선택적)
    try:
        from tools import get_enabled_mcp_server_configs
        mcp_configs = get_enabled_mcp_server_configs()
        if mcp_configs:
            tests.append(("MCP 도구 포함", test_with_mcp_tools))
    except:
        pass
    
    results = []
    skipped = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result is None:
                skipped.append(test_name)
            else:
                results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {str(e)}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {test_name}")
    
    if skipped:
        for test_name in skipped:
            print(f"⏭️  건너뜀: {test_name} (API 키 미설정)")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과")
    if skipped:
        print(f"   ⏭️  {len(skipped)}개 테스트 건너뜀 (API 키 필요)")
    
    if passed == total:
        print("🎉 모든 테스트가 통과했습니다!")
        return 0
    else:
        print(f"⚠️  {total - passed}개 테스트가 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

