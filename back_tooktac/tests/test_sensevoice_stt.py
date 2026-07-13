"""SenseVoice STT 어댑터 테스트 — 모델은 띄우지 않는다(GPU/수 GB).

지키려는 계약은 하나다:
    transcribe(wav) -> (text, {"segments": [{text, start, end}, ...]})

SpeechAnalyzer 가 segments 의 start/end(ms) 로 말속도를 계산한다.
이 모양이 깨지면 예외 없이 speed 점수만 0이 된다 — 그래서 테스트로 고정한다.
"""
import pytest

from app.services.stt.sensevoice import SenseVoiceClient, _strip_tags, _to_segments
from app.services.speech.speech_analyzer import SpeechAnalyzer


def test_sentence_info를_segments로_변환한다():
    result = [{
        "sentence_info": [
            {"text": "<|ko|><|NEUTRAL|><|Speech|>안녕하세요", "start": 0, "end": 1500},
            {"text": "<|ko|><|NEUTRAL|><|Speech|>저는 개발자입니다", "start": 1500, "end": 4000},
        ],
    }]

    segments = _to_segments(result)

    assert segments == [
        {"text": "안녕하세요", "start": 0, "end": 1500},
        {"text": "저는 개발자입니다", "start": 1500, "end": 4000},
    ]


def test_말속도_계산이_그대로_동작한다():
    """Clova 대신 넣어도 SpeechAnalyzer 가 같은 방식으로 읽는지 확인."""
    result = [{
        "sentence_info": [
            {"text": "안녕하세요", "start": 0, "end": 2000},      # 2초
            {"text": "반갑습니다", "start": 3000, "end": 5000},   # 2초 (사이 1초 침묵)
        ],
    }]

    speed = SpeechAnalyzer({"segments": _to_segments(result)}).speech_speed_calculate()

    # 침묵은 빠지고 발화 4초만 센다. 음절 10개 -> 150음절/분
    assert speed["total_duration_sec"] == 4.0
    assert speed["syllables_per_min"] == 150.0


def test_sentence_info가_없으면_전체_텍스트라도_건진다():
    """말속도는 못 내지만 텍스트 평가와 꼬리질문은 살아야 한다."""
    segments = _to_segments([{"text": "<|ko|><|NEUTRAL|><|Speech|>안녕하세요"}])

    assert segments == [{"text": "안녕하세요", "start": 0, "end": 0}]


def test_빈_결과는_빈_리스트():
    assert _to_segments([]) == []
    assert _to_segments([{"text": ""}]) == []


def test_태그와_이모지를_제거한다():
    """SenseVoice는 감정·음향 이벤트를 인식한다.

    FunASR의 rich_transcription_postprocess를 쓰면 그것들이 이모지로 텍스트에 박힌다.
    이 텍스트는 그대로 LLM 평가와 음절 수 계산에 들어가므로 이모지가 섞이면 안 된다.
    """
    assert _strip_tags("<|ko|><|HAPPY|><|Speech|><|woitn|>안녕") == "안녕"
    assert _strip_tags("안녕하세요 😊 반갑습니다 👏") == "안녕하세요 반갑습니다"
    assert _strip_tags("") == ""
    assert _strip_tags(None) == ""


def test_transcribe가_텍스트와_segments를_돌려준다(monkeypatch):
    class FakeModel:
        def generate(self, **kwargs):
            assert kwargs["language"] == "ko"
            return [{
                "sentence_info": [
                    {"text": "첫 문장", "start": 0, "end": 1000},
                    {"text": "둘째 문장", "start": 1000, "end": 2000},
                ]
            }]

    monkeypatch.setattr("app.services.stt.sensevoice.get_model", lambda: FakeModel())

    text, raw = SenseVoiceClient().transcribe("dummy.wav")

    assert text == "첫 문장 둘째 문장"
    assert len(raw["segments"]) == 2


def test_동시_추론은_세마포어로_제한된다(monkeypatch):
    """GPU VRAM 은 유한하다. 무제한으로 밀어넣으면 죽는다."""
    import threading

    from app.services.stt import sensevoice

    peak = 0
    running = 0
    lock = threading.Lock()

    class SlowModel:
        def generate(self, **kwargs):
            nonlocal peak, running
            with lock:
                running += 1
                peak = max(peak, running)
            threading.Event().wait(0.05)
            with lock:
                running -= 1
            return [{"text": "응답"}]

    monkeypatch.setattr(sensevoice, "get_model", lambda: SlowModel())
    monkeypatch.setattr(sensevoice, "_INFERENCE_SLOTS", threading.Semaphore(2))

    threads = [threading.Thread(target=lambda: SenseVoiceClient().transcribe("x.wav")) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert peak <= 2, f"동시 추론이 {peak}개까지 올라갔다 — 세마포어가 안 걸렸다"


def test_알_수_없는_stt_타입은_거부한다():
    from app.services.stt.stt_service import STTService

    with pytest.raises(ValueError):
        STTService("whisper")
