// hooks/useSttSocket.ts
import { useEffect, useRef } from "react";
import { getInterviewSessionId } from "@/api/api";
import { getBackendWsUrl } from "@/lib/env";

interface UseSttSocketProps {
    isAnswerActive: boolean;
    questionId: string
    onTranscriptUpdate?: (text: string) => void;
    onFeedbackUpdate?: (feedback: any) => void;
}

const MAX_ANSWER_MS = 90_000;
const MIME_TYPE = "video/webm;codecs=vp8,opus";

export function useSttSocket({ isAnswerActive, questionId, onTranscriptUpdate, onFeedbackUpdate }: UseSttSocketProps) {
    const recorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (!isAnswerActive) return;

        let cancelled = false;
        chunksRef.current = [];

        const stopRecorder = () => {
            // 답변 시간 만료(훅의 타이머)와 페이지의 카운트다운이 둘 다 정지를 시도한다.
            // 이미 멈춘 MediaRecorder에 stop()을 부르면 InvalidStateError가 난다.
            const recorder = recorderRef.current;
            if (recorder && recorder.state !== "inactive") recorder.stop();
        };

        navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(stream => {
            if (cancelled) {
                stream.getTracks().forEach(track => track.stop());
                return;
            }

            const recorder = new MediaRecorder(stream, { mimeType: MIME_TYPE });
            recorderRef.current = recorder;

            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            recorder.onstop = async () => {
                // 마이크·카메라를 놓아준다. 안 하면 다음 질문까지 켜진 채로 남는다.
                stream.getTracks().forEach(track => track.stop());

                const blob = new Blob(chunksRef.current, { type: MIME_TYPE });
                chunksRef.current = [];
                const buffer = await blob.arrayBuffer();

                const sessionId = getInterviewSessionId();
                const sessionQuery = sessionId ? `&session_id=${sessionId}` : "";
                const wsUrl = getBackendWsUrl("/ws/transcript", process.env.NEXT_PUBLIC_STT_WS_URL);

                // 이 소켓은 cleanup에서 닫지 않는다. onstop은 cleanup 직후에 실행되므로
                // 거기서 닫으면 녹음을 보내기도 전에 연결이 끊긴다. 서버가 결과를 보낸 뒤
                // 스스로 닫는다.
                const socket = new WebSocket(`${wsUrl}?question_id=${questionId}${sessionQuery}`);

                socket.onopen = () => {
                    // 빈 녹음이어도 보낸다. 서버가 "빈 오디오"로 기록해야
                    // 프론트 폴러가 멈춘다(안 보내면 결과 행이 없어 무한 로딩).
                    socket.send(buffer);
                };

                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    onTranscriptUpdate?.(data.transcript);
                    onFeedbackUpdate?.(data.feedback);
                };

                socket.onclose = (event) => {
                    if (event.code === 4401) {
                        alert("세션이 만료되었습니다. 다시 로그인해주세요.");
                        window.location.href = "/login";
                    } else if (event.code === 4403) {
                        alert("잘못된 인증 정보입니다. 다시 로그인해주세요.");
                        window.location.href = "/login";
                    } else {
                        console.warn("WebSocket 종료됨:", event.code, event.reason);
                    }
                };
            };

            recorder.start();

            // 자동 종료 (90초 후). cleanup에서 반드시 정리한다 — 남겨두면
            // 이전 질문의 타이머가 다음 질문 도중에 깨어나 녹음을 끊는다.
            timeoutRef.current = setTimeout(stopRecorder, MAX_ANSWER_MS);
        }).catch(err => console.error("마이크/카메라 접근 실패:", err));

        return () => {
            cancelled = true;
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
                timeoutRef.current = null;
            }
            stopRecorder();
        };
    }, [isAnswerActive, questionId]);
}
