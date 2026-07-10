/**
 * 브라우저에서 얼굴·포즈 랜드마크를 뽑는다.
 *
 * 서버(posture_analyzer.py)가 하던 일을 그대로 가져온 것이므로 입력 조건도 같아야 한다.
 * 특히 좌우 반전: 서버는 cv2.flip(frame, 1) 후 추론했다. 뒤집힌 영상에서는 MediaPipe가
 * 좌우 라벨을 반대로 붙이므로, 좌표만 1-x 해서는 서버 판정과 맞지 않는다.
 * 캔버스로 실제로 뒤집어서 추론한다.
 */
import { FaceLandmarker, FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

import { FRAME_HEIGHT, FRAME_WIDTH } from './postureProtocol';

const WASM_PATH = '/mediapipe/wasm';
const FACE_MODEL =
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
const POSE_MODEL =
    'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

export type Landmarkers = {
    face: FaceLandmarker;
    pose: PoseLandmarker;
    delegate: 'GPU' | 'CPU';
    close: () => void;
};

async function createWith(delegate: 'GPU' | 'CPU'): Promise<Omit<Landmarkers, 'close'>> {
    const fileset = await FilesetResolver.forVisionTasks(WASM_PATH);
    const face = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: FACE_MODEL, delegate },
        runningMode: 'VIDEO',
        numFaces: 1,
    });
    const pose = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: POSE_MODEL, delegate },
        runningMode: 'VIDEO',
        numPoses: 1,
    });
    return { face, pose, delegate };
}

/** GPU를 먼저 시도하고 실패하면 CPU(WASM)로 떨어진다. 둘 다 실패하면 throw. */
async function createLandmarkers(): Promise<Landmarkers> {
    let built: Omit<Landmarkers, 'close'>;
    try {
        built = await createWith('GPU');
    } catch (e) {
        console.warn('[posture] GPU delegate 실패, CPU 로 폴백:', e);
        built = await createWith('CPU');
    }
    return {
        ...built,
        close: () => {
            built.face.close();
            built.pose.close();
        },
    };
}

// 랜드마커 생성은 모델 로드를 포함해 수 초가 걸린다. 질문마다 다시 만들면
// 매 답변 시작 직후 몇 초간 분석이 비어버린다. 탭 수명 동안 한 번만 만든다.
let cached: Promise<Landmarkers> | null = null;

export function getLandmarkers(): Promise<Landmarkers> {
    if (!cached) {
        cached = createLandmarkers().catch((e) => {
            cached = null; // 실패는 캐시하지 않는다 — 다음에 다시 시도할 수 있게
            throw e;
        });
    }
    return cached;
}

/** 준비 시간 동안 미리 불러온다. 실패해도 조용히 넘어간다(모드 결정 때 다시 시도). */
export function prefetchLandmarkers(): void {
    getLandmarkers().catch(() => undefined);
}

/** 서버의 cv2.flip(frame, 1) 을 재현하는 640x480 캔버스 */
export function createMirrorCanvas(): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    canvas.width = FRAME_WIDTH;
    canvas.height = FRAME_HEIGHT;
    return canvas;
}

/** 비디오를 좌우 반전해 캔버스에 그린다. 비율은 무시하고 늘린다(서버 동작과 동일). */
export function drawMirrored(canvas: HTMLCanvasElement, video: HTMLVideoElement): void {
    const ctx = canvas.getContext('2d')!;
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();
}

export type Detection = {
    face: ReturnType<FaceLandmarker['detectForVideo']>['faceLandmarks'][number] | undefined;
    pose: ReturnType<PoseLandmarker['detectForVideo']>['landmarks'][number] | undefined;
    elapsedMs: number;
};

export function detect(
    landmarkers: Landmarkers,
    source: HTMLCanvasElement,
    timestampMs: number,
): Detection {
    const started = performance.now();
    const faceResult = landmarkers.face.detectForVideo(source, timestampMs);
    const poseResult = landmarkers.pose.detectForVideo(source, timestampMs);
    return {
        face: faceResult.faceLandmarks?.[0],
        pose: poseResult.landmarks?.[0],
        elapsedMs: performance.now() - started,
    };
}
