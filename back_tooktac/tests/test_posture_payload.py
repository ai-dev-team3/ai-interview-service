"""/ws/expression 바이너리 페이로드 파싱 테스트.

프론트(lib/postureProtocol.ts)가 만드는 바이트를 그대로 흉내내 검증한다.
한쪽만 바뀌면 조용히 엉뚱한 랜드마크를 읽게 되므로 형식을 여기 고정한다.
"""
import struct

import pytest

from app.services.vision.payload import (
    KIND_JPEG,
    KIND_LANDMARKS,
    LANDMARK_PAYLOAD_BYTES,
    PayloadError,
    parse_landmarks,
    payload_kind,
)
from app.services.vision.posture_rules import FACE_INDICES, POSE_INDICES


def _build(face_present=True, pose_present=True, fill=None):
    """프론트가 보낼 바이트를 구성한다."""
    n = (len(FACE_INDICES) + len(POSE_INDICES)) * 3
    values = fill if fill is not None else [i / 100.0 for i in range(n)]
    return bytes([KIND_LANDMARKS, int(face_present), int(pose_present), 0]) + struct.pack(f"<{n}f", *values)


def test_payload_size_is_220_bytes():
    assert LANDMARK_PAYLOAD_BYTES == 220
    assert len(_build()) == 220


def test_kind_detection():
    assert payload_kind(_build()) == KIND_LANDMARKS
    assert payload_kind(bytes([KIND_JPEG]) + b"\xff\xd8\xff") == KIND_JPEG
    with pytest.raises(PayloadError):
        payload_kind(b"")


def test_parses_face_and_pose_in_declared_order():
    face, pose = parse_landmarks(_build())

    assert set(face) == set(FACE_INDICES)
    assert set(pose) == set(POSE_INDICES)

    # 얼굴이 먼저, 그다음 포즈. 값은 0.00, 0.01, 0.02, ... 순서
    first_face_idx = FACE_INDICES[0]
    assert face[first_face_idx].x == pytest.approx(0.00)
    assert face[first_face_idx].y == pytest.approx(0.01)
    assert face[first_face_idx].visibility == pytest.approx(0.02)

    first_pose_idx = POSE_INDICES[0]
    offset = len(FACE_INDICES) * 3
    assert pose[first_pose_idx].x == pytest.approx(offset / 100.0)


def test_absent_landmarks_become_none():
    face, pose = parse_landmarks(_build(face_present=False))
    assert face is None and pose is not None

    face, pose = parse_landmarks(_build(pose_present=False))
    assert face is not None and pose is None

    face, pose = parse_landmarks(_build(face_present=False, pose_present=False))
    assert face is None and pose is None


def test_rejects_wrong_length():
    with pytest.raises(PayloadError, match="220"):
        parse_landmarks(_build()[:-4])


def test_rejects_nan_and_inf():
    n = (len(FACE_INDICES) + len(POSE_INDICES)) * 3
    bad = [0.5] * n
    bad[0] = float("nan")
    with pytest.raises(PayloadError, match="NaN"):
        parse_landmarks(_build(fill=bad))

    bad[0] = float("inf")
    with pytest.raises(PayloadError, match="NaN"):
        parse_landmarks(_build(fill=bad))


def test_out_of_range_coords_are_accepted():
    """랜드마크가 프레임 밖이면 0~1을 벗어난다. MediaPipe의 정상 동작이다."""
    n = (len(FACE_INDICES) + len(POSE_INDICES)) * 3
    face, _ = parse_landmarks(_build(fill=[-0.2] * n))
    assert face[FACE_INDICES[0]].x == pytest.approx(-0.2)
