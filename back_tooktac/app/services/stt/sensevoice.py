"""SenseVoice STT (로컬 GPU 추론).

실전 면접 전용이다. 연습 면접은 Clova를 그대로 쓴다.

실전에서 로컬 추론을 쓰는 이유:
  꼬리질문 에이전트가 직전 답변의 텍스트를 받아야 다음 질문을 만든다.
  즉 STT가 준비 시간(10초) 안에 끝나야 면접이 안 끊긴다. 외부 API 왕복으로는
  그 예산을 지키기 어렵다.

동시성 (자세 분석과 같은 원칙):
  모델은 프로세스당 하나만 올린다(VRAM 때문). 그런데 그 하나를 여러 요청이
  동시에 쓰면 GPU 메모리가 터진다. 그래서 세마포어로 동시 추론 수를 제한한다.
  MediaPipe 때와 달리 인스턴스를 연결마다 만들 수는 없다 — 모델이 GB 단위다.
"""
import logging
import os
import re
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 동시 GPU 추론 상한. 8GB VRAM 기준으로 잡았다.
# 넘어서면 대기한다 — 죽는 것보다 몇 초 늦는 게 낫다.
MAX_CONCURRENT_INFERENCE = int(os.getenv("SENSEVOICE_MAX_CONCURRENCY", "2"))

_MODEL = None
_MODEL_LOCK = threading.Lock()
_INFERENCE_SLOTS = threading.Semaphore(MAX_CONCURRENT_INFERENCE)


def _device() -> str:
    """GPU가 없으면 CPU로 떨어진다. 느리지만 죽지는 않는다."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:
        logger.exception("torch 확인 실패 — CPU로 진행")
    logger.warning("CUDA를 쓸 수 없다 — SenseVoice를 CPU로 돌린다 (느림)")
    return "cpu"


def get_model():
    """모델은 프로세스당 한 번만 올린다 (로드에 수 초, VRAM 수백 MB)."""
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                from funasr import AutoModel

                device = _device()
                started = time.perf_counter()
                # vad_model이 있어야 문장별 타임스탬프(sentence_info)가 나온다.
                # 말속도 점수가 segments의 start/end에 의존하므로 이게 없으면 점수가 죽는다.
                _MODEL = AutoModel(
                    model="iic/SenseVoiceSmall",
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": 30000},
                    device=device,
                    disable_update=True,
                )
                logger.info(
                    "SenseVoice 모델 로드 완료 (%.1f초, device=%s)",
                    time.perf_counter() - started,
                    device,
                )
    return _MODEL


def warm_up() -> None:
    """기동 시 미리 올린다. 첫 사용자가 모델 로딩을 기다리지 않게."""
    try:
        get_model()
    except Exception:
        logger.exception("SenseVoice 워밍업 실패 — 첫 요청 때 다시 시도한다")


class SenseVoiceClient:
    """STTService와 같은 계약: transcribe(wav) -> (text, {"segments": [...]})"""

    def transcribe(self, wav_path: str) -> Tuple[str, dict]:
        model = get_model()

        started = time.perf_counter()
        with _INFERENCE_SLOTS:
            waited = time.perf_counter() - started
            inference_started = time.perf_counter()
            result = model.generate(
                input=wav_path,
                language="ko",
                use_itn=True,
                batch_size_s=60,
            )
            inference_ms = (time.perf_counter() - inference_started) * 1000

        segments = _to_segments(result)
        text = " ".join(seg["text"] for seg in segments if seg["text"]).strip()

        logger.info(
            "SenseVoice STT 완료: 추론 %.0fms (대기 %.0fms), 세그먼트 %d개, %d자",
            inference_ms, waited * 1000, len(segments), len(text),
        )
        return text, {"segments": segments}


def _to_segments(result) -> list[dict]:
    """FunASR 출력을 Clova의 segments 모양으로 맞춘다.

    SpeechAnalyzer는 segments[].{text, start, end}(ms)만 본다.
    말속도 = 음절수 / (발화 구간의 합). 침묵은 빠져야 하므로 VAD 구간이 필요하다.

    sentence_info가 없으면(모델/버전에 따라 다르다) 전체 텍스트만이라도 건진다.
    그 경우 start=end=0 이라 말속도는 0이 되지만, 텍스트 평가는 정상 동작한다.
    """
    if not result:
        return []

    first = result[0] or {}
    sentences = first.get("sentence_info")

    if sentences:
        segments = []
        for s in sentences:
            text = _strip_tags(s.get("text", ""))
            if not text:
                continue
            segments.append({
                "text": text,
                "start": int(s.get("start", 0)),
                "end": int(s.get("end", 0)),
            })
        if segments:
            return segments

    text = _strip_tags(first.get("text", ""))
    if not text:
        return []
    logger.warning("SenseVoice에 sentence_info가 없다 — 말속도 점수를 낼 수 없다")
    return [{"text": text, "start": 0, "end": 0}]


_TAG = re.compile(r"<\|[^|]*\|>")
# SenseVoice는 감정·음향 이벤트를 인식한다. FunASR의 rich_transcription_postprocess를
# 쓰면 그것들이 이모지(😊, 👏 ...)로 텍스트에 박힌다. 답변 텍스트는 LLM 평가와
# 음절 수 계산에 그대로 들어가므로 이모지가 섞이면 안 된다. 그래서 직접 지운다.
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff️]"
)


def _strip_tags(text: Optional[str]) -> str:
    """<|ko|><|NEUTRAL|><|Speech|> 같은 태그와 이모지를 걷어낸다."""
    if not text:
        return ""
    cleaned = _EMOJI.sub("", _TAG.sub("", text))
    return " ".join(cleaned.split())
