"""서버측 자세 분석.

기본 경로는 브라우저가 랜드마크를 뽑아 보내므로 이 모듈의 MediaPipe는 쓰이지 않는다.
저사양 기기가 프레임(JPEG)을 보내는 폴백 경로에서만 PostureCoreModel을 만든다.

판정 로직은 posture_rules.score_landmarks 한 곳에 있다. 두 경로가 거기서 합류하므로
기기에 따라 점수가 갈리지 않는다.
"""
from typing import Dict, Optional

import cv2
import numpy as np

from app.services.score.scale import clamp_score
from app.services.vision.posture_rules import (
    FACE_INDICES,
    POSE_INDICES,
    Landmark,
    score_landmarks,
)


class PostureCoreModel:
    """MediaPipe로 프레임에서 랜드마크를 뽑는다 (폴백 경로 전용).

    MediaPipe의 solution 객체는 스레드 안전하지 않고 프레임 간 추적 상태를 갖는다.
    따라서 이 인스턴스는 절대 여러 연결이 공유해선 안 되며, 연결마다 하나씩 만든다.

    실측 비용 (연결 1개당, mediapipe 모듈 임포트 52MB는 별도의 1회성 공유분):
      메모리  104MB   <- 폴백 사용자가 늘 때 가장 먼저 터지는 자원
      생성    12ms
      프레임  18ms    (얼굴 미검출 시. 추적이 걸리면 더 싸다)
    close() 하면 전부 반환된다.
    """

    def __init__(self):
        import mediapipe as mp

        self.face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
        self.pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def close(self) -> None:
        self.face_mesh.close()
        self.pose.close()

    def infer_once(self, frame: np.ndarray) -> Dict[str, object]:
        """한 프레임을 받아 판정 결과를 돌려준다."""
        frame = cv2.flip(frame, 1)  # 좌우 반전으로 거울 효과
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # MediaPipe는 RGB 입력을 기대

        face_result = self.face_mesh.process(rgb)
        pose_result = self.pose.process(rgb)

        face = None
        if face_result.multi_face_landmarks:
            lm = face_result.multi_face_landmarks[0].landmark
            face = {i: Landmark(lm[i].x, lm[i].y, 0.0) for i in FACE_INDICES}

        pose = None
        if pose_result.pose_landmarks:
            plm = pose_result.pose_landmarks.landmark
            pose = {i: Landmark(plm[i].x, plm[i].y, plm[i].visibility) for i in POSE_INDICES}

        return score_landmarks(face, pose, w, h)


class PostureSessionState:
    def __init__(self):
        # 이 질문(WebSocket 연결) 동안만 유지할 누적값
        self.total_frames = 0  # 총 프레임 수
        self.center_frames = 0  # 완전 정면 프레임 수
        self.shoulder_warning_count = 0  # 어깨 경고 횟수
        self.hand_warning_count = 0  # 손 경고 횟수
        self.shoulder_prev_state = "CENTER"  # 이전 어깨 상태
        self.hand_prev_state = "NONE"  # 이전 손 상태

    def update(self, step: Dict[str, object]):
        # 프레임별 결과를 받아 누적값 갱신
        self.total_frames += 1  # 프레임 수 증가
        if step["ok_gaze"] and step["ok_pitch"] and step["ok_head"]:
            self.center_frames += 1  # 완전 정면이면 카운트 증가

        # 어깨 경고: CENTER에서 CENTER가 아닌 상태로 변할 때 카운트
        if step["shoulder_dir"] != self.shoulder_prev_state and self.shoulder_prev_state == "CENTER":
            self.shoulder_warning_count += 1  # 경고 증가
        self.shoulder_prev_state = step["shoulder_dir"]  # 이전 상태 갱신

        # 손 경고: NONE에서 VISIBLE로 변할 때 카운트
        if step["hand_dir"] != self.hand_prev_state and self.hand_prev_state == "NONE":
            self.hand_warning_count += 1  # 경고 증가
        self.hand_prev_state = step["hand_dir"]  # 이전 상태 갱신

    def finalize(self) -> Dict[str, int]:
        """누적 결과로 최종 영상 점수를 낸다. 결과는 항상 0~100이다.

        예전 산식은 gaze + shoulder + hand - 100 이었다. gaze 는 0~100, 어깨와 손은
        각각 0~50 이므로 범위가 -100~100 이었다. 실제로 DB 에 -54 점이 저장돼 있었다.
        정면을 거의 못 본 사용자는 음수를 받고, 그게 리포트 평균까지 끌어내렸다.

        지금은 응시(0~100)와 자세(어깨+손, 0~100)를 반반 섞는다.
        """
        gaze_score = (
            int((self.center_frames / self.total_frames) * 100) if self.total_frames > 0 else 0
        )
        shoulder_score = max(0, 50 - 5 * self.shoulder_warning_count)  # 0~50
        hand_score = max(0, 50 - 5 * self.hand_warning_count)          # 0~50
        posture_score = shoulder_score + hand_score                     # 0~100

        video_score = clamp_score(gaze_score * 0.5 + posture_score * 0.5)

        return {
            "gaze_rate_score": gaze_score,
            "shoulder_posture_warning_count": self.shoulder_warning_count,
            "hand_posture_warning_count": self.hand_warning_count,
            "shoulder_hand_score": posture_score,
            "video_score": video_score,
        }


def to_feedback(step: Dict[str, object]) -> Dict[str, bool]:
    """프론트에 보낼 즉시 피드백용 boolean 묶음"""
    return {
        "gaze": step["ok_gaze"],
        "pitch": step["ok_pitch"],
        "head": step["ok_head"],
        "shoulder": step["ok_shoulder"],
        "hand": step["ok_hand"],
    }
