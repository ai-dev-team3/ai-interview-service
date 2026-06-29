import { useEffect } from "react";

interface UseExpressionSocketProps {
    isAnswerActive: boolean;
    questionId: string;
    setGazeActive?: (active: boolean) => void;
    setPostureActive?: (active: boolean) => void;
    setHandActive?: (active: boolean) => void;
}

export function useExpressionSocket({ isAnswerActive, questionId, setGazeActive, setPostureActive, setHandActive }: UseExpressionSocketProps) {
    useEffect(() => {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        canvas.width = 640;
        canvas.height = 480;

        let socket: WebSocket;
        let interval: NodeJS.Timeout;

        const video = document.getElementById("webcam-video") as HTMLVideoElement;

        if (isAnswerActive && video) {
            socket = new WebSocket(
                `${process.env.NEXT_PUBLIC_EXPRESSION_WS_URL || "wss://tooktac.shop:10443/api/ws/expression"}?question_id=${questionId}`
            );

            socket.onopen = () => {
                interval = setInterval(() => {
                    if (video.readyState >= 2 && ctx && socket.readyState === WebSocket.OPEN) {
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        canvas.toBlob((blob) => {
                            blob?.arrayBuffer().then((buffer) => {
                                socket.send(buffer);
                            });
                        }, "image/jpeg");
                    }
                }, 300);
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const result = data.expression;

                if (typeof result === 'object' && result !== null) {
                    setGazeActive?.(!result.head || !result.pitch || !result.gaze );
                    setPostureActive?.(!result.shoulder);
                    setHandActive?.(!result.hand);
                } else {
                    console.warn("❌ expression 분석 실패 또는 비정상 응답:", result);
                }
            };

            socket.onclose = (event) => {
                if (event.code === 4401) {
                    alert("세션이 만료되었습니다. 다시 로그인해주세요.");
                    window.location.href = "/login";
                } else if (event.code === 4403) {
                    alert("잘못된 인증입니다. 다시 로그인해주세요.");
                    window.location.href = "/login";
                } else {
                    console.warn("WebSocket 종료:", event.code, event.reason);
                }
            };
        }

        return () => {
            clearInterval(interval);
            socket?.close();
        };
    }, [isAnswerActive, questionId]);
}
