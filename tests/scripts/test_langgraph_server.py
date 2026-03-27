"""
LangGraph Server API 테스트 스크립트
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:2024"


def test_server_health():
    """서버 상태 확인"""
    print("=" * 60)
    print("🔍 1. 서버 상태 확인")
    print("=" * 60)
    
    try:
        # OpenAPI 문서 확인
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            print(f"✅ 서버 접속 성공 (OpenAPI 문서 확인)")
            return True
        else:
            print(f"⚠️ 서버 응답: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 접속 실패: {e}")
        return False


def test_assistants_list():
    """등록된 Assistant 목록 확인"""
    print("\n" + "=" * 60)
    print("📊 2. 등록된 Assistant 목록 확인")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/assistants")
        if response.status_code == 200:
            assistants = response.json()
            if isinstance(assistants, list):
                print(f"✅ 등록된 Assistant: {len(assistants)}개")
                for assistant in assistants:
                    assistant_id = assistant.get("assistant_id", "unknown")
                    print(f"   - {assistant_id}")
                return assistants
            else:
                print(f"✅ Assistant 응답: {assistants}")
                return [assistants] if assistants else []
        else:
            print(f"❌ Assistant 목록 조회 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            # 기본 그래프 ID 반환 (langgraph.json에서 설정한 것)
            return [{"assistant_id": "agent"}]
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 기본 그래프 ID 반환
        return [{"assistant_id": "agent"}]


def test_create_thread():
    """스레드 생성"""
    print("\n" + "=" * 60)
    print("🧵 3. 스레드 생성")
    print("=" * 60)
    
    try:
        # 스레드 생성 (POST /threads)
        response = requests.post(
            f"{BASE_URL}/threads",
            json={}
        )
        if response.status_code in [200, 201]:
            thread_data = response.json()
            thread_id = thread_data.get("thread_id") or thread_data.get("id")
            print(f"✅ 스레드 생성 성공: {thread_id}")
            return thread_id
        else:
            # 스레드 ID를 직접 생성하여 시도
            thread_id = f"test-thread-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"⚠️ 스레드 생성 응답: {response.status_code}, 임시 ID 사용: {thread_id}")
            return thread_id
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        thread_id = f"test-thread-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"   임시 스레드 ID 사용: {thread_id}")
        return thread_id


def test_create_run(thread_id: str, assistant_id: str = "agent"):
    """실행 생성 및 대기"""
    print("\n" + "=" * 60)
    print("🚀 4. 그래프 실행 테스트")
    print("=" * 60)
    
    if not thread_id:
        print("❌ 스레드 ID가 없습니다.")
        return None
    
    try:
        # 실행 생성 (MessagesState 형식)
        run_data = {
            "assistant_id": assistant_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "안녕하세요! 간단한 인사말로 답변해주세요."
                    }
                ]
            }
        }
        
        print(f"📤 실행 요청 전송 중...")
        print(f"   Assistant: {assistant_id}")
        print(f"   스레드: {thread_id}")
        print(f"   입력: {run_data['input']['messages'][0]['content']}")
        
        response = requests.post(
            f"{BASE_URL}/threads/{thread_id}/runs",
            json=run_data
        )
        
        if response.status_code in [200, 201]:
            run_result = response.json()
            run_id = run_result.get("run_id")
            print(f"✅ 실행 생성 성공: {run_id}")
            
            # 실행 상태 확인
            print(f"\n⏳ 실행 상태 확인 중...")
            status_response = requests.get(
                f"{BASE_URL}/threads/{thread_id}/runs/{run_id}"
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   상태: {status.get('status', 'unknown')}")
                
                # 실행 결과 확인
                if status.get('status') == 'success':
                    result = status.get('values', {}).get('messages', [])
                    if result:
                        last_message = result[-1]
                        print(f"\n✅ 실행 완료!")
                        print(f"   응답: {last_message.get('content', 'N/A')[:100]}...")
                elif status.get('status') == 'error':
                    print(f"❌ 실행 오류: {status.get('error', 'Unknown error')}")
                
                return run_id
            else:
                print(f"⚠️ 상태 확인 실패: {status_response.status_code}")
                return run_id
        else:
            print(f"❌ 실행 생성 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_api_docs():
    """API 문서 접속 확인"""
    print("\n" + "=" * 60)
    print("📚 5. API 문서 확인")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print(f"✅ API 문서 접속 가능")
            print(f"   URL: {BASE_URL}/docs")
        else:
            print(f"⚠️ API 문서 접속 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("🧪 LangGraph Server API 테스트 시작")
    print("=" * 60)
    print(f"서버 주소: {BASE_URL}")
    print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 서버 상태 확인
    if not test_server_health():
        print("\n❌ 서버가 실행되지 않았습니다.")
        print("   'uv run langgraph dev' 명령으로 서버를 먼저 시작하세요.")
        return
    
    # 2. Assistant 목록 확인
    assistants = test_assistants_list()
    
    if not assistants:
        print("\n⚠️ 등록된 Assistant가 없습니다. 기본 'agent' 사용")
        assistant_id = "agent"
    else:
        # 첫 번째 Assistant ID 사용
        assistant_id = assistants[0].get("assistant_id", "agent") if isinstance(assistants[0], dict) else "agent"
        print(f"\n✅ 사용할 Assistant: {assistant_id}")
    
    # 3. 스레드 생성
    thread_id = test_create_thread()
    
    # 4. 그래프 실행 테스트
    if thread_id:
        test_create_run(thread_id, assistant_id=assistant_id)
    
    # 5. API 문서 확인
    test_api_docs()
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
    print("\n💡 추가 확인 사항:")
    print(f"   1. API 문서: {BASE_URL}/docs")
    print(f"   2. Studio UI: https://smith.langchain.com/studio/?baseUrl={BASE_URL}")
    print(f"   3. 스레드 확인: {BASE_URL}/threads/{thread_id if thread_id else 'YOUR_THREAD_ID'}")


if __name__ == "__main__":
    main()

