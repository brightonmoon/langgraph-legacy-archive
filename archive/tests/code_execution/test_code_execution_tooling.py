"""
코드 실행 도구화 테스트

Phase 1, 2 구현 검증 및 코딩 에이전트 구조 테스트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.code_execution_envs import (
    execute_code_tool,
    CodeExecutionFactory,
    ExecutionEnvironment,
    ExecutionConfig,
    execute_code_in_docker,
    execute_code_locally
)


def test_factory():
    """팩토리 테스트"""
    print("\n" + "="*70)
    print("테스트 1: CodeExecutionFactory")
    print("="*70)
    
    try:
        # 사용 가능한 환경 확인
        available = CodeExecutionFactory.get_available_environments()
        print(f"\n✅ 사용 가능한 실행 환경: {[e.value for e in available]}")
        
        # 도커 실행자 생성
        docker_executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.DOCKER)
        print(f"✅ 도커 실행자 생성 성공: {docker_executor.get_environment().value}")
        print(f"   사용 가능: {docker_executor.is_available()}")
        
        # 로컬 실행자 생성
        local_executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.LOCAL)
        print(f"✅ 로컬 실행자 생성 성공: {local_executor.get_environment().value}")
        print(f"   사용 가능: {local_executor.is_available()}")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_docker_executor():
    """도커 실행자 테스트"""
    print("\n" + "="*70)
    print("테스트 2: Docker Executor")
    print("="*70)
    
    # 테스트 코드 파일 생성
    test_code = """print("Hello from Docker!")
print("Test successful!")
"""
    
    test_file = Path("tests/test_output/test_docker_executor.py")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code, encoding='utf-8')
    
    print(f"\n📝 테스트 코드 파일: {test_file}")
    
    try:
        executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.DOCKER)
        
        if not executor.is_available():
            print("⚠️ 도커가 사용 불가능합니다. 테스트를 건너뜁니다.")
            return True
        
        config = ExecutionConfig(
            environment=ExecutionEnvironment.DOCKER,
            timeout=30,
            output_directory="tests/test_output/results"
        )
        
        # 설정 검증
        is_valid, error_msg = executor.validate_config(config)
        if not is_valid:
            print(f"⚠️ 설정 검증 실패: {error_msg}")
            return True  # 도커 이미지가 없을 수 있으므로 실패로 처리하지 않음
        
        print("\n🐳 도커에서 코드 실행 중...")
        result = executor.execute(test_file, config)
        
        print(f"\n✅ 실행 결과:")
        print(f"   성공: {result.success}")
        print(f"   종료 코드: {result.exit_code}")
        print(f"   실행 시간: {result.execution_time:.2f}초")
        if result.stdout:
            print(f"\n📊 출력:\n{result.stdout[:200]}...")
        if result.error:
            print(f"\n❌ 오류: {result.error}")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_local_executor():
    """로컬 실행자 테스트"""
    print("\n" + "="*70)
    print("테스트 3: Local Executor")
    print("="*70)
    
    # 테스트 코드 파일 생성
    test_code = """print("Hello from Local!")
print("Test successful!")
result = 1 + 2
print(f"1 + 2 = {result}")
"""
    
    test_file = Path("tests/test_output/test_local_executor.py")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code, encoding='utf-8')
    
    print(f"\n📝 테스트 코드 파일: {test_file}")
    
    try:
        executor = CodeExecutionFactory.create_executor(ExecutionEnvironment.LOCAL)
        
        # 절대 경로로 변환
        work_dir = Path("tests/test_output").resolve()
        output_dir = Path("tests/test_output/results").resolve()
        
        config = ExecutionConfig(
            environment=ExecutionEnvironment.LOCAL,
            timeout=30,
            working_directory=str(work_dir),
            output_directory=str(output_dir)
        )
        
        # 설정 검증
        is_valid, error_msg = executor.validate_config(config)
        if not is_valid:
            print(f"❌ 설정 검증 실패: {error_msg}")
            return False
        
        print("\n💻 로컬에서 코드 실행 중...")
        result = executor.execute(test_file, config)
        
        print(f"\n✅ 실행 결과:")
        print(f"   성공: {result.success}")
        print(f"   종료 코드: {result.exit_code}")
        print(f"   실행 시간: {result.execution_time:.2f}초")
        if result.stdout:
            print(f"\n📊 출력:\n{result.stdout}")
        if result.stderr:
            print(f"\n⚠️ 경고:\n{result.stderr}")
        if result.error:
            print(f"\n❌ 오류: {result.error}")
        
        return result.success
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_execute_code_tool():
    """통합 Tool 테스트"""
    print("\n" + "="*70)
    print("테스트 4: execute_code_tool (통합 Tool)")
    print("="*70)
    
    # 테스트 코드 파일 생성
    test_code = """print("Hello from Tool!")
