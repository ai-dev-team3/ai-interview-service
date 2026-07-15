"""SenseVoice STT (로컬 GPU 추론).

실전 면접 전용이다. 연습 면접은 Clova를 그대로 쓴다.

실전에서 로컬 추론을 쓰는 이유:
  꼬리질문 에이전트가 직전 답변의 텍스트를 받아야 다음 질문을 만든다.
  즉 STT가 준비 시간(10초) 안에 끝나야 면접이 안 끊긴다.
  실측: 70초 오디오 -> 약 0.8초 (RTF 0.01).

VAD를 따로 돌리는 이유:
  SenseVoice는 타임스탬프를 내지 않는다. AutoModel에 vad_model을 붙여도 출력은
  {key, text} 뿐이고 sentence_info가 없다 (merge_vad=False로도 마찬가지).
  그런데 말속도는 '발화 구간의 합'(침묵 제외)이 있어야 계산된다. 타임스탬프가
  없으면 예외 없이 speed 점수만 0이 된다 — 실측으로 확인했다.

  그래서 VAD를 따로 한 번 더 돌려 발화 구간의 길이만 얻는다.

  구간별로 쪼개서 추론하는 방법도 해봤지만 버렸다. 짧은 조각(3초)에서 SenseVoice가
  음절 단위로 띄어쓰기를 깨뜨린다("그러 한 일 들 을 잘 처리 해낼 수 있 기").
  이 텍스트는 그대로 LLM 평가에 들어가므로 품질을 떨어뜨린다. 통짜로 추론해야
  깨끗하다.

동시성 (자세 분석과 같은 원칙):
  모델은 프로세스당 하나만 올린다(VRAM). 그 하나를 여러 요청이 동시에 쓰면
  GPU 메모리가 터지므로 세마포어로 동시 추론 수를 제한한다. MediaPipe와 달리
  연결마다 인스턴스를 만들 수는 없다 — 모델이 GB 단위다.
"""
import logging
import os
import re
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000

# VAD 한 구간의 최대 길이. SenseVoice는 짧은 발화로 학습돼 너무 긴 구간은 품질이 떨어진다.
MAX_SEGMENT_MS = 30000

# 동시 GPU 추론 상한. 8GB VRAM 기준.
# 넘으면 대기한다 — 죽는 것보다 몇 초 늦는 게 낫다.
MAX_CONCURRENT_INFERENCE = int(os.getenv("SENSEVOICE_MAX_CONCURRENCY", "2"))

_MODELS = None  # asr (내부에 VAD 내장)
_MODEL_LOCK = threading.Lock()
_INFERENCE_SLOTS = threading.Semaphore(MAX_CONCURRENT_INFERENCE)

# asr.generate 가 내부에서 돌린 VAD 의 발화 구간을 담는다. asr 객체 하나를 동시에 여러
# 스레드가 쓰므로(_INFERENCE_SLOTS) 반드시 스레드별로 따로 담아야 한다.
_captured = threading.local()
_CAPTURE_FLAG = "_sv_capture_installed"


def _ensure_capture_installed(asr) -> None:
    """asr.vad_model.inference 를 한 번만 감싸, 그 발화 구간을 _captured 에 기록한다.

    SenseVoice 는 타임스탬프를 내지 않아 말속도용 발화 구간을 따로 얻어야 한다. 예전엔
    같은 오디오에 VAD 를 한 번 더 돌렸는데(전체 STT 의 약 21%), 그 구간은 asr 가 내부에서
    이미 계산해 버리고 있었다. 여기서 그 값을 주워오면 두 번째 패스가 통째로 사라진다.
    """
    if getattr(asr, _CAPTURE_FLAG, False):
        return

    original = asr.vad_model.inference

    def capture(*args, **kwargs):
        out = original(*args, **kwargs)
        try:
            results = out[0]  # (results, meta) 튜플. results[0]["value"] = [[start_ms, end_ms], ...]
            _captured.spans = [(int(s), int(e)) for s, e in results[0]["value"]]
        except (IndexError, KeyError, TypeError, ValueError):
            _captured.spans = []
        return out

    asr.vad_model.inference = capture
    setattr(asr, _CAPTURE_FLAG, True)


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


def get_models():
    """모델은 프로세스당 한 번만 올린다 (로드 수 초, 첫 실행이면 다운로드).

    asr 하나만 올린다. vad_model 을 붙여 두면 내부에서 알아서 끊어 추론하고 결과를
    합쳐 준다 — 이때 텍스트가 가장 깨끗하고, 그 과정에서 계산되는 발화 구간을
    _ensure_capture_installed 로 주워 쓴다. 별도 VAD 모델을 따로 올리지 않는다.
    """
    global _MODELS
    if _MODELS is None:
        with _MODEL_LOCK:
            if _MODELS is None:
                from funasr import AutoModel

                device = _device()
                started = time.perf_counter()
                asr = AutoModel(
                    model="iic/SenseVoiceSmall",
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": MAX_SEGMENT_MS},
                    device=device,
                    disable_update=True,
                )
                _ensure_capture_installed(asr)
                _MODELS = asr
                logger.info(
                    "SenseVoice 모델 로드 완료 (%.1f초, device=%s)",
                    time.perf_counter() - started, device,
                )
    return _MODELS


