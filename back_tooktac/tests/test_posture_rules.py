"""자세 판정 로직 테스트.

핵심은 두 경로의 동치성이다.

  기본 경로 : 브라우저가 뽑은 랜드마크 -> score_landmarks
  폴백 경로 : JPEG -> PostureCoreModel.infer_once -> score_landmarks

같은 랜드마크가 들어가면 같은 결과가 나와야 한다. 그래야 기기에 따라
사용자 점수가 갈리지 않는다.

이 테스트는 리팩터 이전에 먼저 작성해 옛 구현과 대조했고 통과했다.
지금은 폴백 경로가 랜드마크를 올바른 인덱스로 뽑아내는지를 지킨다.
"""
import numpy as np
import pytest

from app.services.vision.posture_rules import (
    FACE_INDICES,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LEFT_INDEX,
    POSE_INDICES,
    RIGHT_INDEX,
    Landmark,
    score_landmarks,
)


class _Lm:
    """MediaPipe 랜드마크를 흉내내는 최소 객체"""

    def __init__(self, x, y, visibility=0.0):
        self.x = x
        self.y = y
        self.z = 0.0
        self.visibility = visibility


def _fake_face(seed: int = 0):
    rng = np.random.default_rng(seed)
    return [_Lm(float(rng.uniform(0.2, 0.8)), float(rng.uniform(0.2, 0.8))) for _ in range(478)]


def _fake_pose(seed: int = 1, hand_visible: bool = False):
    rng = np.random.default_rng(seed)
    lms = [_Lm(float(rng.uniform(0.2, 0.8)), float(rng.uniform(0.2, 0.8)), 0.1) for _ in range(33)]
    if hand_visible:
        lms[LEFT_INDEX].visibility = 0.9
    return lms


def _to_map(lms, indices):
    return {i: Landmark(lms[i].x, lms[i].y, lms[i].visibility) for i in indices}


# ---------- 폴백 경로(프레임)와 기본 경로(랜드마크)의 동치성 ----------

def _legacy_infer(face_lms, pose_lms, w=FRAME_WIDTH, h=FRAME_HEIGHT):
    """PostureCoreModel.infer_once 를 MediaPipe 없이 태운다.

    process()를 가짜로 바꿔 같은 랜드마크를 흘려 넣고, 프레임 경로가
    내놓는 결과를 얻는다.
    """
    from app.services.vision.posture_analyzer import PostureCoreModel

    core = PostureCoreModel()

    class _FaceResult:
        multi_face_landmarks = [type("L", (), {"landmark": face_lms})()] if face_lms else None

    class _PoseResult:
        pose_landmarks = type("L", (), {"landmark": pose_lms})() if pose_lms else None

    core.face_mesh = type("FM", (), {"process": staticmethod(lambda _rgb: _FaceResult())})()
    core.pose = type("P", (), {"process": staticmethod(lambda _rgb: _PoseResult())})()

    frame = np.zeros((h, w, 3), dtype=np.uint8)
    return core.infer_once(frame)


@pytest.mark.parametrize("hand_visible", [False, True])
def test_matches_legacy_implementation(hand_visible):
    face_lms = _fake_face()
    pose_lms = _fake_pose(hand_visible=hand_visible)

    legacy = _legacy_infer(face_lms, pose_lms)
    new = score_landmarks(
        _to_map(face_lms, FACE_INDICES),
        _to_map(pose_lms, POSE_INDICES),
    )

    assert new == legacy


def test_matches_legacy_without_face():
    pose_lms = _fake_pose()
    legacy = _legacy_infer(None, pose_lms)
    new = score_landmarks(None, _to_map(pose_lms, POSE_INDICES))
    assert new == legacy


def test_matches_legacy_without_pose():
    face_lms = _fake_face()
    legacy = _legacy_infer(face_lms, None)
    new = score_landmarks(_to_map(face_lms, FACE_INDICES), None)
    assert new == legacy


# ---------- 판정 규칙 ----------

def test_no_landmarks_is_all_center():
    result = score_landmarks(None, None)
    assert result["gaze_h"] == "CENTER"
    assert result["hand_dir"] == "NONE"
    assert all(result[k] for k in ("ok_gaze", "ok_pitch", "ok_head", "ok_shoulder", "ok_hand"))


def test_hand_visible_above_threshold():
    pose = _to_map(_fake_pose(hand_visible=True), POSE_INDICES)
    assert score_landmarks(None, pose)["hand_dir"] == "VISIBLE"

    pose_down = dict(pose)
    pose_down[LEFT_INDEX] = Landmark(0.5, 0.5, 0.5)   # 임계치는 > 0.5 이므로 경계값은 NONE
    pose_down[RIGHT_INDEX] = Landmark(0.5, 0.5, 0.5)
    assert score_landmarks(None, pose_down)["hand_dir"] == "NONE"


def test_shoulder_tilt_thresholds():
    def pose_with(dy):
        return {
            7: Landmark(0.4, 0.3, 1.0), 8: Landmark(0.6, 0.3, 1.0),
            11: Landmark(0.4, 0.5 + dy, 1.0), 12: Landmark(0.6, 0.5, 1.0),
            19: Landmark(0.4, 0.9, 0.0), 20: Landmark(0.6, 0.9, 0.0),
        }

    assert score_landmarks(None, pose_with(0.05))["shoulder_dir"] == "LEFT UP"
    assert score_landmarks(None, pose_with(-0.05))["shoulder_dir"] == "RIGHT UP"
    assert score_landmarks(None, pose_with(0.0))["shoulder_dir"] == "CENTER"
