"""SenseVoice STT 어댑터 테스트 — 모델은 띄우지 않는다(GPU/수 GB).

지키려는 계약:
    transcribe(wav) -> (text, {"segments": [{text, start, end}, ...]})

SpeechAnalyzer 는 segments 에서 두 가지만 본다:
    발화 시간   = sum(end - start)      <- VAD 구간
    전체 텍스트 = 모든 text 이어붙이기   <- 통짜 추론
말속도 = 음절 수 / 발화 시간.

실제로 이런 일이 있었다: SenseVoice 는 타임스탬프를 내지 않아(출력이 {key, text} 뿐)
말속도가 예외 없이 0으로 죽었다. 그래서 VAD 를 따로 돌리는 구조가 됐다.
그 구조를 여기서 고정한다.
"""
import numpy as np
import pytest

from app.services.speech.speech_analyzer import SpeechAnalyzer
from app.services.stt import sensevoice
from app.services.stt.sensevoice import SAMPLE_RATE, SenseVoiceClient, _strip_tags


class FakeVad:
    """발화 구간을 ms 단위로 돌려준다 (침묵은 빠져 있다)"""

    def __init__(self, spans):
        self.spans = spans

    def generate(self, input, fs):  # noqa: A002
        return [{"value": [list(s) for s in self.spans]}]


class FakeAsr:
    """구간마다 순서대로 텍스트를 돌려준다"""

    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = []

    def generate(self, input, fs, **kwargs):  # noqa: A002
        self.calls.append(len(input))
        return [{"text": self.texts.pop(0) if self.texts else ""}]


@pytest.fixture
def audio(monkeypatch):
    """10초짜리 가짜 오디오. librosa.load 를 가로챈다."""
    samples = np.zeros(10 * SAMPLE_RATE, dtype=np.float32)
    monkeypatch.setattr("librosa.load", lambda path, sr: (samples, sr))
    return samples


def _use(monkeypatch, vad, asr):
    monkeypatch.setattr(sensevoice, "get_models", lambda: (vad, asr))


def test_텍스트는_통짜로_발화시간은_VAD로(monkeypatch, audio):
    """짧은 조각을 따로 추론하면 SenseVoice 가 띄어쓰기를 깨뜨린다.

    ("그러 한 일 들 을 잘 처리 해낼 수 있 기" — 실측)
    이 텍스트가 그대로 LLM 평가에 들어가므로 통짜로 추론해야 한다.
    """
    vad = FakeVad([(0, 2000), (3000, 5000)])  # 사이 1초는 침묵
    asr = FakeAsr(["<|ko|><|NEUTRAL|><|Speech|>안녕하세요 반갑습니다"])
    _use(monkeypatch, vad, asr)

    text, raw = SenseVoiceClient().transcribe("dummy.wav")

    assert text == "안녕하세요 반갑습니다"
    # ASR 은 오디오 전체로 딱 한 번만 부른다 (10초 = 160000 샘플)
    assert asr.calls == [10 * SAMPLE_RATE]
    # 구간은 VAD 그대로. 텍스트 전문은 첫 구간에 몰아둔다(합계만 쓰이므로).
    assert raw["segments"] == [
        {"text": "안녕하세요 반갑습니다", "start": 0, "end": 2000},
        {"text": "", "start": 3000, "end": 5000},
    ]


def test_말속도가_침묵을_빼고_계산된다(monkeypatch, audio):
    """SpeechAnalyzer 가 Clova 때와 똑같이 읽는지 — 이게 교체의 핵심 조건이다."""
    vad = FakeVad([(0, 2000), (3000, 5000)])
    asr = FakeAsr(["안녕하세요 반갑습니다"])
    _use(monkeypatch, vad, asr)

    _, raw = SenseVoiceClient().transcribe("dummy.wav")
    speed = SpeechAnalyzer(raw).speech_speed_calculate()

    # 침묵 1초는 빠지고 발화 4초만 센다. 음절 10개 -> 150음절/분
    assert speed["total_duration_sec"] == 4.0
    assert speed["syllables_per_min"] == 150.0


def test_VAD가_발화를_못_찾아도_텍스트는_건진다(monkeypatch, audio):
    """말속도는 포기하더라도 텍스트 평가와 꼬리질문은 살아야 한다."""
    vad = FakeVad([])
    asr = FakeAsr(["전체 텍스트"])
    _use(monkeypatch, vad, asr)

    text, raw = SenseVoiceClient().transcribe("dummy.wav")

    assert text == "전체 텍스트"
    assert raw["segments"] == [{"text": "전체 텍스트", "start": 0, "end": 0}]
    assert SpeechAnalyzer(raw).speech_speed_calculate()["syllables_per_min"] == 0.0


def test_무음이면_빈_결과(monkeypatch, audio):
    _use(monkeypatch, FakeVad([]), FakeAsr([""]))

    text, raw = SenseVoiceClient().transcribe("dummy.wav")

    assert text == ""
    assert raw["segments"] == []


def test_태그와_이모지를_제거한다():
    """SenseVoice 는 감정·음향 이벤트를 인식한다.

    FunASR 의 rich_transcription_postprocess 를 쓰면 그것들이 이모지로 텍스트에 박힌다.
    이 텍스트는 그대로 LLM 평가와 음절 수 계산에 들어가므로 이모지가 섞이면 안 된다.
    """
    assert _strip_tags("<|ko|><|HAPPY|><|Speech|><|woitn|>안녕") == "안녕"
    assert _strip_tags("안녕하세요 😊 반갑습니다 👏") == "안녕하세요 반갑습니다"
    assert _strip_tags("") == ""
    assert _strip_tags(None) == ""


def test_동시_추론은_세마포어로_제한된다(monkeypatch, audio):
    """GPU VRAM 은 유한하다. 무제한으로 밀어넣으면 죽는다."""
    import threading

    peak = 0
    running = 0
    lock = threading.Lock()

    class SlowAsr:
        def generate(self, input, fs, **kwargs):  # noqa: A002
            nonlocal peak, running
            with lock:
                running += 1
                peak = max(peak, running)
            threading.Event().wait(0.05)
            with lock:
                running -= 1
            return [{"text": "응답"}]

    _use(monkeypatch, FakeVad([(0, 1000)]), SlowAsr())
    monkeypatch.setattr(sensevoice, "_INFERENCE_SLOTS", threading.Semaphore(2))

    threads = [
        threading.Thread(target=lambda: SenseVoiceClient().transcribe("x.wav"))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert peak <= 2, f"동시 추론이 {peak}개까지 올라갔다 — 세마포어가 안 걸렸다"


def test_알_수_없는_stt_타입은_거부한다():
    from app.services.stt.stt_service import STTService

    with pytest.raises(ValueError):
        STTService("whisper")
