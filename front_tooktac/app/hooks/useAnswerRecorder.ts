import { useEffect, useRef } from 'react';

/**
 * 답변을 녹음하고, 끝나면 blob을 넘겨준다.
 *
 * 연습 면접의 useSttSocket과 달리 소켓을 열지 않는다. 실전은 REST로 올리고
 * 서버가 다음 질문을 돌려준다.
 *
 * 오디오만 녹음한다. 서버는 ffmpeg로 wav만 뽑아 쓰고 영상은 버린다.
 * (예전에 영상까지 녹화했다가 90초짜리 vp8이 전송 상한을 넘겨 답변이 통째로 유실됐다.)
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

interface Options {
    /** true가 되면 녹음 시작, false가 되면 멈추고 onComplete를 부른다 */
    active: boolean;
    /** 질문이 바뀌면 새로 녹음한다 */
    questionOrder: number;
    maxMs: number;
    onComplete: (audio: Blob) => void;
}

export function useAnswerRecorder({ active, questionOrder, maxMs, onComplete }: Options) {
    // onComplete가 매 렌더 새 함수여도 녹음이 다시 시작되지 않도록 ref로 둔다.
    const onCompleteRef = useRef(onComplete);
    onCompleteRef.current = onComplete;

    useEffect(() => {
        if (!active) return;

        let cancelled = false;
        let stream: MediaStream | null = null;
        let recorder: MediaRecorder | null = null;
        let timer: ReturnType<typeof setTimeout> | null = null;
        const chunks: Blob[] = [];

        const stop = () => {
            if (recorder && recorder.state !== 'inactive') recorder.stop();
        };

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
                    console.info(`답변 녹음: ${(blob.size / 1024).toFixed(0)} KB`);

                    // 빈 녹음이어도 올린다. 서버가 결과 행을 남겨야 분석 대기 화면이 끝난다.
                    onCompleteRef.current(blob);
                };

                recorder.start();

                // 답변 시간 만료. cleanup에서 반드시 지운다 — 남겨두면 이전 질문의
                // 타이머가 다음 질문 도중에 깨어나 녹음을 끊는다.
                timer = setTimeout(stop, maxMs);
            })
            .catch((err) => console.error('마이크 접근 실패:', err));

        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
            stop();
            stream?.getTracks().forEach((t) => t.stop());
        };
    }, [active, questionOrder, maxMs]);
}
