import { useEffect } from "react";
import { getInterviewSessionId } from "@/api/api";
import { getBackendWsUrl } from "@/lib/env";
import { getPostureMode } from "@/lib/postureMode";
import {
    ANALYSIS_INTERVAL_MS,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    encodeJpeg,
    encodeLandmarks,
} from "@/lib/postureProtocol";
import {
    type Landmarkers,
    createMirrorCanvas,
    detect,
    drawMirrored,
    getLandmarkers,
    prefetchLandmarkers,
} from "@/lib/postureVision";

interface UseExpressionSocketProps {
    isAnswerActive: boolean;
    questionId: string;
    setGazeActive?: (active: boolean) => void;
    setPostureActive?: (active: boolean) => void;
    setHandActive?: (active: boolean) => void;
}

export function useExpressionSocket({
    isAnswerActive,
    questionId,
    setGazeActive,
    setPostureActive,
    setHandActive,
}: UseExpressionSocketProps) {
    // 준비 시간(30초) 동안 모델을 미리 올린다. 답변이 시작되자마자 분석이 돌게 한다.
    useEffect(() => {
        if (getPostureMode() === "client") prefetchLandmarkers();
    }, []);

    useEffect(() => {
        const video = document.getElementById("webcam-video") as HTMLVideoElement | null;
        if (!isAnswerActive || !video) return;

        let cancelled = false;
        let interval: ReturnType<typeof setInterval> | null = null;
        let landmarkers: Landmarkers | null = null;

        let useClient = getPostureMode() === "client";

        const canvas = createMirrorCanvas(); // 640x480 — 서버의 카메라 행렬과 맞춘다
        const sessionId = getInterviewSessionId();
        const sessionQuery = sessionId ? `&session_id=${sessionId}` : "";
        const wsUrl = getBackendWsUrl("/ws/expression", process.env.NEXT_PUBLIC_EXPRESSION_WS_URL);
        const socket = new WebSocket(`${wsUrl}?question_id=${questionId}${sessionQuery}`);

        const fallbackToServer = (reason: string) => {
            console.warn(`[posture] 서버 경로로 전환: ${reason}`);
            useClient = false;
            // 랜드마커는 닫지 않는다. 탭 수명 동안 공유되는 캐시라, 여기서 닫으면
            // 다른 질문에서 다시 수 초를 들여 만들어야 한다.
            landmarkers = null;
        };

        const sendLandmarks = () => {
            // 서버는 랜드마크 경로에서 cv2.flip 을 하지 않는다. 여기서 뒤집어 추론한다.
            drawMirrored(canvas, video);
            const { face, pose } = detect(landmarkers!, canvas, performance.now());
            socket.send(encodeLandmarks(face, pose));
        };

        const sendJpeg = () => {
            // 서버가 cv2.flip 으로 뒤집는다. 여기서는 원본 그대로 보낸다.
            const ctx = canvas.getContext("2d")!;
            ctx.drawImage(video, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
            canvas.toBlob((blob) => {
                if (!blob || socket.readyState !== WebSocket.OPEN) return;
                blob.arrayBuffer().then((buffer) => socket.send(encodeJpeg(buffer)));
            }, "image/jpeg");
        };

        const tick = () => {
            if (video.readyState < 2 || socket.readyState !== WebSocket.OPEN) return;
            try {
                // 클라이언트 모드라도 랜드마커가 아직 없으면 JPEG를 보낸다.
                // 모델 로딩(수 초) 동안 프레임을 버리면 그만큼 분석이 유실된다.
                if (useClient && landmarkers) sendLandmarks();
                else sendJpeg();
            } catch (e) {
                fallbackToServer(`추론 실패: ${e}`);
            }
        };

        socket.onopen = () => {
            interval = setInterval(tick, ANALYSIS_INTERVAL_MS);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const result = data.expression;

            if (typeof result === "object" && result !== null) {
                setGazeActive?.(!result.head || !result.pitch || !result.gaze);
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

        if (useClient) {
            getLandmarkers()
                .then((created) => {
                    if (cancelled) return; // 캐시된 인스턴스이므로 닫지 않는다
                    landmarkers = created;
                    console.info(`[posture] 클라이언트 추론 시작 (delegate=${created.delegate})`);
                })
                .catch((e) => fallbackToServer(`랜드마커 초기화 실패: ${e}`));
        }

        return () => {
            cancelled = true;
            if (interval) clearInterval(interval);
            socket.close();
        };
    }, [isAnswerActive, questionId]);
}
