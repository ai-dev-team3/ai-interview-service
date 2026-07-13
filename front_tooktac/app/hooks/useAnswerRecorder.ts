import { useEffect, useRef, useState } from 'react';

import {
    DEFAULT_CONFIG,
    type AnswerState,
    type EndReason,
    decideEnd,
    endingProgress,
    isSpeech,
} from '@/lib/answerEnd';

/**
 * 답변을 녹음하고, 끝나면 blob을 넘겨준다.
 *
 * 답변은 두 가지로 끝난다.
 *   무음   말이 끝나고 침묵이 이어지면 자동으로 끝낸다
 *   상한   90초
 *
 * 90초는 상한이지 길이가 아니다. 할 말이 30초에 끝난 사람을 60초 동안 앉혀두면
 * 답답하다. "답변 완료" 버튼은 두지 않는다 — 실제 면접에 그런 버튼은 없다.
 * 대신 잘못 자르면 되돌릴 수 없으므로 판정은 보수적으로 한다 (lib/answerEnd.ts).
 *
 * 소켓은 열지 않는다. 실전은 REST 로 올리고 서버가 다음 질문을 돌려준다.
 * 오디오만 녹음한다 — 서버는 wav 만 뽑아 쓰고 영상은 버린다.
 */
const AUDIO_MIME_TYPES = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
];

function pickMimeType(): string | undefined {
    if (typeof MediaRecorder === 'undefined') return undefined;
    return AUDIO_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

/** 이 프레임의 음량 (0~1 근처) */
function rmsOf(buffer: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) sum += buffer[i] * buffer[i];
    return Math.sqrt(sum / buffer.length);
}

interface Options {
    active: boolean;
    /** 질문이 바뀌면 새로 녹음한다 */
    questionOrder: number;
    onComplete: (audio: Blob, reason: EndReason) => void;
}

export function useAnswerRecorder({ active, questionOrder, onComplete }: Options) {
    // onComplete 가 매 렌더 새 함수여도 녹음이 다시 시작되지 않도록 ref 로 둔다.
    const onCompleteRef = useRef(onComplete);
    onCompleteRef.current = onComplete;

    /** 화면에 "답변을 마치는 중"을 보여주기 위한 0~1 진행도 */
    const [ending, setEnding] = useState(0);
    /** 남은 답변 시간(초). 상한까지 */
    const [remainingSec, setRemainingSec] = useState(DEFAULT_CONFIG.maxAnswerMs / 1000);

    useEffect(() => {
        if (!active) {
            setEnding(0);
            setRemainingSec(DEFAULT_CONFIG.maxAnswerMs / 1000);
            return;
        }

        let cancelled = false;
        let stream: MediaStream | null = null;
        let recorder: MediaRecorder | null = null;
        let audioCtx: AudioContext | null = null;
        let raf = 0;
        const chunks: Blob[] = [];

        const config = DEFAULT_CONFIG;
        const startedAt = performance.now();

        // 배경 소음 기준선을 매번 다시 잰다. 고정 임계값을 쓰면 조용한 방과
        // 시끄러운 방에서 전혀 다르게 동작한다.
        const calibration: number[] = [];
        const answer: AnswerState = {
            elapsedMs: 0,
            noiseFloor: null,
            speechMs: 0,
            lastSpeechAtMs: null,
        };

        let lastFrameAt = startedAt;
        let ended = false;

        const stop = (reason: EndReason) => {
            if (ended) return;
            ended = true;
            endReason = reason;
            if (recorder && recorder.state !== 'inactive') recorder.stop();
        };

        let endReason: EndReason = 'timeout';

        navigator.mediaDevices
            .getUserMedia({ audio: true })
            .then((s) => {
                if (cancelled) {
                    s.getTracks().forEach((t) => t.stop());
                    return;
                }
                stream = s;

                const mimeType = pickMimeType();
                recorder = new MediaRecorder(s, mimeType ? { mimeType } : undefined);

                recorder.ondataavailable = (e) => {
                    if (e.data.size > 0) chunks.push(e.data);
                };

                recorder.onstop = () => {
                    // 마이크를 놓아준다. 안 하면 면접 내내 켜진 채로 남는다.
                    s.getTracks().forEach((t) => t.stop());

                    const blob = new Blob(chunks, { type: recorder!.mimeType });
                    console.info(
                        `[answer] 녹음 종료: ${(answer.elapsedMs / 1000).toFixed(1)}초, ` +
                            `발화 ${(answer.speechMs / 1000).toFixed(1)}초, ` +
                            `${(blob.size / 1024).toFixed(0)} KB, 사유=${endReason}`,
                    );

                    // 빈 녹음이어도 올린다. 서버가 결과 행을 남겨야 분석 대기 화면이 끝난다.
                    onCompleteRef.current(blob, endReason);
                };

                recorder.start();

                // --- 음량 관측 ---
                audioCtx = new AudioContext();
                const analyser = audioCtx.createAnalyser();
                analyser.fftSize = 1024;
                audioCtx.createMediaStreamSource(s).connect(analyser);
                const buffer = new Float32Array(analyser.fftSize);

                const tick = () => {
                    if (cancelled || ended) return;

                    const now = performance.now();
                    const frameMs = now - lastFrameAt;
                    lastFrameAt = now;
                    answer.elapsedMs = now - startedAt;

                    analyser.getFloatTimeDomainData(buffer);
                    const rms = rmsOf(buffer);

                    if (answer.elapsedMs < config.calibrationMs) {
                        calibration.push(rms);
                    } else if (answer.noiseFloor === null) {
                        // 보정 구간의 중앙값. 평균은 기침 한 번에 흔들린다.
                        const sorted = [...calibration].sort((a, b) => a - b);
                        answer.noiseFloor = sorted[Math.floor(sorted.length / 2)] ?? 0;
                        console.info(
                            `[answer] 배경 소음 기준선 ${answer.noiseFloor.toFixed(4)}`,
                        );
                    }

                    if (isSpeech(rms, answer.noiseFloor, config)) {
                        answer.speechMs += frameMs;
                        answer.lastSpeechAtMs = answer.elapsedMs;
                    }

                    setEnding(endingProgress(answer, config));
                    setRemainingSec(
                        Math.max(0, Math.ceil((config.maxAnswerMs - answer.elapsedMs) / 1000)),
                    );

                    const reason = decideEnd(answer, config);
                    if (reason) {
                        stop(reason);
                        return;
                    }

                    raf = requestAnimationFrame(tick);
                };

                raf = requestAnimationFrame(tick);
            })
            .catch((err) => console.error('마이크 접근 실패:', err));

        return () => {
            cancelled = true;
            cancelAnimationFrame(raf);
            if (recorder && recorder.state !== 'inactive') recorder.stop();
            stream?.getTracks().forEach((t) => t.stop());
            audioCtx?.close().catch(() => undefined);
        };
    }, [active, questionOrder]);

    return { ending, remainingSec };
}
