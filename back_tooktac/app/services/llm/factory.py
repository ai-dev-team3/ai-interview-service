"""LangChain 챗 모델 팩토리.

Gemini와 OpenAI를 둘 다 사용하며, 우선 모델이 실패하면 다른 쪽으로 폴백한다.
서비스 코드는 이 팩토리가 돌려주는 Runnable을 LCEL 체인에 그대로 끼워 쓰면 된다.
"""
import logging
from typing import Literal, Optional

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    OPENAI_API_KEY,
    OPENAI_MODEL_NAME,
)

logger = logging.getLogger(__name__)


def _build_gemini(
    temperature: Optional[float],
    max_tokens: Optional[int],
    top_p: Optional[float],
    top_k: Optional[int],
) -> Optional[ChatGoogleGenerativeAI]:
    if not GEMINI_API_KEY:
        return None
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_output_tokens"] = max_tokens
    if top_p is not None:
        kwargs["top_p"] = top_p
    if top_k is not None:
        kwargs["top_k"] = top_k
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME,
        google_api_key=GEMINI_API_KEY,
        **kwargs,
    )


def _build_openai(
    temperature: Optional[float],
    max_tokens: Optional[int],
    top_p: Optional[float],
) -> Optional[ChatOpenAI]:
    if not OPENAI_API_KEY:
        return None
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if top_p is not None:
        kwargs["top_p"] = top_p
    return ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        **kwargs,
    )


def get_chat_model(
    primary: Literal["gemini", "openai"] = "gemini",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    schema: Optional[type] = None,
) -> Runnable:
    """우선 모델 + 폴백 모델로 구성된 Runnable을 반환.

    한쪽 API 키가 없으면 있는 쪽 단독으로 동작하고,
    둘 다 없으면 RuntimeError를 낸다.

    schema 를 주면 그 모양으로만 응답하도록 모델에 강제한다(구조화 출력).
    Gemini 는 responseSchema, OpenAI 는 json_schema strict 모드를 쓴다.

    이건 프롬프트로 "JSON만 내보내세요"라고 부탁하는 것과 다르다. JsonOutputParser 는
    파서일 뿐이라, LLM 이 앞에 한마디만 붙여도 파싱이 깨진다. 구조화 출력은 모델이
    스키마를 벗어난 응답을 애초에 만들 수 없게 한다.

    스키마는 폴백으로 묶기 '전에' 각 모델에 건다 —
    RunnableWithFallbacks 에는 with_structured_output 이 없다.
    """
    gemini = _build_gemini(temperature, max_tokens, top_p, top_k)
    openai = _build_openai(temperature, max_tokens, top_p)  # top_k는 OpenAI 미지원

    ordered = [gemini, openai] if primary == "gemini" else [openai, gemini]
    available = [m for m in ordered if m is not None]

    if not available:
        raise RuntimeError(
            "사용 가능한 LLM이 없습니다. GEMINI_API_KEY 또는 OPENAI_API_KEY를 설정하세요."
        )

    if schema is not None:
        available = [m.with_structured_output(schema) for m in available]

    if len(available) == 1:
        logger.warning("LLM 폴백 없이 단독 구성: %s", type(available[0]).__name__)
        return available[0]

    return available[0].with_fallbacks(available[1:])
