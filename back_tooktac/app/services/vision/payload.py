"""/ws/expression 의 바이너리 페이로드 형식.

첫 바이트가 종류를 가른다.

    0x01  브라우저가 뽑은 랜드마크 (기본 경로)
          [0]=0x01 [1]=face_present [2]=pose_present [3]=예약
          [4:]     float32 리틀엔디언 54개
                   = 얼굴 12점 × (x, y, visibility) + 포즈 6점 × (x, y, visibility)
          총 220바이트

    0x02  JPEG 프레임 (저사양 기기 폴백)
          [0]=0x02 [1:] = JPEG 바이트

프론트의 lib/postureProtocol.ts 와 짝을 이룬다. 한쪽만 바꾸면 깨진다.
"""
from typing import Dict, Optional, Tuple

import numpy as np

from app.services.vision.posture_rules import FACE_INDICES, POSE_INDICES, Landmark

KIND_LANDMARKS = 0x01
KIND_JPEG = 0x02

_HEADER_BYTES = 4
_FLOATS_PER_POINT = 3
_POINT_COUNT = len(FACE_INDICES) + len(POSE_INDICES)
LANDMARK_PAYLOAD_BYTES = _HEADER_BYTES + _POINT_COUNT * _FLOATS_PER_POINT * 4  # 220


class PayloadError(ValueError):
    """페이로드 형식이 맞지 않음"""


def payload_kind(data: bytes) -> int:
    if not data:
        raise PayloadError("빈 페이로드")
    return data[0]


def parse_landmarks(data: bytes) -> Tuple[Optional[Dict[int, Landmark]], Optional[Dict[int, Landmark]]]:
    """0x01 페이로드에서 (얼굴, 포즈) 랜드마크를 꺼낸다. 감지 안 된 쪽은 None."""
    if len(data) != LANDMARK_PAYLOAD_BYTES:
        raise PayloadError(f"랜드마크 페이로드 길이가 {LANDMARK_PAYLOAD_BYTES}가 아님: {len(data)}")

    face_present = bool(data[1])
    pose_present = bool(data[2])

    values = np.frombuffer(data, dtype="<f4", count=_POINT_COUNT * _FLOATS_PER_POINT, offset=_HEADER_BYTES)
    if not np.all(np.isfinite(values)):
        raise PayloadError("랜드마크에 NaN/Inf 가 있음")

    def take(indices, offset):
        return {
            idx: Landmark(
                float(values[offset + n * 3]),
                float(values[offset + n * 3 + 1]),
                float(values[offset + n * 3 + 2]),
            )
            for n, idx in enumerate(indices)
        }

    face = take(FACE_INDICES, 0) if face_present else None
    pose = take(POSE_INDICES, len(FACE_INDICES) * 3) if pose_present else None
    return face, pose
