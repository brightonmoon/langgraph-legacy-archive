"""
설정 관리 모듈 - LangSmith 설정 및 모델 초기화 헬퍼
"""

import logging
import os
import warnings
from datetime import datetime
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)


def setup_langsmith_disabled():
    """LangSmith 완전 비활성화"""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGSMITH_API_KEY"] = ""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    warnings.filterwarnings("ignore", category=UserWarning, module="langsmith")
    warnings.filterwarnings("ignore", category=UserWarning, module="langchain")


def init_chat_model_helper(
    model_name: str = None,
    api_key: str = None,
    temperature: float = 0.7,
    model_type: str = "ollama"
):
    """모델 초기화 헬퍼 함수

    Args:
        model_name: 사용할 모델명
                   - Ollama: "gpt-oss:120b-cloud", "kimi-k2:1t-cloud", "qwen2.5-coder:latest" 등
                   - Anthropic: "claude-sonnet-4-5-20250929"
                   - OpenAI: "gpt-4o"
        api_key: API 키 (None이면 환경변수에서 가져옴)
        temperature: 모델 temperature
        model_type: 모델 타입 ("ollama", "anthropic", "openai" 등)
                    None이면 model_name에서 자동 추론

    Returns:
        LangChain ChatModel 인스턴스 또는 None
    """
    try:
        # 환경변수 로드
        load_dotenv()

        # 모델명 결정
        if model_name is None:
            if model_type == "ollama":
                model_name = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")
            elif model_type == "anthropic":
                model_name = os.getenv("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-5-20250929")
            elif model_type == "openai":
                model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
            else:
                model_name = os.getenv("OLLAMA_MODEL_NAME", "gpt-oss:120b-cloud")

        # 모델 타입 자동 추론 (model_name에 타입이 포함된 경우)
        if ":" in model_name and not model_name.startswith("ollama:") and not model_name.startswith("anthropic:") and not model_name.startswith("openai:"):
            # model_name에 타입이 없는 경우, model_type을 기반으로 접두사 추가
            if model_type == "ollama":
                model_str = f"ollama:{model_name}"
            elif model_type == "anthropic":
                model_str = f"anthropic:{model_name}"
            elif model_type == "openai":
                model_str = f"openai:{model_name}"
            else:
                model_str = f"ollama:{model_name}"
        elif model_name.startswith("ollama:") or model_name.startswith("anthropic:") or model_name.startswith("openai:"):
            # 이미 접두사가 있는 경우 그대로 사용
            model_str = model_name
        else:
            # 기본값: ollama
            model_str = f"ollama:{model_name}"

        # API 키 결정
        if api_key is None:
            if model_str.startswith("ollama:"):
                api_key = os.getenv("OLLAMA_API_KEY")
            elif model_str.startswith("anthropic:"):
                api_key = os.getenv("ANTHROPIC_API_KEY")
            elif model_str.startswith("openai:"):
                api_key = os.getenv("OPENAI_API_KEY")

        # Ollama 모델인 경우 API 키가 없어도 경고만 (로컬 모델 사용 가능)
        if model_str.startswith("ollama:") and not api_key:
            logger.warning("⚠️  OLLAMA_API_KEY가 설정되지 않았습니다.")
            logger.warning("   .env 파일에 OLLAMA_API_KEY=your_api_key를 추가하세요.")
            logger.warning("   또는 로컬 Ollama 모델을 사용하려면 ChatOllama를 직접 사용하세요.")
            # API 키 없이도 시도 (로컬 모델일 수 있음)
            try:
                model = init_chat_model(
                    model_str,
                    temperature=temperature
                )
            except Exception as e:
                logger.error(f"❌ 모델 초기화 실패: {str(e)}")
                return None
        else:
            # 모델 초기화
            model = init_chat_model(
                model_str,
                api_key=api_key,
                temperature=temperature
            )

        logger.info("✅ 모델이 성공적으로 초기화되었습니다.")
        logger.info(f"   모델: {model_str}")
        logger.info(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # API key is NOT logged for security

        return model

    except Exception as e:
        logger.error(f"❌ 모델 초기화 중 오류 발생: {str(e)}")
        return None


# 하위 호환성을 위한 함수 (점진적 마이그레이션용)
def create_ollama_model(model_name: str = None):
    """Ollama 모델 생성 및 반환 (레거시 함수)

    이 함수는 하위 호환성을 위해 제공됩니다.
    새 코드에서는 init_chat_model_helper()를 직접 사용하세요.

    Args:
        model_name: 사용할 모델명 (예: "gpt-oss:120b-cloud", "kimi-k2:1t-cloud")
                    None이면 환경변수 OLLAMA_MODEL_NAME 또는 기본값 사용

    Returns:
        LangChain ChatModel 인스턴스 또는 None
    """
    return init_chat_model_helper(model_name=model_name, model_type="ollama")
