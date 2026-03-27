#!/usr/bin/env python3
"""
Docker 컨테이너 정리 유틸리티 스크립트

code-exec-session-* 이름의 컨테이너들을 찾아서 정리합니다.
"""

import docker
import sys
from typing import List


def cleanup_code_exec_containers() -> int:
    """code-exec-session-* 이름의 컨테이너들을 정리
    
    Returns:
        정리된 컨테이너 개수
    """
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"❌ Docker 클라이언트 연결 실패: {str(e)}")
        return 0
    
    # code-exec-session-* 이름의 컨테이너 찾기
    containers = client.containers.list(all=True, filters={"name": "code-exec-session-"})
    
    if not containers:
        print("✅ 정리할 컨테이너가 없습니다.")
        return 0
    
    print(f"🔍 {len(containers)}개의 컨테이너를 찾았습니다.")
    
    cleaned_count = 0
    for container in containers:
        try:
            container_name = container.name
            container_status = container.status
            
            print(f"  - {container_name} ({container_status})")
            
            # 실행 중이면 중지
            if container_status == "running":
                container.stop()
                print(f"    ✅ 중지 완료")
            
            # 컨테이너 제거
            container.remove()
            print(f"    ✅ 제거 완료")
            cleaned_count += 1
            
        except docker.errors.NotFound:
            # 이미 삭제된 컨테이너
            print(f"    ⚠️ 이미 삭제됨")
        except Exception as e:
            print(f"    ❌ 정리 실패: {str(e)}")
    
    print(f"\n✅ 총 {cleaned_count}개의 컨테이너를 정리했습니다.")
    return cleaned_count


def main():
    """메인 함수"""
    print("🧹 Docker 컨테이너 정리 시작...\n")
    
    cleaned_count = cleanup_code_exec_containers()
    
    if cleaned_count > 0:
        print(f"\n✅ 정리 완료: {cleaned_count}개 컨테이너 제거")
        sys.exit(0)
    else:
        print("\n✅ 정리할 컨테이너가 없습니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()