def warm_up() -> None:
    """기동 시 미리 올린다. 첫 사용자가 모델 로딩을 기다리지 않게."""
    try:
        get_models()
    except Exception:
        logger.exception("SenseVoice 워밍업 실패 — 첫 요청 때 다시 시도한다")


class SenseVoiceClient:
    """STTService와 같은 계약: transcribe(wav) -> (text, {"segments": [...]})"""

    def transcribe(self, wav_path: str) -> Tuple[str, dict]:
        import librosa

        asr = get_models()
        _ensure_capture_installed(asr)  # get_models 가 mock 된 테스트 경로까지 커버
        audio, _ = librosa.load(wav_path, sr=SAMPLE_RATE)

        queued = time.perf_counter()
        with _INFERENCE_SLOTS:
            waited_ms = (time.perf_counter() - queued) * 1000
            started = time.perf_counter()
            _captured.spans = []  # 이전 호출 값이 남지 않게 초기화
            segments = self._transcribe_segments(asr, audio)
            inference_ms = (time.perf_counter() - started) * 1000

        text = " ".join(seg["text"] for seg in segments if seg["text"]).strip()
        speech_ms = sum(seg["end"] - seg["start"] for seg in segments)

        logger.info(
            "SenseVoice STT 완료: 추론 %.0fms (대기 %.0fms) | 오디오 %.1f초, 발화 %.1f초 | 구간 %d개, %d자",
            inference_ms, waited_ms, len(audio) / SAMPLE_RATE, speech_ms / 1000,
            len(segments), len(text),
        )
        return text, {"segments": segments}

    def _transcribe_segments(self, asr, audio) -> list[dict]:
        """SpeechAnalyzer가 읽을 segments를 만든다.

        SpeechAnalyzer는 segments에서 딱 두 가지만 본다:
            발화 시간 = sum(end - start)     <- VAD 구간에서 온다
            전체 텍스트 = 모든 text를 이어붙인 것  <- 통짜 추론에서 온다
        말속도 = 음절 수 / 발화 시간. 둘 다 정확하다.

        발화 구간은 asr.generate 가 내부에서 이미 계산한 것을 _captured 로 주워 쓴다
        (예전엔 VAD 를 한 번 더 돌렸다). 구간별 text는 실제 그 구간의 말이 아니다(전문을
        첫 구간에 몰아둔다) — 위 두 값 말고는 쓰이지 않기 때문이다.
        """
        text = _run_asr(asr, audio)  # 이 안에서 내부 VAD 가 돌며 _captured.spans 를 채운다
        if not text:
            return []

        spans = getattr(_captured, "spans", None) or []
        spans = [(s, e) for s, e in spans if e > s]
        if not spans:
            # 텍스트는 나왔는데 VAD가 발화를 못 찾았다 — 말속도는 포기하고
            # 텍스트 평가와 꼬리질문은 살린다.
            logger.warning("VAD가 발화 구간을 찾지 못했다 — 말속도 점수를 낼 수 없다")
            return [{"text": text, "start": 0, "end": 0}]

        segments = [{"text": text, "start": spans[0][0], "end": spans[0][1]}]
        segments += [{"text": "", "start": s, "end": e} for s, e in spans[1:]]
        return segments


def _run_asr(asr, audio) -> str:
    result = asr.generate(input=audio, fs=SAMPLE_RATE, language="ko", use_itn=True)
    if not result:
        return ""
    return _strip_tags(result[0].get("text"))


_TAG = re.compile(r"<\|[^|]*\|>")
# SenseVoice는 감정·음향 이벤트를 인식한다. FunASR의 rich_transcription_postprocess를
# 쓰면 그것들이 이모지(😊, 👏 ...)로 텍스트에 박힌다. 답변 텍스트는 LLM 평가와
# 음절 수 계산에 그대로 들어가므로 이모지가 섞이면 안 된다. 그래서 직접 지운다.
_EMOJI = re.compile("[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff️]")


def _strip_tags(text: Optional[str]) -> str:
    """<|ko|><|NEUTRAL|><|Speech|> 같은 태그와 이모지를 걷어낸다."""
    if not text:
        return ""
    cleaned = _EMOJI.sub("", _TAG.sub("", text))
    return " ".join(cleaned.split())
