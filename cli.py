#!/usr/bin/env python3
"""
간단한 CLI 인터페이스 - Agent 선택 및 쿼리 실행

⚠️  레거시 경고:
이 CLI는 빠른 테스트 및 학습 목적으로 제공됩니다.
LangGraph 환경 적응을 위해 LangGraph dev 사용을 권장합니다:
  - langgraph dev 실행
  - Studio 접속: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
  
자세한 내용은 .cursor/docs/in_progress/cli_migration_review.mdc 참고
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.agents import AgentFactory


def show_menu():
    """메인 메뉴 표시"""
    print("\n🚀 Agentic AI CLI")
    print("=" * 30)
    print("1. Study Agents (학습용)")
    print("2. Orchestrator Agent (하이브리드 아키텍처)")
    print("3. Agent 정보")
    print("4. 종료")
    print("-" * 30)


def show_study_menu():
    """Study Agents 서브메뉴 표시"""
    print("\n📚 Study Agents (학습용)")
    print("=" * 30)
    print("1. Basic Agent")
    print("2. LangGraph Agent") 
    print("3. LangGraph Tools Agent")
    print("4. LangGraph MCP Agent")
    print("5. LangGraph Tools Middleware Agent")
    print("6. Coding Agent")
    print("7. Multiple Workers Coding Agent")
    print("8. 뒤로 가기")
    print("-" * 30)
    print("모델 선택:")
    print("  기본: gpt-oss:120b-cloud")
    print("  kimi: kimi-k2:1t-cloud (입력 시 'kimi' 입력)")
    print("-" * 30)


def run_agent(agent_type: str, model_name: str = None):
    """Agent 실행 및 대화형 인터페이스 시작
    
    Args:
        agent_type: Agent 타입
        model_name: 사용할 모델명 (예: "kimi-k2:1t-cloud")
    """
    print(f"\n🔧 {agent_type.upper()} Agent 시작")
    if model_name:
        print(f"   모델: {model_name}")
    print("-" * 30)
    
    try:
        # Agent 생성
        agent = AgentFactory.create_agent(agent_type, model_name=model_name)
        
        if not agent.is_ready():
            print(f"❌ {agent_type.upper()} Agent 초기화 실패")
            return
        
        # Agent 정보 표시 (간결하게)
        agent_info = agent.get_info()
        print(f"✅ {agent_type.upper()} Agent 준비 완료!")
        
        # Agent 타입에 따라 다른 정보 표시
        if agent_type == "multiple_workers_coding":
            print(f"   Orchestrator: {agent_info.get('orchestrator', 'N/A')}")
            print(f"   Workers: {', '.join(agent_info.get('workers', []))}")
        elif agent_type == "orchestrator":
            print(f"   모델: {agent_info.get('model', 'N/A')}")
            if 'features' in agent_info:
                print(f"   기능: {', '.join(agent_info['features'])}")
        else:
            print(f"   모델: {agent_info.get('model', 'N/A')}")
        
        # 모든 Agent를 대화형 인터페이스로 실행
        print(f"\n💬 대화형 모드 시작")
        if agent_type in ["langgraph_tools", "langgraph_mcp", "langgraph_tools_middleware"]:
            print("💡 '/help' 입력시 도구 설명을 볼 수 있습니다.")
            if agent_type == "langgraph_mcp":
                print("💡 '/mcp' 입력시 MCP 상태를 볼 수 있습니다.")
                print("💡 '/servers' 입력시 서버 상태를 볼 수 있습니다.")
            elif agent_type == "langgraph_tools_middleware":
                print("💡 '/stats' 입력시 Middleware 통계를 볼 수 있습니다.")
        elif agent_type in ["coding", "multiple_workers_coding"]:
            print("💡 코딩 작업을 요청하세요 (예: Python으로 리스트 정렬 함수 작성)")
            if agent_type == "multiple_workers_coding":
                print("💡 두 Worker 모델이 병렬로 코드를 생성하고 품질을 비교합니다.")
        elif agent_type == "orchestrator":
            print("💡 OrchestratorAgent는 하이브리드 아키텍처로 복잡한 작업을 처리합니다.")
            print("💡 - 작업 분석 및 분해")
            print("💡 - Worker 자동 선택 (복잡도에 따라)")
            print("💡 - 결과 통합 및 종합")
            print("💡 - Planning + Filesystem + SubAgent 지원 Worker 자동 생성")
        print("-" * 30)
        agent.chat()
        
        print(f"\n✅ {agent_type.upper()} Agent 실행 완료!")
        
    except Exception as e:
        print(f"❌ {agent_type.upper()} Agent 실행 중 오류: {str(e)}")


def show_agent_info():
    """Agent 정보 표시"""
    print("\n📊 Agent 정보")
    print("-" * 30)
    
    available_agents = AgentFactory.get_available_agents()
    
    for agent_type in available_agents:
        agent_info = AgentFactory.get_agent_info(agent_type)
        print(f"\n🔹 {agent_type.upper()} Agent:")
        print(f"   클래스: {agent_info['class']}")
        print(f"   설명: {agent_info['description']}")
        
        # 실제 Agent 생성하여 상세 정보 확인
        try:
            agent = AgentFactory.create_agent(agent_type)
            if agent.is_ready():
                detailed_info = agent.get_info()
                print(f"   모델: {detailed_info['model']}")
                print(f"   아키텍처: {detailed_info['architecture']}")
                if 'features' in detailed_info:
                    print(f"   기능: {', '.join(detailed_info['features'])}")
            else:
                print("   상태: 초기화 실패")
        except Exception as e:
            print(f"   상태: 오류 - {str(e)}")


def handle_study_menu(model_name: str = None):
    """Study Agents 서브메뉴 처리"""
    while True:
        try:
            show_study_menu()
            choice = input("선택하세요 (1-8): ").strip()
            
            # 모델 선택 (선택적, 이미 있으면 재사용)
            selected_model = model_name
            if choice not in ["8"] and not selected_model:
                model_choice = input("모델 선택 (기본/gpt/kimi): ").strip().lower()
                if model_choice == "kimi":
                    selected_model = "kimi-k2:1t-cloud"
                    print(f"✅ kimi-k2:1t-cloud 모델 선택됨")
                elif model_choice == "gpt":
                    selected_model = "gpt-oss:120b-cloud"
                    print(f"✅ gpt-oss:120b-cloud 모델 선택됨")
                else:
                    print(f"✅ 기본 모델 사용")
            
            if choice == "1":
                run_agent("basic", selected_model)
            elif choice == "2":
                run_agent("langgraph", selected_model)
            elif choice == "3":
                run_agent("langgraph_tools", selected_model)
            elif choice == "4":
                run_agent("langgraph_mcp", selected_model)
            elif choice == "5":
                run_agent("langgraph_tools_middleware", selected_model)
            elif choice == "6":
                run_agent("coding", selected_model)
            elif choice == "7":
                run_agent("multiple_workers_coding", selected_model)
            elif choice == "8":
                break  # 뒤로 가기
            else:
                print("❌ 1-8 사이의 숫자를 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n👋 뒤로 돌아갑니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            print("계속하려면 Enter를 누르세요...")
            input()


def main():
    """메인 함수"""
    print("🚀 Agentic AI CLI 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        try:
            show_menu()
            choice = input("선택하세요 (1-4): ").strip()
            
            if choice == "1":
                # Study Agents 서브메뉴
                handle_study_menu()
            elif choice == "2":
                # OrchestratorAgent (하이브리드 아키텍처)
                model_choice = input("모델 선택 (기본/gpt/kimi): ").strip().lower()
                model_name = None
                if model_choice == "kimi":
                    model_name = "kimi-k2:1t-cloud"
                    print(f"✅ kimi-k2:1t-cloud 모델 선택됨")
                elif model_choice == "gpt":
                    model_name = "gpt-oss:120b-cloud"
                    print(f"✅ gpt-oss:120b-cloud 모델 선택됨")
                else:
                    print(f"✅ 기본 모델 사용")
                run_agent("orchestrator", model_name)
            elif choice == "3":
                show_agent_info()
            elif choice == "4":
                print("\n👋 프로그램을 종료합니다. 안녕히 가세요!")
                break
            else:
                print("❌ 1-4 사이의 숫자를 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Ctrl+C로 프로그램을 종료합니다. 안녕히 가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            print("계속하려면 Enter를 누르세요...")
            input()


if __name__ == "__main__":
    main()
