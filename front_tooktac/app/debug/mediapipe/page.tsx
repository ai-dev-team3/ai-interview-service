'use client';

/**
 * MediaPipe 브라우저 추론 프로토타입 (측정용, 제품 코드 아님).
 *
 * 확인하려는 것:
 *   1. GPU delegate 가 실제로 붙는가 (실패하면 CPU 폴백)
 *   2. 5fps 기준 프레임당 추론 시간 — 저사양 폴백이 필요한가
 *   3. facialTransformationMatrixes 로 피치를 뽑을 수 있는가 (cv2.solvePnP 대체)
 *   4. pose 랜드마크의 visibility 가 손 등장 판정에 쓸 만한가
 *   5. 서버로 보낼 랜드마크 18개의 페이로드 크기
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
    FaceLandmarker,
    FilesetResolver,
    PoseLandmarker,
    type NormalizedLandmark,
} from '@mediapipe/tasks-vision';

// posture_analyzer.py 가 실제로 읽는 인덱스만 추린 것
const FACE_INDICES = [1, 33, 78, 152, 263, 308, 468, 469, 471, 473, 474, 476];
// PoseLandmark: LEFT_EAR=7, RIGHT_EAR=8, LEFT_SHOULDER=11, RIGHT_SHOULDER=12,
//               LEFT_INDEX=19, RIGHT_INDEX=20
const POSE_INDICES = [7, 8, 11, 12, 19, 20];

const TARGET_FPS = 5;
const WASM_PATH = '/mediapipe/wasm';
// ?delegate=cpu 로 CPU(WASM) 추론 시간을 잴 수 있다. 저사양 기기의 대략적 상한이다.
// ?mirror=0 으로 좌우 반전을 끌 수 있다 (기본 켬 — posture_analyzer.py 의 cv2.flip 재현).
const FACE_MODEL =
    'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
const POSE_MODEL =
    'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

type Report = {
    delegate: string;
    faceMs: number;
    poseMs: number;
    totalMs: number;
    fpsHeadroom: number;
    faceFound: boolean;
    poseFound: boolean;
    hasMatrix: boolean;
    pitchDeg: number | null;
    noseXY: string;
    coordBounds: string;
    visibilitySample: string;
    visibilityMax: string;
    payloadBytes: number;
    binaryBytes: number;
};

/** facialTransformationMatrixes(4x4, column-major)에서 피치를 뽑는다. */
function pitchFromMatrix(data: number[]): number {
    // column-major 4x4 -> 회전 성분 R[row][col] = data[col*4 + row]
    const r21 = data[1 * 4 + 2]; // R[2][1]
    return (Math.asin(Math.max(-1, Math.min(1, -r21))) * 180) / Math.PI;
}

function pick(landmarks: NormalizedLandmark[], indices: number[]) {
    return indices.map((i) => {
        const l = landmarks[i];
        return l ? { x: +l.x.toFixed(4), y: +l.y.toFixed(4), v: +l.visibility.toFixed(3) } : null;
    });
}

