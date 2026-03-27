"""출력 포맷팅 유틸리티

예제 파일들에서 사용하는 공통 출력 함수들을 제공합니다.
"""


def print_header(title: str, emoji: str = "", width: int = 60) -> None:
    """헤더 출력

    Args:
        title: 제목 텍스트
        emoji: 제목 앞에 표시할 이모지 (선택)
        width: 구분선 너비
    """
    print("=" * width)
    if emoji:
        print(f"{emoji} {title}")
    else:
        print(title)
    print("=" * width)


def print_section(title: str, level: int = 1, emoji: str = "") -> None:
    """섹션 제목 출력

    Args:
        title: 섹션 제목
        level: 들여쓰기 레벨 (1-3)
        emoji: 제목 앞에 표시할 이모지 (선택)
    """
    prefix = "-" * (level * 2)
    if emoji:
        print(f"\n{prefix} {emoji} {title}")
    else:
        print(f"\n{prefix} {title}")


def print_result(label: str, value: str, indent: int = 3) -> None:
    """결과 라벨-값 쌍 출력

    Args:
        label: 라벨 텍스트
        value: 값 텍스트
        indent: 들여쓰기 공백 수
    """
    print(f"{' ' * indent}{label}: {value}")


def print_separator(char: str = "-", width: int = 60) -> None:
    """구분선 출력

    Args:
        char: 구분선에 사용할 문자
        width: 구분선 너비
    """
    print(char * width)


def print_agent_info(info: dict, indent: int = 3) -> None:
    """Agent 정보 출력

    Args:
        info: Agent.get_info()의 반환값
        indent: 들여쓰기 공백 수
    """
    prefix = " " * indent

    if "type" in info:
        print(f"{prefix}타입: {info['type']}")
    if "model" in info:
        print(f"{prefix}모델: {info['model']}")
    if "architecture" in info:
        print(f"{prefix}아키텍처: {info['architecture']}")
    if "nodes" in info:
        nodes = info['nodes']
        if isinstance(nodes, list):
            print(f"{prefix}노드: {', '.join(nodes)}")
        else:
            print(f"{prefix}노드: {nodes}")
    if "flow" in info:
        print(f"{prefix}흐름: {info['flow']}")


def print_test_case(index: int, description: str, width: int = 60) -> None:
    """테스트 케이스 시작 출력

    Args:
        index: 테스트 번호
        description: 테스트 설명
        width: 구분선 너비
    """
    print(f"\n{'=' * width}")
    print(f"예제 {index}: {description}")
    print(f"{'=' * width}\n")


def print_success(message: str = "완료") -> None:
    """성공 메시지 출력"""
    print(f"✅ {message}")


def print_error(message: str) -> None:
    """에러 메시지 출력"""
    print(f"❌ {message}")


def print_warning(message: str) -> None:
    """경고 메시지 출력"""
    print(f"⚠️ {message}")


def print_info(message: str) -> None:
    """정보 메시지 출력"""
    print(f"📝 {message}")
