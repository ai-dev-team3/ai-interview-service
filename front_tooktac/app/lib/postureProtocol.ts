/**
 * /ws/expression 의 바이너리 페이로드 형식.
 *
 * 백엔드의 app/services/vision/payload.py 와 짝을 이룬다. 한쪽만 바꾸면 깨진다.
 *
 *   0x01  브라우저가 뽑은 랜드마크 (기본 경로), 220바이트
 *         [0]=0x01 [1]=face_present [2]=pose_present [3]=예약
 *         [4:]     float32 리틀엔디언 54개
 *                  = 얼굴 12점 × (x, y, visibility) + 포즈 6점 × (x, y, visibility)
 *
 *   0x02  JPEG 프레임 (저사양 기기 폴백)
 *         [0]=0x02 [1:] = JPEG 바이트
 */
import type { NormalizedLandmark } from '@mediapipe/tasks-vision';

export const KIND_LANDMARKS = 0x01;
export const KIND_JPEG = 0x02;

/** posture_rules.py 의 FACE_INDICES / POSE_INDICES 와 순서까지 같아야 한다. */
export const FACE_INDICES = [1, 33, 78, 152, 263, 308, 468, 469, 471, 473, 474, 476];
export const POSE_INDICES = [7, 8, 11, 12, 19, 20];

/** 서버가 solvePnP 카메라 행렬을 이 크기로 만든다. 바꾸면 피치가 달라진다. */
export const FRAME_WIDTH = 640;
export const FRAME_HEIGHT = 480;

/** 5fps. 서버 부담이 없으므로 프레임이 많을수록 정면 응시율이 정확해진다. */
export const ANALYSIS_INTERVAL_MS = 200;

const HEADER_BYTES = 4;
const POINT_COUNT = FACE_INDICES.length + POSE_INDICES.length;
export const LANDMARK_PAYLOAD_BYTES = HEADER_BYTES + POINT_COUNT * 3 * 4; // 220

export function encodeLandmarks(
    face: NormalizedLandmark[] | undefined,
    pose: NormalizedLandmark[] | undefined,
): ArrayBuffer {
    const buffer = new ArrayBuffer(LANDMARK_PAYLOAD_BYTES);
    const view = new DataView(buffer);

    view.setUint8(0, KIND_LANDMARKS);
    view.setUint8(1, face ? 1 : 0);
    view.setUint8(2, pose ? 1 : 0);
    view.setUint8(3, 0);

    let offset = HEADER_BYTES;
    const write = (landmarks: NormalizedLandmark[] | undefined, indices: number[]) => {
        for (const i of indices) {
            const l = landmarks?.[i];
            // 리틀엔디언을 명시한다. 서버는 '<f4' 로 읽는다.
            view.setFloat32(offset, l?.x ?? 0, true);
            view.setFloat32(offset + 4, l?.y ?? 0, true);
            view.setFloat32(offset + 8, l?.visibility ?? 0, true);
            offset += 12;
        }
    };
    write(face, FACE_INDICES);
    write(pose, POSE_INDICES);

    return buffer;
}

export function encodeJpeg(jpeg: ArrayBuffer): ArrayBuffer {
    const out = new Uint8Array(1 + jpeg.byteLength);
    out[0] = KIND_JPEG;
    out.set(new Uint8Array(jpeg), 1);
    return out.buffer;
}
