"""자세 판정 로직 — 프레임도 MediaPipe도 모른다.

랜드마크가 어디서 왔든(브라우저 추론 / 서버 추론) 이 한 곳에서 판정한다.
경로가 둘이어도 채점은 한 벌이어야 기기에 따라 점수가 갈리지 않는다.

임계치와 계산식은 기존 posture_analyzer.PostureCoreModel.infer_once 에서
그대로 옮겨온 것이다. 값을 바꾸면 점수가 달라진다.
"""
from typing import Dict, Mapping, NamedTuple, Optional

import cv2
import numpy as np


class Landmark(NamedTuple):
    x: float  # 정규화 좌표 (프레임 밖이면 0~1을 벗어날 수 있다)
    y: float
    visibility: float


# 프론트가 캔버스를 640x480으로 늘려 그린 뒤 추론하므로 서버도 같은 크기를 가정한다.
# solvePnP의 카메라 행렬(focal_length = w)이 이 값에 의존하므로 바꾸면 피치가 달라진다.
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 얼굴 랜드마크 (FaceMesh, refine_landmarks=True 기준)
LEFT_EYE_OUTER = 33
LEFT_IRIS_LEFT = 471
LEFT_IRIS_RIGHT = 469
LEFT_EYE_CENTER = 468
RIGHT_EYE_OUTER = 263
RIGHT_IRIS_LEFT = 476
RIGHT_IRIS_RIGHT = 474
RIGHT_EYE_CENTER = 473
PNP_FACE_INDICES = (1, 152, 33, 263, 78, 308)  # 코끝, 턱, 좌우 눈 구석, 좌우 입꼬리

# 포즈 랜드마크 (PoseLandmark enum 값)
LEFT_EAR = 7
RIGHT_EAR = 8
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_INDEX = 19
RIGHT_INDEX = 20

# 클라이언트가 전송하는 랜드마크 인덱스 (순서가 곧 바이너리 페이로드 순서다)
FACE_INDICES = (1, 33, 78, 152, 263, 308, 468, 469, 471, 473, 474, 476)
POSE_INDICES = (7, 8, 11, 12, 19, 20)

# solvePnP용 3D 모델 포인트 (고정값)
_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),        # 코 끝
    (0.0, -63.6, -12.5),    # 턱
    (-43.3, 32.7, -26.0),   # 왼쪽 눈 구석
    (43.3, 32.7, -26.0),    # 오른쪽 눈 구석
    (-28.9, -28.9, -24.1),  # 왼쪽 입꼬리
    (28.9, -28.9, -24.1),   # 오른쪽 입꼬리
], dtype=np.float32)


def camera_matrix(w: int, h: int) -> np.ndarray:
    """카메라 내부 파라미터 행렬 (초점거리 = 프레임 폭 가정)"""
    return np.array([
        [w, 0, w / 2],
        [0, w, h / 2],
        [0, 0, 1],
    ], dtype=np.float64)


FaceLandmarks = Mapping[int, Landmark]
PoseLandmarks = Mapping[int, Landmark]


def score_landmarks(
    face: Optional[FaceLandmarks],
    pose: Optional[PoseLandmarks],
    w: int = FRAME_WIDTH,
    h: int = FRAME_HEIGHT,
) -> Dict[str, object]:
    """한 프레임의 랜드마크로 즉시 피드백용 판정 결과를 만든다."""
    gaze_h = "CENTER"
    pitch_dir = "CENTER"
    turn_dir = "CENTER"
    shoulder_dir = "CENTER"
    hand_dir = "NONE"

    if face:
        # 왼쪽 눈의 수평 시선 지표
        left_eye_outer = np.array([face[LEFT_EYE_OUTER].x * w, face[LEFT_EYE_OUTER].y * h])
        left_iris_left = np.array([face[LEFT_IRIS_LEFT].x * w, face[LEFT_IRIS_LEFT].y * h])
        left_iris_right = np.array([face[LEFT_IRIS_RIGHT].x * w, face[LEFT_IRIS_RIGHT].y * h])
        left_ratio = np.linalg.norm(left_iris_left - left_eye_outer) / (
            np.linalg.norm(left_iris_right - left_iris_left) + 1e-6
        )

        # 오른쪽 눈의 수평 시선 지표
        right_eye_outer = np.array([face[RIGHT_EYE_OUTER].x * w, face[RIGHT_EYE_OUTER].y * h])
        right_iris_left = np.array([face[RIGHT_IRIS_LEFT].x * w, face[RIGHT_IRIS_LEFT].y * h])
        right_iris_right = np.array([face[RIGHT_IRIS_RIGHT].x * w, face[RIGHT_IRIS_RIGHT].y * h])
        right_ratio = np.linalg.norm(right_eye_outer - right_iris_right) / (
            np.linalg.norm(right_iris_right - right_iris_left) + 1e-6
        )

        gaze_h = "LEFT" if left_ratio < 0.42 else "RIGHT" if right_ratio < 0.40 else "CENTER"

        # PnP로 피치(상하) 추정
        image_points = np.array(
            [[face[i].x * w, face[i].y * h] for i in PNP_FACE_INDICES], dtype=np.float32
        )
        # 좌표가 퇴화(모든 점이 겹치거나 일직선)하면 solvePnP는 False를 돌려주는 게 아니라
        # cv2.error를 던진다. 랜드마크 경로에서는 좌표가 네트워크로 들어오므로 정상 입력을
        # 가정할 수 없다. 피치를 못 구하면 CENTER로 두고 나머지 판정은 그대로 진행한다.
        try:
            success, rvec, _ = cv2.solvePnP(
                _MODEL_POINTS, image_points, camera_matrix(w, h), np.zeros((4, 1))
            )
        except cv2.error:
            success = False

        if success:
            rmat, _ = cv2.Rodrigues(rvec)
            pitch = np.degrees(np.arcsin(-rmat[2][1]))
            pitch_dir = "UP" if pitch < -12 else "DOWN" if pitch > 9 else "CENTER"

    if pose:
        if face:
            # 좌우 회전: 눈 중심과 귀의 x 거리 비교
            le, re = face[LEFT_EYE_CENTER], face[RIGHT_EYE_CENTER]
            le2e = abs(le.x - pose[LEFT_EAR].x)
            re2e = abs(re.x - pose[RIGHT_EAR].x)
            turn_dir = "LEFT" if le2e > re2e + 0.035 else "RIGHT" if re2e > le2e + 0.055 else "CENTER"

        # 어깨 기울기
        diff = pose[LEFT_SHOULDER].y - pose[RIGHT_SHOULDER].y
        shoulder_dir = "LEFT UP" if diff > 0.04 else "RIGHT UP" if diff < -0.04 else "CENTER"

        # 손 등장 여부
        hand_dir = (
            "VISIBLE"
            if pose[LEFT_INDEX].visibility > 0.5 or pose[RIGHT_INDEX].visibility > 0.5
            else "NONE"
        )

    return {
        "gaze_h": gaze_h,
        "pitch_dir": pitch_dir,
        "turn_dir": turn_dir,
        "shoulder_dir": shoulder_dir,
        "hand_dir": hand_dir,
        "ok_gaze": (gaze_h == "CENTER"),
        "ok_pitch": (pitch_dir == "CENTER"),
        "ok_head": (turn_dir == "CENTER"),
        "ok_shoulder": (shoulder_dir == "CENTER"),
        "ok_hand": (hand_dir == "NONE"),
    }