export default function MediaPipeProbePage() {
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const faceRef = useRef<FaceLandmarker | null>(null);
    const poseRef = useRef<PoseLandmarker | null>(null);

    const [status, setStatus] = useState('초기화 중...');
    const [report, setReport] = useState<Report | null>(null);
    const [samples, setSamples] = useState<number[]>([]);

    const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    const forcedDelegate = params?.get('delegate')?.toUpperCase() === 'CPU' ? 'CPU' : 'GPU';
    const mirror = params?.get('mirror') !== '0';

    // 한 프레임 값이 아니라 관측된 전체 범위를 누적해야 정규화 여부를 확인할 수 있다
    const bounds = useRef({ minX: 1, maxX: 0, minY: 1, maxY: 0, maxVis: 0 });

    const load = useCallback(async (delegate: 'GPU' | 'CPU') => {
        const fileset = await FilesetResolver.forVisionTasks(WASM_PATH);
        const face = await FaceLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: FACE_MODEL, delegate },
            runningMode: 'VIDEO',
            numFaces: 1,
            outputFacialTransformationMatrixes: true,
        });
        const pose = await PoseLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: POSE_MODEL, delegate },
            runningMode: 'VIDEO',
            numPoses: 1,
        });
        return { face, pose };
    }, []);

    useEffect(() => {
        let cancelled = false;
        let timer: ReturnType<typeof setInterval> | null = null;
        let stream: MediaStream | null = null;
        let usedDelegate = 'GPU';

        (async () => {
            try {
                let models;
                usedDelegate = forcedDelegate;
                try {
                    setStatus(`${forcedDelegate} delegate 로 로드 중...`);
                    models = await load(forcedDelegate);
                } catch (e) {
                    console.warn(`${forcedDelegate} delegate 실패, CPU 로 폴백:`, e);
                    usedDelegate = `CPU (${forcedDelegate} 실패)`;
                    setStatus('CPU delegate 로 로드 중...');
                    models = await load('CPU');
                }
                if (cancelled) return;
                faceRef.current = models.face;
                poseRef.current = models.pose;

                stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                if (cancelled) {
                    stream.getTracks().forEach((t) => t.stop());
                    return;
                }
                const video = videoRef.current!;
                video.srcObject = stream;
                await video.play();

                setStatus(`측정 중 (${TARGET_FPS}fps, delegate=${usedDelegate}, mirror=${mirror})`);

                timer = setInterval(() => {
                    const v = videoRef.current;
                    const f = faceRef.current;
                    const p = poseRef.current;
                    if (!v || !f || !p || v.readyState < 2) return;

                    // posture_analyzer.py:53 의 cv2.flip(frame, 1) 을 재현한다.
                    // 뒤집힌 영상에서는 MediaPipe 가 좌우를 반대로 라벨링하므로,
                    // 좌표만 1-x 하는 것으로는 서버 로직과 맞지 않는다.
                    let source: HTMLVideoElement | HTMLCanvasElement = v;
                    if (mirror) {
                        const canvas = canvasRef.current!;
                        if (canvas.width !== v.videoWidth) {
                            canvas.width = v.videoWidth;
                            canvas.height = v.videoHeight;
                        }
                        const ctx = canvas.getContext('2d')!;
                        ctx.save();
                        ctx.translate(canvas.width, 0);
                        ctx.scale(-1, 1);
                        ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
                        ctx.restore();
                        source = canvas;
                    }

                    const ts = performance.now();
                    const t0 = performance.now();
                    const faceResult = f.detectForVideo(source, ts);
                    const t1 = performance.now();
                    const poseResult = p.detectForVideo(source, ts);
                    const t2 = performance.now();

                    const faceLm = faceResult.faceLandmarks?.[0];
                    const poseLm = poseResult.landmarks?.[0];
                    const matrix = faceResult.facialTransformationMatrixes?.[0];

                    const payload = {
                        face: faceLm ? pick(faceLm, FACE_INDICES) : null,
                        pose: poseLm ? pick(poseLm, POSE_INDICES) : null,
                    };
                    const jsonBytes = new TextEncoder().encode(JSON.stringify(payload)).length;
                    // 실제로는 Float32Array 로 보낸다: 18개 × (x, y, visibility) × 4바이트
                    const binaryBytes = (FACE_INDICES.length + POSE_INDICES.length) * 3 * 4;
                    const payloadBytes = jsonBytes;

                    // 실제로 서버로 보낼 18개 랜드마크의 좌표 범위를 누적한다
                    const b = bounds.current;
                    const track = (lms: NormalizedLandmark[] | undefined, idx: number[]) => {
                        if (!lms) return;
                        for (const i of idx) {
                            const l = lms[i];
                            if (!l) continue;
                            if (l.x < b.minX) b.minX = l.x;
                            if (l.x > b.maxX) b.maxX = l.x;
                            if (l.y < b.minY) b.minY = l.y;
                            if (l.y > b.maxY) b.maxY = l.y;
                        }
                    };
                    track(faceLm, FACE_INDICES);
                    track(poseLm, POSE_INDICES);
                    if (poseLm) {
                        const vis = Math.max(poseLm[19]?.visibility ?? 0, poseLm[20]?.visibility ?? 0);
                        if (vis > b.maxVis) b.maxVis = vis;
                    }

                    const totalMs = t2 - t0;
                    setSamples((prev) => [...prev.slice(-29), totalMs]);
                    setReport({
                        delegate: usedDelegate,
                        faceMs: +(t1 - t0).toFixed(1),
                        poseMs: +(t2 - t1).toFixed(1),
                        totalMs: +totalMs.toFixed(1),
                        fpsHeadroom: +(1000 / TARGET_FPS / totalMs).toFixed(1),
                        faceFound: !!faceLm,
                        poseFound: !!poseLm,
                        hasMatrix: !!matrix,
                        pitchDeg: matrix ? +pitchFromMatrix(matrix.data).toFixed(1) : null,
                        noseXY: faceLm
                            ? `x=${faceLm[1].x.toFixed(3)} y=${faceLm[1].y.toFixed(3)}`
                            : '-',
                        coordBounds: `x ${b.minX.toFixed(3)}~${b.maxX.toFixed(3)}  y ${b.minY.toFixed(3)}~${b.maxY.toFixed(3)}`,
                        visibilitySample: poseLm
                            ? `LEFT_INDEX=${poseLm[19]?.visibility.toFixed(3)} RIGHT_INDEX=${poseLm[20]?.visibility.toFixed(3)}`
                            : '-',
                        visibilityMax: b.maxVis.toFixed(3),
                        payloadBytes,
                        binaryBytes,
                    });
                }, 1000 / TARGET_FPS);
            } catch (e) {
                console.error(e);
                setStatus(`실패: ${e instanceof Error ? e.message : String(e)}`);
            }
        })();

        return () => {
            cancelled = true;
            if (timer) clearInterval(timer);
            stream?.getTracks().forEach((t) => t.stop());
            faceRef.current?.close();
            poseRef.current?.close();
        };
    }, [load]);

    const avg = samples.length ? samples.reduce((a, b) => a + b, 0) / samples.length : 0;
    const max = samples.length ? Math.max(...samples) : 0;

    return (
        <div className="min-h-screen bg-slate-50 p-8">
            <h1 className="text-2xl font-bold mb-2">MediaPipe 브라우저 추론 프로토타입</h1>
            <p className="text-sm text-slate-600 mb-6">{status}</p>

            <video ref={videoRef} muted playsInline className="w-80 rounded-lg border mb-2" />
            <canvas ref={canvasRef} className="hidden" />
            <p className="text-xs text-slate-500 mb-6">
                ?delegate=cpu 로 CPU 추론 시간 측정 · ?mirror=0 으로 좌우 반전 해제
            </p>

            {report && (
                <div className="grid gap-2 max-w-2xl text-sm font-mono">
                    <Row label="delegate" value={report.delegate} />
                    <Row label="face 추론" value={`${report.faceMs} ms`} />
                    <Row label="pose 추론" value={`${report.poseMs} ms`} />
                    <Row label="합계 (최근)" value={`${report.totalMs} ms`} />
                    <Row label={`합계 (평균/최대, ${samples.length}샘플)`} value={`${avg.toFixed(1)} / ${max.toFixed(1)} ms`} />
                    <Row
                        label={`${TARGET_FPS}fps 여유`}
                        value={`${report.fpsHeadroom}x  (1.0 미만이면 못 따라감)`}
                    />
                    <hr className="my-2" />
                    <Row label="얼굴 감지" value={String(report.faceFound)} />
                    <Row label="포즈 감지" value={String(report.poseFound)} />
                    <Row label="변환 행렬 제공" value={String(report.hasMatrix)} />
                    <Row label="행렬에서 뽑은 피치" value={report.pitchDeg === null ? '-' : `${report.pitchDeg}°`} />
                    <Row label="코끝 좌표 (매 프레임 변함, 정상)" value={report.noseXY} />
                    <Row
                        label="18개 좌표의 누적 범위 (0~1 밖이면 정규화 아님)"
                        value={report.coordBounds}
                    />
                    <Row label="visibility 현재값 (손 내리면 낮음, 정상)" value={report.visibilitySample} />
                    <Row
                        label="visibility 누적 최댓값 (손 들면 0.5 넘어야 함)"
                        value={report.visibilityMax}
                    />
                    <Row label="랜드마크 18개 (JSON)" value={`${report.payloadBytes} bytes/frame`} />
                    <Row label="랜드마크 18개 (Float32 바이너리)" value={`${report.binaryBytes} bytes/frame`} />
                    <Row
                        label="현재 JPEG 방식과 비교"
                        value={`JPEG 약 30~50KB → ${(40000 / report.binaryBytes).toFixed(0)}배 감소`}
                    />
                </div>
            )}
        </div>
    );
}

function Row({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between border-b border-slate-200 py-1">
            <span className="text-slate-500">{label}</span>
            <span className="text-slate-900">{value}</span>
        </div>
    );
}
