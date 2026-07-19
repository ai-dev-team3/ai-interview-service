"""Langfuse LLM 추적 핸들러.

이 프로젝트의 모든 LLM 호출은 LangChain(ChatOpenAI/ChatGoogleGenerativeAI)을
통과한다. 여기서 만든 콜백 핸들러를 모델 생성 시 callbacks에 넣으면
각 호출의 모델/입출력/토큰/지연시간이 self-host Langfuse로 전송되어
대시보드(별도 Next.js 앱)가 조회할 수 있게 된다.

왜 langfuse 자체 CallbackHandler를 안 쓰나:
  - langfuse v3의 CallbackHandler는 OpenTelemetry가 protobuf>=5를 끌어와
    mediapipe(protobuf<5)와 충돌한다.
  - langfuse v2의 CallbackHandler는 옛 `langchain.schema` 경로를 import하는데
    이 프로젝트의 langchain-core 1.x에는 그 경로가 없다.
그래서 langchain 비의존·protobuf 비의존인 langfuse '저수준 클라이언트'만 쓰고,
LangChain 연결은 이 파일의 얇은 BaseCallbackHandler로 직접 붙인다.

LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY 가 없으면 추적은 꺼지고 앱은 그대로 동작한다.
키/호스트는 langfuse SDK가 환경변수(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
LANGFUSE_HOST)에서 직접 읽는다.
"""
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from app.observability.context import current_feature

logger = logging.getLogger(__name__)

# 기능 표시가 없는 곳에서 온 호출. 대시보드에서 '미분류'로 묶인다.
UNTAGGED = "llm-call"


def _messages_to_text(messages: List[List[Any]]) -> str:
    """on_chat_model_start의 messages(리스트의 리스트)를 사람이 읽을 텍스트로."""
    parts = []
    for batch in messages:
        for m in batch:
            content = getattr(m, "content", m)
            parts.append(content if isinstance(content, str) else str(content))
    return "\n".join(parts)


def _model_name(serialized: Optional[dict], metadata: Optional[dict]) -> str:
    if metadata and metadata.get("ls_model_name"):
        return metadata["ls_model_name"]
    kwargs = (serialized or {}).get("kwargs", {})
    return kwargs.get("model") or kwargs.get("model_name") or "unknown"


def _parse_result(response: Any):
    """LLMResult에서 출력 텍스트와 토큰 usage를 뽑는다."""
    output = ""
    usage = None
    try:
        gen0 = response.generations[0][0]
        message = getattr(gen0, "message", None)
        output = getattr(gen0, "text", "") or (getattr(message, "content", "") if message else "")

        # langchain-core 1.x는 provider 무관하게 usage_metadata를 채운다.
        um = getattr(message, "usage_metadata", None) if message else None
        if um:
            usage = {
                "input": um.get("input_tokens"),
                "output": um.get("output_tokens"),
                "total": um.get("total_tokens"),
                "unit": "TOKENS",
            }
        elif getattr(response, "llm_output", None):
            tu = (response.llm_output or {}).get("token_usage") or {}
            if tu:
                usage = {
                    "input": tu.get("prompt_tokens"),
                    "output": tu.get("completion_tokens"),
                    "total": tu.get("total_tokens"),
                    "unit": "TOKENS",
                }
    except Exception:
        logger.debug("Langfuse 결과 파싱 실패", exc_info=True)
    return output, usage


class LangfuseTracer(BaseCallbackHandler):
    """LangChain 콜백 → langfuse 저수준 클라이언트 브리지.

    LLM 호출 하나당 generation 1개(각자의 trace)를 남긴다. 비용은 Langfuse 서버가
    모델명 + usage로 자동 계산한다.

    generation 이름은 그 호출이 속한 기능(context.py)으로 남긴다 — 대시보드가
    이 이름으로 기능별 집계를 한다.
    """

    def __init__(self, client: Any):
        self._client = client
        self._gens: Dict[UUID, Any] = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        try:
            self._gens[run_id] = self._client.generation(
                name=current_feature() or UNTAGGED,
                model=_model_name(serialized, metadata),
                input=_messages_to_text(messages),
                metadata=metadata,
            )
        except Exception:
            logger.debug("Langfuse on_chat_model_start 실패", exc_info=True)

    def on_llm_end(self, response, *, run_id, **kwargs):
        gen = self._gens.pop(run_id, None)
        if gen is None:
            return
        try:
            output, usage = _parse_result(response)
            gen.end(output=output, usage=usage)
        except Exception:
            logger.debug("Langfuse on_llm_end 실패", exc_info=True)

    def on_llm_error(self, error, *, run_id, **kwargs):
        gen = self._gens.pop(run_id, None)
        if gen is None:
            return
        try:
            gen.end(level="ERROR", status_message=str(error))
        except Exception:
            logger.debug("Langfuse on_llm_error 실패", exc_info=True)


@lru_cache(maxsize=1)
def _get_handler() -> Optional[BaseCallbackHandler]:
    """공용 트레이서를 한 번만 만들어 재사용한다(내부 Langfuse 클라이언트도 싱글턴)."""
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        logger.warning("langfuse 패키지가 없어 LLM 추적을 건너뜁니다.")
        return None
    try:
        client = Langfuse()  # 키/호스트는 환경변수에서 읽는다
        logger.info("Langfuse LLM 추적 활성화 (host=%s)", os.getenv("LANGFUSE_HOST", "기본값"))
        return LangfuseTracer(client)
    except Exception:
        logger.warning("Langfuse 초기화 실패 — LLM 추적 비활성화", exc_info=True)
        return None


def langfuse_callbacks() -> List[BaseCallbackHandler]:
    """LangChain 챗 모델 생성 시 callbacks= 인자로 넣을 리스트를 반환한다.

    추적이 꺼져 있으면 빈 리스트 → LangChain은 아무 콜백도 붙이지 않는다.
    """
    handler = _get_handler()
    return [handler] if handler else []
