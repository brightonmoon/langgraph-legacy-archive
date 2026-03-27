"""
Langfuse 상태 확인 스크립트
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_langfuse_config():
    """Langfuse 설정 확인"""
    print("=" * 60)
    print("🔍 Langfuse 설정 확인")
    print("=" * 60)
    
    # 환경변수 확인
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    print(f"\n📋 환경변수 설정:")
    print(f"   LANGFUSE_SECRET_KEY: {'✅ 설정됨' if secret_key else '❌ 설정되지 않음'}")
    print(f"   LANGFUSE_PUBLIC_KEY: {'✅ 설정됨' if public_key else '❌ 설정되지 않음'}")
    print(f"   LANGFUSE_HOST: {host}")
    
    # 대시보드 URL 확인
    print(f"\n🌐 Langfuse 대시보드 접속:")
    if "localhost" in host or "127.0.0.1" in host:
        print(f"   🏠 자체 호스팅: {host}")
        print(f"      - Docker로 실행 중인지 확인: docker ps | grep langfuse")
        print(f"      - 실행 중이 아니면: docker run -d -p 3000:3000 langfuse/langfuse")
    else:
        print(f"   ☁️  클라우드: {host}")
        print(f"      - 웹 브라우저에서 접속: {host}")
    
    # 설정 상태 요약
    print(f"\n📊 설정 상태:")
    if secret_key and public_key:
        print("   ✅ Langfuse 설정 완료")
        print(f"   💡 대시보드 접속: {host}")
    else:
        print("   ⚠️  Langfuse 설정 필요")
        print("\n   📝 .env 파일에 다음을 추가하세요:")
        print("   LANGFUSE_SECRET_KEY=your_secret_key")
        print("   LANGFUSE_PUBLIC_KEY=your_public_key")
        print("   LANGFUSE_HOST=http://localhost:3000  # 자체 호스팅")
        print("   # 또는")
        print("   LANGFUSE_HOST=https://cloud.langfuse.com  # 클라우드")
    
    return secret_key and public_key


def check_langfuse_usage():
    """코드에서 Langfuse 사용 여부 확인"""
    print("\n" + "=" * 60)
    print("📝 코드에서 Langfuse 사용 확인")
    print("=" * 60)
    
    import subprocess
    
    # Langfuse import 확인
    try:
        result = subprocess.run(
            ["grep", "-r", "langfuse", "src/", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd="/home/doyamoon/agentic_ai"
        )
        if result.stdout:
            print("   ✅ Langfuse 사용 코드 발견:")
            lines = result.stdout.strip().split('\n')[:5]  # 처음 5줄만
            for line in lines:
                print(f"      {line}")
        else:
            print("   ⚠️  코드에서 Langfuse 사용이 발견되지 않았습니다")
            print("   💡 Langfuse 통합이 필요합니다")
    except Exception as e:
        print(f"   ❌ 확인 중 오류: {e}")


def main():
    """메인 함수"""
    print("\n" + "=" * 60)
    print("🔍 Langfuse 상태 확인")
    print("=" * 60)
    
    is_configured = check_langfuse_config()
    check_langfuse_usage()
    
    print("\n" + "=" * 60)
    print("💡 다음 단계")
    print("=" * 60)
    
    if is_configured:
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"\n1. Langfuse 대시보드 접속:")
        print(f"   {host}")
        print("\n2. 대시보드에서 확인할 수 있는 내용:")
        print("   - Traces: 실행 추적 내역")
        print("   - Generations: LLM 호출 상세 정보")
        print("   - Spans: 각 노드별 실행 시간")
        print("   - Scores: 성능 평가")
        print("   - Metrics: 토큰 사용량, 비용, 지연 시간")
    else:
        print("\n1. Langfuse 설정:")
        print("   - .env 파일에 환경변수 추가")
        print("\n2. Langfuse 서버 실행 (자체 호스팅 시):")
        print("   docker run -d -p 3000:3000 langfuse/langfuse")
        print("\n3. 또는 클라우드 사용:")
        print("   https://cloud.langfuse.com 에서 계정 생성")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

