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
    coordRange: string;
    visibilitySample: string;
    payloadBytes: number;
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
    const faceRef = useRef<FaceLandmarker | null>(null);
    const poseRef = useRef<PoseLandmarker | null>(null);

    const [status, setStatus] = useState('초기화 중...');
    const [report, setReport] = useState<Report | null>(null);
    const [samples, setSamples] = useState<number[]>([]);

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
                try {
                    setStatus('GPU delegate 로 로드 중...');
                    models = await load('GPU');
                } catch (e) {
                    console.warn('GPU delegate 실패, CPU 로 폴백:', e);
                    usedDelegate = 'CPU (GPU 실패)';
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

                setStatus(`측정 중 (${TARGET_FPS}fps, delegate=${usedDelegate})`);

                timer = setInterval(() => {
                    const v = videoRef.current;
                    const f = faceRef.current;
                    const p = poseRef.current;
                    if (!v || !f || !p || v.readyState < 2) return;

                    const ts = performance.now();
                    const t0 = performance.now();
                    const faceResult = f.detectForVideo(v, ts);
                    const t1 = performance.now();
                    const poseResult = p.detectForVideo(v, ts);
                    const t2 = performance.now();

                    const faceLm = faceResult.faceLandmarks?.[0];
                    const poseLm = poseResult.landmarks?.[0];
                    const matrix = faceResult.facialTransformationMatrixes?.[0];

                    const payload = {
                        face: faceLm ? pick(faceLm, FACE_INDICES) : null,
                        pose: poseLm ? pick(poseLm, POSE_INDICES) : null,
                    };
                    const payloadBytes = new TextEncoder().encode(JSON.stringify(payload)).length;

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
                        coordRange: faceLm
                            ? `x=${faceLm[1].x.toFixed(3)} y=${faceLm[1].y.toFixed(3)} (0~1이면 정규화)`
                            : '-',
                        visibilitySample: poseLm
                            ? `LEFT_INDEX=${poseLm[19]?.visibility.toFixed(3)} RIGHT_INDEX=${poseLm[20]?.visibility.toFixed(3)}`
                            : '-',
                        payloadBytes,
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

            <video ref={videoRef} muted playsInline className="w-80 rounded-lg border mb-6" />

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
                    <Row label="좌표 범위" value={report.coordRange} />
                    <Row label="visibility 샘플" value={report.visibilitySample} />
                    <Row label="랜드마크 18개 페이로드" value={`${report.payloadBytes} bytes/frame`} />
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
