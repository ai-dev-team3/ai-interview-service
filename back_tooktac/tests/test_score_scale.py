"""모든 점수는 0~100 이다.

실제 DB 에서 발견된 것 (수정 전):
    video_evaluation_result.final_video_score   -54 ~ 88
    report_improvement.score                     86 ~ 689
    detail.video.shoulder_posture.score        -310
    문항 final_score                             -5.6

원인은 세 가지였다.
  1) 영상 점수 산식이 gaze + shoulder + hand - 100 이라 범위가 -100~100 이었다.
  2) 자세 점수가 100 - 경고수*10 이라 경고가 많으면 음수로 내려갔다.
  3) 강점/개선점 점수는 LLM 이 자유롭게 뱉는데 검증이 없었다.
"""
import pytest

from app.services.feedback.speechfeedback import SpeechFeedbackGenerator
from app.services.report.gemini_advisor import _clamp_scores
from app.services.score.scale import clamp_score, from_ten_point, from_unit
from app.services.score.scoring import QuestionTypeWeights
from app.services.vision.posture_analyzer import PostureSessionState


def test_clamp_score():
    assert clamp_score(-54) == 0
    assert clamp_score(689) == 100
    assert clamp_score(73.4) == 73
    assert clamp_score(None) == 0
    assert clamp_score("이상한 값") == 0


def test_스케일_변환():
    assert from_unit(0.0) == 0
    assert from_unit(0.6053) == 61
    assert from_unit(1.0) == 100

    # LLM 척도는 1이 최하, 10이 최고다
    assert from_ten_point(1) == 0
    assert from_ten_point(10) == 100
    assert from_ten_point(5.5) == 50


def test_영상_점수는_음수가_되지_않는다():
    """예전 산식은 gaze + shoulder + hand - 100 이라 정면을 못 보면 음수였다."""
    state = PostureSessionState()

    # 최악: 100프레임 내내 시선이 벗어나고, 어깨·손 경고가 쏟아진다
    for i in range(100):
        state.update({
            "ok_gaze": False, "ok_pitch": False, "ok_head": False,
            "ok_shoulder": False, "ok_hand": False,
            "shoulder_dir": "LEFT UP" if i % 2 else "CENTER",
            "hand_dir": "VISIBLE" if i % 2 else "NONE",
        })

    result = state.finalize()

    assert result["video_score"] >= 0, "영상 점수가 음수다"
    assert result["video_score"] <= 100
    assert 0 <= result["shoulder_hand_score"] <= 100


def test_영상_점수_만점():
    state = PostureSessionState()
    for _ in range(50):
        state.update({
            "ok_gaze": True, "ok_pitch": True, "ok_head": True,
            "ok_shoulder": True, "ok_hand": True,
            "shoulder_dir": "CENTER", "hand_dir": "NONE",
        })

    assert state.finalize()["video_score"] == 100


def test_문항_점수는_0에서_100_사이():
    for video in (-100, -20, 0, 50, 100, 200):
        score = QuestionTypeWeights.calculate_weighted_score({
            "type": "기술형",
            "detailAnalysis": {
                "text": {"score": 80},
                "voice": {"score": 60},
                "video": {"score": video},
            },
        })
        assert 0 <= score <= 100, f"video={video} 일 때 문항 점수가 {score}"


def test_LLM이_뱉은_점수를_자른다():
    """실제로 689 가 DB 에 저장돼 있었다."""
    result = _clamp_scores([
        {"title": "강점", "score": 689},
        {"title": "강점", "score": -5},
        {"title": "강점", "score": 91},
    ])

    assert [item["score"] for item in result] == [100, 0, 91]


def test_LLM_응답이_망가져도_죽지_않는다():
    assert _clamp_scores(None) == []
    assert _clamp_scores("아무 말") == []
    assert _clamp_scores([{"title": "점수 없음"}]) == [{"title": "점수 없음", "score": 0}]


@pytest.mark.parametrize("spm", [0, 300, 2000])
@pytest.mark.parametrize("fillers", [0, 50])
@pytest.mark.parametrize("st_std", [0.0, 3.5, 20.0])
def test_음성_점수도_0에서_100(spm, fillers, st_std):
    gen = SpeechFeedbackGenerator(
        {"syllables_per_min": spm},
        {"pitch_std": st_std, "pitch_feedback": ""},
        [("음", i) for i in range(fillers)],
    )
    feedback = gen.generate_feedback()

    assert 0 <= feedback["total_score"] <= 100
    for name, score in feedback["score_detail"].items():
        assert score >= 0, f"{name} 점수가 음수"
