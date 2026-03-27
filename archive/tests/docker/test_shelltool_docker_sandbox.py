"""
ShellToolMiddleware를 사용한 Docker 샌드박스 환경 테스트

이 테스트는 LangChain의 ShellToolMiddleware와 DockerExecutionPolicy를 사용하여
격리된 Docker 컨테이너에서 Python 코드를 실행하는 기능을 검증합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ShellToolMiddleware,
    DockerExecutionPolicy,
)
from langchain_ollama import ChatOllama


def test_shelltool_docker_sandbox():
    """ShellToolMiddleware를 사용한 Docker 샌드박스 테스트"""
    print("=" * 60)
    print("ShellToolMiddleware Docker 샌드박스 테스트")
    print("=" * 60)
    
    # Ollama 모델 설정 (간단한 테스트용)
    # 주의: ShellToolMiddleware는 Agent가 shell tool을 호출해야 하므로,
    # 모델이 tool calling을 지원해야 함
    model = ChatOllama(
        model="qwen2.5-coder:latest",
        temperature=0,
    )
    
    # 시스템 프롬프트 설정 (shell tool 사용을 명확히)
    # 주의: create_agent는 시스템 프롬프트를 직접 설정할 수 없으므로,
    # 모델에 바인딩하거나 다른 방법 사용 필요
    
    # 작업 디렉토리 설정 (프로젝트 루트)
    workspace_root = str(project_root)
    print(f"\n📁 Workspace Root: {workspace_root}")
    
    # Agent 생성 (ShellToolMiddleware 포함)
    print("\n🔧 Agent 생성 중...")
    
    # 먼저 startup_commands 없이 기본 테스트
    print("📦 기본 Python 테스트용 Agent 생성 (startup_commands 없음)...")
    agent_basic = create_agent(
        model=model,
        tools=[],
        middleware=[
            ShellToolMiddleware(
                workspace_root=workspace_root,
                execution_policy=DockerExecutionPolicy(
                    image="python:3.11-slim",
                    command_timeout=60.0,
                ),
            ),
        ],
    )
    
    # pandas/numpy가 이미 설치된 커스텀 이미지 사용
    print("📦 Pandas/NumPy 테스트용 Agent 생성 (커스텀 이미지 사용)...")
    agent_with_packages = create_agent(
        model=model,
        tools=[],
        middleware=[
            ShellToolMiddleware(
                workspace_root=workspace_root,
                startup_commands=[
                    "export PYTHONPATH=/workspace",
                ],
                execution_policy=DockerExecutionPolicy(
                    image="csv-sandbox:test",  # pandas/numpy가 설치된 커스텀 이미지
                    command_timeout=60.0,
                ),
            ),
        ],
    )
    
    print("✅ Agent 생성 완료")
    
    # 테스트 케이스 0: 기본 Python 테스트 (패키지 없음)
    print("\n" + "=" * 60)
    print("테스트 0: 기본 Python 테스트 (패키지 없음)")
    print("=" * 60)
    
    test_code_0 = """
print("✅ 기본 Python 테스트 성공")
print(f"Python 버전: {__import__('sys').version}")
"""
    
    test_file_0 = project_root / "workspace" / "test_basic.py"
    test_file_0.parent.mkdir(parents=True, exist_ok=True)
    test_file_0.write_text(test_code_0, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_0}")
    
    print("\n🚀 Agent에게 코드 실행 요청...")
    try:
        result = agent_basic.invoke({
            "messages": [{
                "role": "user",
                "content": f"shell 명령어로 'python workspace/test_basic.py'를 실행해줘"
            }]
        })
        
        print("\n📊 실행 결과:")
        print("-" * 60)
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(last_message.content)
            else:
                print(str(last_message))
        else:
            print(str(result))
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 실행 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 1: 간단한 Python 코드 실행 (pandas/numpy)
    print("\n" + "=" * 60)
    print("테스트 1: Pandas/NumPy 코드 실행")
    print("=" * 60)
    
    test_code_1 = """
