"""services/speech/answer_pipeline.py — 음성 답변 파이프라인 유닛 테스트.

STT/분석/LLM 컴포넌트는 전부 페이크를 주입해 배선과 실패 처리만 검증한다.
(모듈 임포트가 librosa/torch를 당겨 최초 임포트는 다소 느릴 수 있음)
"""
import asyncio

import pytest

from app.services.speech.answer_pipeline import (
    AnswerAnalysisPipeline,
    AudioConversionError,
    FfmpegNotFoundError,
)


class FakeSTT:
    """stt_type별 동작을 흉내내는 페이크"""
    fail_vito = False

    def __init__(self, stt_type):
        self.stt_type = stt_type

    def transcribe(self, wav_path):
        if self.stt_type == "clova":
            return "클로바 전사 결과", {"segments": [{"text": "클로바 전사 결과", "start": 0, "end": 1000}]}
        if FakeSTT.fail_vito:
            raise RuntimeError("vito 서버 오류")
        return "비토 전사 음 결과", {}


class FakeAnalyzer:
    def __init__(self, raw):
        self.raw = raw

    def speech_speed_calculate(self):
        return {"syllables_per_min": 300.0}

    def calculate_pitch_variation(self, wav_path):
        return {"pitch_feedback": "적절", "pitch_std": 20.0}

    def find_filler_words(self, text):
        return [("음", 2)] if "음" in text else []


class FakeFeedbackGenerator:
    def __init__(self, speed, pitch, fillers):
        self.fillers = fillers

    def generate_feedback(self):
        return {
            "labels": {"speed": "적절"},
            "score_detail": {"speed": 90, "filler": 80, "pitch": 85},
            "total_score": 85,
            "filler_count": len(self.fillers),
        }


class FakeOrchestrator:
    def evaluate_answer(self, question, answer, qtype):
        return {"final_score": 77, "model_answer": "모범답변"}


class FailingOrchestrator:
    def evaluate_answer(self, question, answer, qtype):
        raise RuntimeError("LLM 다운")


def _pipeline(orchestrator=None):
    FakeSTT.fail_vito = False
    return AnswerAnalysisPipeline(
        stt_factory=FakeSTT,
        analyzer_factory=FakeAnalyzer,
        feedback_factory=FakeFeedbackGenerator,
        orchestrator=orchestrator or FakeOrchestrator(),
    )


def test_transcribe_strips_text():
    text, raw = asyncio.run(_pipeline().transcribe("x.wav"))
    assert text == "클로바 전사 결과"
    assert raw["segments"]


def test_analyze_and_evaluate_parallel_success():
    sf, ev = asyncio.run(_pipeline().analyze_and_evaluate(
        "x.wav", {"segments": []}, "답변", "질문", "기술형"
    ))
    assert sf["total_score"] == 85
    assert sf["filler_count"] == 1  # vito 텍스트("음" 포함)에서 간투어 탐지
    assert ev == {"final_score": 77, "model_answer": "모범답변"}


def test_vito_failure_does_not_break_analysis():
    pipeline = _pipeline()
    FakeSTT.fail_vito = True

    sf, ev = asyncio.run(pipeline.analyze_and_evaluate(
        "x.wav", {"segments": []}, "답변", "질문", "기술형"
    ))
    assert sf["filler_count"] == 0  # vito 실패 → 빈 텍스트로 간투어 없음
    assert ev is not None  # 평가는 정상 진행


def test_llm_failure_returns_none_evaluation():
    pipeline = _pipeline(orchestrator=FailingOrchestrator())

    sf, ev = asyncio.run(pipeline.analyze_and_evaluate(
        "x.wav", {"segments": []}, "답변", "질문", "기술형"
    ))
    assert sf["total_score"] == 85  # 음성 분석 결과는 살아있음
    assert ev is None


def test_convert_raises_ffmpeg_not_found(monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("app.services.speech.answer_pipeline.subprocess.run", raise_not_found)

    with pytest.raises(FfmpegNotFoundError):
        asyncio.run(_pipeline().convert_webm_to_wav("a.webm", "a.wav"))


def test_convert_raises_conversion_error(monkeypatch):
    class Proc:
        returncode = 1
        stderr = b"invalid data"

    monkeypatch.setattr(
        "app.services.speech.answer_pipeline.subprocess.run", lambda *a, **k: Proc()
    )

    with pytest.raises(AudioConversionError):
        asyncio.run(_pipeline().convert_webm_to_wav("a.webm", "a.wav"))
