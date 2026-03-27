"""
Code Execution Factory - 코드 실행 환경 팩토리

Docker 중심 아키텍처로 단순화:
- DOCKER: DockerExecutor (독립적인 컨테이너 실행)
- 로컬 환경 실행자 제거: 격리되지 않은 실행은 보안상 위험
- 세션 관리 제거: 각 실행은 독립적인 컨테이너에서 수행
"""

import os
from typing import Dict, Type, Optional
from .base import CodeExecutor, ExecutionEnvironment
from .executors.docker_executor import DockerExecutor


class CodeExecutionFactory:
    """코드 실행 환경 팩토리
    
    Docker 중심 아키텍처:
    - DOCKER: DockerExecutor 사용 (독립적인 컨테이너 실행)
    """
    
    _executors: Dict[ExecutionEnvironment, Type[CodeExecutor]] = {
        ExecutionEnvironment.DOCKER: DockerExecutor,  # Docker 컨테이너 실행
        # 로컬 환경 실행자 제거됨:
        # - LOCAL: Docker로 통일 (격리된 환경 필요)
        # - IPYTHON: DockerExecutor 사용
        # - REPL: DockerExecutor 사용
        # 향후 추가:
        # ExecutionEnvironment.CLOUD: CloudExecutor,
        # ExecutionEnvironment.EXTERNAL: ExternalExecutor,
    }
    
    _instances: Dict[ExecutionEnvironment, CodeExecutor] = {}
    
    @classmethod
    def create_executor(
        cls,
        environment: ExecutionEnvironment,
        **kwargs
    ) -> CodeExecutor:
        """실행 환경에 맞는 실행자 생성
        
        Args:
            environment: 실행 환경 타입
            **kwargs: 실행 환경별 추가 파라미터
                     - docker: docker_image
                     - cloud: api_endpoint, api_key
                     - external: execution_command
        
        Returns:
            CodeExecutor 인스턴스
        """
        if environment not in cls._executors:
            raise ValueError(f"지원하지 않는 실행 환경: {environment}")
        
        executor_class = cls._executors[environment]
        
        # 싱글톤 패턴 (선택적)
        cache_key = (environment, tuple(sorted(kwargs.items())))
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # 실행 환경별 초기화
        if environment == ExecutionEnvironment.DOCKER:
            docker_image = kwargs.get("docker_image") or os.getenv("DOCKER_IMAGE", "csv-sandbox:test")
            executor = executor_class(default_image=docker_image)
        else:
            executor = executor_class(**kwargs)
        
        cls._instances[cache_key] = executor
        return executor
    
    @classmethod
    def get_available_environments(cls) -> list[ExecutionEnvironment]:
        """사용 가능한 실행 환경 목록 반환"""
        available = []
        for env, executor_class in cls._executors.items():
            try:
                executor = cls.create_executor(env)
                if executor.is_available():
                    available.append(env)
            except Exception:
                continue
        return available
    
    @classmethod
    def register_executor(
        cls,
        environment: ExecutionEnvironment,
        executor_class: Type[CodeExecutor]
    ):
        """새로운 실행 환경 등록 (플러그인 방식)"""
        cls._executors[environment] = executor_class
        print(f"✅ 실행 환경 등록됨: {environment.value}")

