"""
Checkpointer 모듈 - Agent 상태 지속성 관리
"""

from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.postgres import AsyncPostgresSaver  # type: ignore[import]
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    AsyncPostgresSaver = None

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


class CheckpointerFactory:
    """Checkpointer 생성 팩토리 클래스"""
    
    @staticmethod
    def create_in_memory() -> MemorySaver:
        """
        메모리 기반 Checkpointer 생성 (개발/테스트용)
        
        Returns:
            MemorySaver: 메모리 기반 Checkpointer 인스턴스
        
        특징:
            - 빠른 속도
            - 프로세스 종료 시 데이터 소실
            - 테스트 및 개발에 적합
        """
        return MemorySaver()
    
    @staticmethod
    def create_postgres(conn_string: str) -> Optional["BaseCheckpointSaver"]:
        """
        PostgreSQL 기반 Checkpointer 생성 (프로덕션용)
        
        Args:
            conn_string: PostgreSQL 연결 문자열
                예: "postgresql://user:password@localhost:5432/dbname"
        
        Returns:
            AsyncPostgresSaver: PostgreSQL 기반 Checkpointer 인스턴스
        
        특징:
            - 영구 저장
            - 높은 안정성
            - 프로덕션 환경에 적합
        
        Raises:
            ImportError: langgraph-checkpoint-postgres가 설치되지 않은 경우
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL Checkpointer를 사용하려면 다음 패키지를 설치하세요:\n"
                "  uv add langgraph-checkpoint-postgres"
            )
        
        return AsyncPostgresSaver.from_conn_string(conn_string)
    
    @staticmethod
    def create_from_config(config: dict) -> "BaseCheckpointSaver":
        """
        설정에서 Checkpointer 생성
        
        Args:
            config: Checkpointer 설정 딕셔너리
                - type: "memory" | "postgres"
                - conn_string: (postgres인 경우) 연결 문자열
        
        Returns:
            BaseCheckpointSaver: Checkpointer 인스턴스
        
        예시:
            >>> config = {"type": "memory"}
            >>> checkpointer = CheckpointerFactory.create_from_config(config)
            
            >>> config = {
            ...     "type": "postgres",
            ...     "conn_string": "postgresql://user:pass@localhost/db"
            ... }
            >>> checkpointer = CheckpointerFactory.create_from_config(config)
        """
        checkpointer_type = config.get("type", "memory").lower()
        
        if checkpointer_type == "memory":
            return CheckpointerFactory.create_in_memory()
        elif checkpointer_type == "postgres":
            conn_string = config.get("conn_string")
            if not conn_string:
                raise ValueError("PostgreSQL Checkpointer를 사용하려면 'conn_string'이 필요합니다.")
            return CheckpointerFactory.create_postgres(conn_string)
        else:
            raise ValueError(f"지원하지 않는 Checkpointer 타입: {checkpointer_type}")
    
    @staticmethod
    def create_from_env() -> "BaseCheckpointSaver":
        """
        환경 변수에서 Checkpointer 생성
        
        환경 변수:
            - CHECKPOINTER_TYPE: "memory" | "postgres" (기본값: "memory")
            - POSTGRES_CONN_STRING: PostgreSQL 연결 문자열 (postgres 타입인 경우)
        
        Returns:
            BaseCheckpointSaver: Checkpointer 인스턴스
        """
        import os
        
        checkpointer_type = os.getenv("CHECKPOINTER_TYPE", "memory").lower()
        
        if checkpointer_type == "memory":
            return CheckpointerFactory.create_in_memory()
        elif checkpointer_type == "postgres":
            conn_string = os.getenv("POSTGRES_CONN_STRING")
            if not conn_string:
                raise ValueError(
                    "PostgreSQL Checkpointer를 사용하려면 POSTGRES_CONN_STRING 환경 변수가 필요합니다."
                )
            return CheckpointerFactory.create_postgres(conn_string)
        else:
            raise ValueError(f"지원하지 않는 Checkpointer 타입: {checkpointer_type}")


def create_checkpointer(
    checkpointer_type: str = "memory",
    conn_string: Optional[str] = None
) -> "BaseCheckpointSaver":
    """
    Checkpointer 생성 헬퍼 함수
    
    Args:
        checkpointer_type: Checkpointer 타입 ("memory" | "postgres")
        conn_string: PostgreSQL 연결 문자열 (postgres 타입인 경우)
    
    Returns:
        BaseCheckpointSaver: Checkpointer 인스턴스
    
    예시:
        >>> # 메모리 Checkpointer
        >>> checkpointer = create_checkpointer("memory")
        
        >>> # PostgreSQL Checkpointer
        >>> checkpointer = create_checkpointer(
        ...     "postgres",
        ...     "postgresql://user:pass@localhost/db"
        ... )
    """
    if checkpointer_type == "memory":
        return CheckpointerFactory.create_in_memory()
    elif checkpointer_type == "postgres":
        if not conn_string:
            raise ValueError("PostgreSQL Checkpointer를 사용하려면 'conn_string'이 필요합니다.")
        return CheckpointerFactory.create_postgres(conn_string)
    else:
        raise ValueError(f"지원하지 않는 Checkpointer 타입: {checkpointer_type}")


def get_default_checkpointer() -> MemorySaver:
    """
    기본 Checkpointer 반환 (메모리 기반)
    
    Returns:
        MemorySaver: 메모리 기반 Checkpointer 인스턴스
    
    특징:
        - 개발 및 테스트에 즉시 사용 가능
        - 추가 설정 불필요
        - 프로세스 종료 시 데이터 소실
    
    사용 예시:
        >>> from src.agents.memory.checkpointer import get_default_checkpointer
        >>> checkpointer = get_default_checkpointer()
        >>> agent = LangGraphAgentTools(checkpointer=checkpointer)
    
    참고:
        프로덕션 환경에서는 PostgresSaver 사용을 권장합니다.
        하지만 현재는 개발 단계이므로 MemorySaver로 충분합니다.
    """
    return CheckpointerFactory.create_in_memory()


def list_threads(checkpointer: "BaseCheckpointSaver") -> list[str]:
    """
    Checkpointer에 저장된 모든 thread ID 목록 반환
    
    Args:
        checkpointer: Checkpointer 인스턴스
    
    Returns:
        list[str]: Thread ID 목록
    
    예시:
        >>> from src.agents.memory.checkpointer import get_default_checkpointer, list_threads
        >>> checkpointer = get_default_checkpointer()
        >>> threads = list_threads(checkpointer)
        >>> print(f"저장된 thread 수: {len(threads)}")
    """
    try:
        # list() 메서드를 사용하여 모든 thread ID 가져오기
        thread_ids = checkpointer.list()
        return list(thread_ids) if thread_ids else []
    except Exception as e:
        print(f"⚠️ Thread 목록 조회 중 오류 발생: {str(e)}")
        return []


def delete_thread(checkpointer: "BaseCheckpointSaver", thread_id: str) -> bool:
    """
    특정 thread 삭제
    
    Args:
        checkpointer: Checkpointer 인스턴스
        thread_id: 삭제할 thread ID
    
    Returns:
        bool: 삭제 성공 여부
    
    예시:
        >>> from src.agents.memory.checkpointer import get_default_checkpointer, delete_thread
        >>> checkpointer = get_default_checkpointer()
        >>> success = delete_thread(checkpointer, "thread-1")
        >>> if success:
        ...     print("Thread 삭제 완료")
    """
    try:
        checkpointer.delete_thread({"configurable": {"thread_id": thread_id}})
        return True
    except Exception as e:
        print(f"⚠️ Thread 삭제 중 오류 발생 (thread_id: {thread_id}): {str(e)}")
        return False


def clear_all_threads(checkpointer: "BaseCheckpointSaver") -> int:
    """
    Checkpointer에 저장된 모든 thread 삭제
    
    Args:
        checkpointer: Checkpointer 인스턴스
    
    Returns:
        int: 삭제된 thread 수
    
    예시:
        >>> from src.agents.memory.checkpointer import get_default_checkpointer, clear_all_threads
        >>> checkpointer = get_default_checkpointer()
        >>> deleted_count = clear_all_threads(checkpointer)
        >>> print(f"{deleted_count}개의 thread가 삭제되었습니다.")
    """
    threads = list_threads(checkpointer)
    deleted_count = 0
    
    for thread_id in threads:
        if delete_thread(checkpointer, thread_id):
            deleted_count += 1
    
    return deleted_count