import pandas as pd
import numpy as np

# 간단한 데이터프레임 생성
df = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50]
})

# 기본 연산
result = df['A'].sum()
print(f"✅ Pandas 기본 연산 테스트 성공: {result}")
print(f"DataFrame shape: {df.shape}")
"""
    
    # 코드를 파일로 저장
    test_file = project_root / "workspace" / "test_code.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code_1, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file}")
    
    # Agent에게 코드 실행 요청
    print("\n🚀 Agent에게 코드 실행 요청...")
    try:
        result = agent_with_packages.invoke({
            "messages": [{
                "role": "user",
                "content": f"shell 명령어로 'python workspace/test_code.py'를 실행해줘"
            }]
        })
        
        print("\n📊 실행 결과:")
        print("-" * 60)
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(last_message.content)
            else:
                print(str(last_message))
        else:
            print(str(result))
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 실행 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 2: CSV 파일 읽기 테스트
    print("\n" + "=" * 60)
    print("테스트 2: CSV 파일 읽기 테스트")
    print("=" * 60)
    
    # 간단한 CSV 파일 생성
    csv_content = """col1,col2,col3
1,2,3
4,5,6
7,8,9"""
    
    csv_file = project_root / "workspace" / "test_data.csv"
    csv_file.write_text(csv_content, encoding='utf-8')
    print(f"📝 CSV 파일 생성: {csv_file}")
    
    test_code_2 = """
import pandas as pd

# CSV 파일 읽기
df = pd.read_csv('workspace/test_data.csv')
print(f"✅ CSV 읽기 성공")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\\nData:\\n{df}")
"""
    
    test_file_2 = project_root / "workspace" / "test_code_2.py"
    test_file_2.write_text(test_code_2, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_2}")
    
    # Agent에게 코드 실행 요청
    print("\n🚀 Agent에게 코드 실행 요청...")
    try:
        result = agent_with_packages.invoke({
            "messages": [{
                "role": "user",
                "content": f"shell 명령어로 'python workspace/test_code_2.py'를 실행해줘"
            }]
        })
        
        print("\n📊 실행 결과:")
        print("-" * 60)
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(last_message.content)
            else:
                print(str(last_message))
        else:
            print(str(result))
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 실행 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 테스트 케이스 3: NumPy 연산 테스트
    print("\n" + "=" * 60)
    print("테스트 3: NumPy 연산 테스트")
    print("=" * 60)
    
    test_code_3 = """
import numpy as np

# NumPy 배열 생성 및 연산
arr = np.array([1, 2, 3, 4, 5])
result_sum = np.sum(arr)
result_mean = np.mean(arr)

print(f"✅ NumPy 연산 테스트 성공")
print(f"Array: {arr}")
print(f"Sum: {result_sum}")
print(f"Mean: {result_mean}")
"""
    
    test_file_3 = project_root / "workspace" / "test_code_3.py"
    test_file_3.write_text(test_code_3, encoding='utf-8')
    print(f"📝 테스트 코드 파일 생성: {test_file_3}")
    
    # Agent에게 코드 실행 요청
    print("\n🚀 Agent에게 코드 실행 요청...")
    try:
        result = agent_with_packages.invoke({
            "messages": [{
                "role": "user",
                "content": f"shell 명령어로 'python workspace/test_code_3.py'를 실행해줘"
            }]
        })
        
        print("\n📊 실행 결과:")
        print("-" * 60)
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(last_message.content)
            else:
                print(str(last_message))
        else:
            print(str(result))
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 실행 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    # 환경 변수 확인
    if not os.getenv("OLLAMA_API_KEY"):
        print("⚠️ OLLAMA_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일을 확인하거나 환경 변수를 설정해주세요.")
    
    test_shelltool_docker_sandbox()

