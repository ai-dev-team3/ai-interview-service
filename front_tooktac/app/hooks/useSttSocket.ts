// hooks/useSttSocket.ts
import { useEffect, useRef } from "react";

interface UseSttSocketProps {
    isAnswerActive: boolean;
    questionId: string
    onTranscriptUpdate?: (text: string) => void;
    onFeedbackUpdate?: (feedback: any) => void;
}

export function useSttSocket({ isAnswerActive, questionId, onTranscriptUpdate, onFeedbackUpdate }: UseSttSocketProps) {
    const recorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    useEffect(() => {
        let socket: WebSocket;

        if (isAnswerActive) {
            navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(stream => {
                const mimeType = "video/webm;codecs=vp8,opus";
                const recorder = new MediaRecorder(stream, { mimeType });
                recorderRef.current = recorder;

                recorder.ondataavailable = (e) => {
                    if (e.data.size > 0) {
                        chunksRef.current.push(e.data);
                    }
                };

                recorder.onstop = async () => {
                    const blob = new Blob(chunksRef.current, { type: mimeType });
                    const buffer = await blob.arrayBuffer();

                    socket = new WebSocket(`${process.env.NEXT_PUBLIC_STT_WS_URL || "wss://tooktac.shop:10443/api/ws/transcript"}?question_id=${questionId}`);


                    socket.onopen = () => {
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

                // 자동 종료 (90초 후)
                setTimeout(() => recorder.stop(), 90000);
            });
        }

        return () => {
            recorderRef.current?.stop();
            socket?.close();
        };
    }, [isAnswerActive]);
}
