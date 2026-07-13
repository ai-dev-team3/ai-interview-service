"""음조 점수 — 세미톤 기반으로 재설계한 뒤의 성질을 고정한다.

예전 산식의 결함 (실측으로 확인):
  1) 이상적 범위를 10~20Hz 로 잡았는데 실제 화자는 전부 35~60Hz 였다.
     남 135/137Hz, 여 284/272Hz 화자 8명 전원이 음조 0점을 받고 있었다.
  2) Hz 표준편차는 화자의 기본 음높이를 따라간다. 여성은 남성보다 기본 음높이가
     2배라 같은 억양이라도 Hz std 가 2배로 나온다. 저음 화자가 자동으로 단조로움이 됐다.
  3) '30프레임 창이 하나라도 평탄하면' 그 창의 작은 std 를 반환했다.
     그래서 단조롭게 말한 사람이 더 높은 점수를 받았다 — 산식이 뒤집혀 있었다.
"""
import numpy as np
import pytest

from app.services.feedback.speechfeedback import SpeechFeedbackGenerator
from app.services.speech.speech_analyzer import (
    EXCESSIVE_ST,
    MONOTONE_ST,
    NATURAL_MAX_ST,
    NATURAL_MIN_ST,
    SpeechAnalyzer,
)


def _score(st_std: float) -> int:
    gen = SpeechFeedbackGenerator({}, {"pitch_std": st_std}, [])
    return gen.score_pitch(st_std)


def _tone(st_std: float) -> str:
    gen = SpeechFeedbackGenerator({}, {"pitch_std": st_std}, [])
    return gen.classify_labels()["tone"]


def test_자연스러운_억양이_만점():
    """실측한 화자 8명은 전부 2.8~4.5 세미톤이었다. 만점 구간에 들어와야 한다."""
    for st in (2.8, 3.12, 3.63, 3.97, 3.98, 4.53):
        assert _score(st) == 20, f"{st} 세미톤이 만점이 아니다"


def test_단조로울수록_점수가_낮다():
    """예전에는 반대였다 — 단조로운 사람이 더 높은 점수를 받았다."""
    assert _score(0.5) < _score(1.2) < _score(1.8) < _score(2.5)
    assert _score(MONOTONE_ST) <= 8


def test_과장될수록_점수가_낮다():
    assert _score(5.5) < 20
    assert _score(7.0) < _score(5.5)
    assert _score(9.0) == 0


def test_점수는_0에서_20_사이():
    for st in np.arange(0, 12, 0.1):
        assert 0 <= _score(float(st)) <= 20


def test_라벨():
    assert _tone(1.0) == "단조로움"
    assert _tone(3.5) == "밝음"
    assert _tone(7.0) == "과장됨"


def test_화자의_음높이가_점수를_바꾸지_않는다():
    """같은 억양(비율)이면 목소리가 높든 낮든 같은 점수여야 한다.

    Hz 로 재던 예전 산식이 실패하던 지점이다. 세미톤은 화자의 중앙값 기준이라
    절대 음높이가 상쇄된다.
    """
    # 같은 세미톤 패턴을 남성(120Hz)과 여성(240Hz) 기본 음높이에 얹는다
    pattern = np.array([-3, -1, 0, 1, 3, 0, -2, 2] * 8, dtype=float)

    scores = []
    for base_hz in (120.0, 240.0):
        f0 = base_hz * (2 ** (pattern / 12))
        median = np.median(f0)
        st_std = float(np.std(12 * np.log2(f0 / median)))
        scores.append(_score(st_std))

    assert scores[0] == scores[1], f"음높이만 다른데 점수가 갈렸다: {scores}"

    # Hz 표준편차는 실제로 2배 차이가 난다 (그래서 Hz 기준은 틀렸다)
    hz_stds = [
        float(np.std(base * (2 ** (pattern / 12)))) for base in (120.0, 240.0)
    ]
    assert hz_stds[1] == pytest.approx(hz_stds[0] * 2, rel=0.01)


def test_짧은_음성은_분석하지_않는다(tmp_path, monkeypatch):
    import librosa

    monkeypatch.setattr(librosa, "load", lambda p, sr: (np.zeros(1000, dtype=np.float32), sr))
    monkeypatch.setattr(
        librosa, "pyin", lambda y, fmin, fmax, hop_length: (np.full(5, np.nan), None, None)
    )

    result = SpeechAnalyzer({}).calculate_pitch_variation("x.wav")

    assert result["pitch_std"] == 0.0
    assert "짧아" in result["pitch_feedback"]


def test_경계값들이_뒤집혀있지_않다():
    assert MONOTONE_ST < NATURAL_MIN_ST <= NATURAL_MAX_ST < EXCESSIVE_ST
