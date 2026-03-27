"""Structured Output 예제

LangChain Structured Output 기능을 사용하여
모델 응답을 구조화된 형식으로 받는 예제입니다.
"""
from examples._utils import PROJECT_ROOT  # noqa: F401 - sys.path 설정
from examples._utils import (
    print_header,
    print_section,
    print_success,
    print_error,
)

from pydantic import BaseModel, Field
from langchain.messages import AIMessage
from src.agents.structured_output import ToolStrategy, ProviderStrategy


# ============ 스키마 정의 ============


class ContactInfo(BaseModel):
    """연락처 정보"""

    name: str = Field(description="이름")
    email: str = Field(description="이메일 주소")
    phone: str = Field(description="전화번호")


class WeatherData(BaseModel):
    """날씨 데이터"""

    city: str = Field(description="도시명")
    temperature: float = Field(description="온도 (섭씨)")
    condition: str = Field(description="날씨 상태")
    humidity: float = Field(description="습도 (%)")


class MeetingNotes(BaseModel):
    """회의 기록"""

    title: str = Field(description="회의 제목")
    date: str = Field(description="날짜")
    attendees: list[str] = Field(description="참석자 목록")
    action_items: list[str] = Field(description="액션 아이템")
    summary: str = Field(description="요약")


# ============ 테스트 함수들 ============


def test_tool_strategy():
    """ToolStrategy 사용 예제"""
    print_header("ToolStrategy 예제")

    strategy = ToolStrategy(ContactInfo, tool_name="extract_contact")

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "extract_contact",
                "args": {
                    "name": "홍길동",
                    "email": "hong@example.com",
                    "phone": "010-1234-5678",
                },
                "id": "call_123",
            }
        ],
    )

    try:
        result = strategy.extract(mock_response)
        print_success("추출 성공:")
        print(f"   이름: {result.name}")
        print(f"   이메일: {result.email}")
        print(f"   전화번호: {result.phone}")
        print(f"\n   Type: {type(result)}")
        print(f"   Pydantic Model: {isinstance(result, ContactInfo)}")
    except Exception as e:
        print_error(f"에러: {e}")


def test_provider_strategy():
    """ProviderStrategy 사용 예제"""
    print_section("ProviderStrategy 예제")
    print()

    strategy = ProviderStrategy(WeatherData)

    mock_response = AIMessage(
        content='{"city": "서울", "temperature": 15.5, "condition": "맑음", "humidity": 60.0}'
    )

    try:
        result = strategy.extract(mock_response)
        print_success("추출 성공:")
        print(f"   도시: {result.city}")
        print(f"   온도: {result.temperature}°C")
        print(f"   상태: {result.condition}")
        print(f"   습도: {result.humidity}%")
        print(f"\n   Type: {type(result)}")
    except Exception as e:
        print_error(f"에러: {e}")


def test_validation():
    """검증 기능 테스트"""
    print_section("Validation 테스트")
    print()

    strategy = ToolStrategy(ContactInfo)

    valid_data = {
        "name": "김철수",
        "email": "kim@example.com",
        "phone": "010-9876-5432",
    }

    try:
        result = strategy.validate(valid_data)
        print_success(f"검증 성공: {result.name}")
    except Exception as e:
        print_error(f"검증 실패: {e}")

    invalid_data = {"name": "이영희"}  # email, phone 누락

    try:
        result = strategy.validate(invalid_data)
        print_success(f"검증 성공: {result.name}")
    except Exception as e:
        print_success(f"예상된 검증 실패: {e}")


def test_complex_schema():
    """복잡한 스키마 테스트"""
    print_section("복잡한 스키마 테스트")
    print()

    strategy = ToolStrategy(MeetingNotes, tool_name="create_meeting_notes")

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "create_meeting_notes",
                "args": {
                    "title": "프로젝트 회의",
                    "date": "2025-01-27",
                    "attendees": ["홍길동", "김철수", "이영희"],
                    "action_items": ["개발 계획서 작성", "다음 회의 일정 확정"],
                    "summary": "프로젝트 진행 상황을 논의하고 향후 계획을 수립했습니다.",
                },
                "id": "call_456",
            }
        ],
    )

    try:
        result = strategy.extract(mock_response)
        print_success("회의 기록 추출 성공:")
        print(f"   제목: {result.title}")
        print(f"   날짜: {result.date}")
        print(f"   참석자: {', '.join(result.attendees)}")
        print(f"   액션 아이템: {len(result.action_items)}개")
        for i, item in enumerate(result.action_items, 1):
            print(f"     {i}. {item}")
        print(f"   요약: {result.summary}")
    except Exception as e:
        print_error(f"에러: {e}")


def test_tool_generation():
    """도구 생성 테스트"""
    print_section("도구 생성 테스트")
    print()

    strategy = ToolStrategy(ContactInfo)
    tool = strategy.get_tool()

    print_success("도구 생성 성공:")
    print(f"   이름: {tool.name}")
    print(f"   설명: {tool.description}")
    print(f"   Args Schema: {str(tool.args_schema)[:100]}...")


def main():
    """Structured Output 예제"""
    print_header("Structured Output 예제")
    print()

    test_tool_strategy()
    test_provider_strategy()
    test_validation()
    test_complex_schema()
    test_tool_generation()

    print_section("결과")
    print_success("모든 예제 실행 완료")


if __name__ == "__main__":
    main()
