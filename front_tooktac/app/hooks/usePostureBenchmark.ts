import { useEffect } from 'react';

import {
    MIN_MEASURED_FRAMES,
    WARMUP_FRAMES,
    decideMode,
    isPostureModeDecided,
    setPostureMode,
} from '@/lib/postureMode';
import { ANALYSIS_INTERVAL_MS } from '@/lib/postureProtocol';
import { createMirrorCanvas, detect, drawMirrored, getLandmarkers } from '@/lib/postureVision';

/**
 * 클라이언트 추론 성능을 재서 면접 전체에 쓸 모드를 정한다.
 *
 * 아이스브레이킹 페이지에서 마운트되자마자 돈다. 소켓도, 서버 전송도 없다.
 * 준비 시간(30초) 안에 끝나므로 사용자가 답변을 얼마나 빨리 끝내든 영향이 없다.
 *
 * 이 구간의 프레임은 어디에도 저장되지 않으므로 점수를 오염시키지 않는다.
 * 실패하면 아무것도 저장하지 않는다 -> getPostureMode() 가 서버 모드를 돌려준다.
 */
export function usePostureBenchmark(enabled: boolean) {
    useEffect(() => {
        if (!enabled || isPostureModeDecided()) return;

        let cancelled = false;
        let interval: ReturnType<typeof setInterval> | null = null;
        const canvas = createMirrorCanvas();
        const samples: number[] = [];
        let frameCount = 0;

        getLandmarkers()
            .then((landmarkers) => {
                if (cancelled) return;

                interval = setInterval(() => {
                    const video = document.getElementById('webcam-video') as HTMLVideoElement | null;
                    if (!video || video.readyState < 2) return;

                    let elapsedMs: number;
                    try {
                        drawMirrored(canvas, video);
                        elapsedMs = detect(landmarkers, canvas, performance.now()).elapsedMs;
                    } catch (e) {
                        console.warn('[posture] 벤치마크 추론 실패 — 서버 모드', e);
                        setPostureMode('server');
                        if (interval) clearInterval(interval);
                        return;
                    }

                    frameCount += 1;
                    if (frameCount <= WARMUP_FRAMES) return; // 초기 프레임은 느리다

                    samples.push(elapsedMs);
                    if (samples.length < MIN_MEASURED_FRAMES) return;

                    const mode = decideMode(samples);
                    setPostureMode(mode);
                    console.info(
                        `[posture] 모드 결정: ${mode} (${samples.length}프레임, delegate=${landmarkers.delegate})`,
                    );
                    if (interval) clearInterval(interval);
                }, ANALYSIS_INTERVAL_MS);
            })
            .catch((e) => {
                if (cancelled) return;
                console.warn('[posture] 랜드마커 초기화 실패 — 서버 모드', e);
                setPostureMode('server');
            });

        return () => {
            cancelled = true;
            if (interval) clearInterval(interval);
        };
    }, [enabled]);
}