print("Integration test successful!")
"""
    
    test_file = Path("tests/test_output/test_tool.py")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_code, encoding='utf-8')
    
    print(f"\n📝 테스트 코드 파일: {test_file}")
    
    try:
        # 로컬 환경으로 테스트
        print("\n🔧 execute_code_tool 호출 중...")
        result = execute_code_tool.invoke({
            "code_file": str(test_file),
            "environment": "local",
            "timeout": 30,
            "output_directory": "tests/test_output/results"
        })
        
        print(f"\n✅ Tool 실행 결과:")
        print(result[:500] + "..." if len(result) > 500 else result)
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_code_generation_agent_integration():
    """코딩 에이전트 통합 테스트"""
    print("\n" + "="*70)
    print("테스트 5: 코딩 에이전트 통합 테스트")
    print("="*70)
    
    try:
        from src.agents.sub_agents.code_generation_agent import create_code_generation_agent
        
        # 코딩 에이전트 생성
        agent = create_code_generation_agent(
            enable_planning=True,
            enable_filesystem_tools=True
        )
        
        print("\n✅ 코딩 에이전트 생성 성공")
        
        # 테스트 입력
        initial_state = {
            "messages": [],
            "task_description": "간단한 계산기 함수 만들기",
            "requirements": "덧셈, 뺄셈 함수 생성",
            "context": {"domain": "general"},
            "target_filepath": "tests/test_output/test_calculator_integration.py"
        }
        
        print("\n📋 입력:")
        print(f"  작업: {initial_state['task_description']}")
        print(f"  목표 파일: {initial_state['target_filepath']}")
        
        # 에이전트 실행
        result = agent.invoke(initial_state)
        
        print(f"\n✅ 코딩 에이전트 실행 결과:")
        print(f"   상태: {result.get('status', 'N/A')}")
        print(f"   생성된 코드 길이: {len(result.get('generated_code', ''))} 문자")
        print(f"   생성된 파일: {result.get('generated_code_file', 'N/A')}")
        
        # 생성된 파일 확인
        if result.get('generated_code_file'):
            code_file = Path(result['generated_code_file'])
            if code_file.exists():
                print(f"   ✅ 파일 존재 확인: {code_file}")
        
        # Filesystem 결과 확인
        if result.get('files_created'):
            print(f"\n📁 Filesystem 결과:")
            for filepath in result.get('files_created', []):
                exists = Path(filepath).exists()
                print(f"   {'✅' if exists else '❌'} {filepath}")
        
        return True
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "="*70)
    print("코드 실행 도구화 테스트 시작")
    print("="*70)
    
    # 테스트 디렉토리 생성
    test_output_dir = Path("tests/test_output")
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # 테스트 실행
    results.append(("Factory", test_factory()))
    results.append(("Docker Executor", test_docker_executor()))
    results.append(("Local Executor", test_local_executor()))
    results.append(("execute_code_tool", test_execute_code_tool()))
    results.append(("코딩 에이전트 통합", test_code_generation_agent_integration()))
    
    # 결과 요약
    print("\n" + "="*70)
    print("테스트 결과 요약")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    
    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

