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
    drawVideo,
    getLandmarkers,
    prefetchLandmarkers,
} from "@/lib/postureVision";

// 클라이언트 모드에서 랜드마커를 기다려주는 시간. 이 안에 준비되면 JPEG를 한 장도
// 보내지 않는다 -> 서버가 MediaPipe 인스턴스를 띄울 일이 없다.
// 넘기면 그때부터 JPEG를 보낸다 (분석을 통째로 잃는 것보다는 낫다).
const LANDMARKER_GRACE_MS = 2000;

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
        let loading = false;
        let failed = false; // 클라이언트 경로가 한 번 죽으면 이 질문 동안 다시 시도하지 않는다

        const canvas = createMirrorCanvas(); // 640x480 — 서버의 카메라 행렬과 맞춘다
        const sessionId = getInterviewSessionId();
        const sessionQuery = sessionId ? `&session_id=${sessionId}` : "";
        const wsUrl = getBackendWsUrl("/ws/expression", process.env.NEXT_PUBLIC_EXPRESSION_WS_URL);
        const socket = new WebSocket(`${wsUrl}?question_id=${questionId}${sessionQuery}`);

        const fallbackToServer = (reason: string) => {
            console.warn(`[posture] 서버 경로로 전환: ${reason}`);
            failed = true;
            // 랜드마커는 닫지 않는다. 탭 수명 동안 공유되는 캐시라, 여기서 닫으면
            // 다른 질문에서 다시 수 초를 들여 만들어야 한다.
            landmarkers = null;
        };

        const ensureLandmarkers = () => {
            if (loading || landmarkers || failed) return;
            loading = true;
            getLandmarkers()
                .then((created) => {
                    if (cancelled) return; // 캐시된 인스턴스이므로 닫지 않는다
                    landmarkers = created;
                    console.info(`[posture] 클라이언트 추론 시작 (delegate=${created.delegate})`);
                })
                .catch((e) => fallbackToServer(`랜드마커 초기화 실패: ${e}`));
        };

        const sendLandmarks = () => {
            // 서버는 랜드마크 경로에서 cv2.flip 을 하지 않는다. 여기서 추론한다.
            drawVideo(canvas, video);
            const { face, pose } = detect(landmarkers!, canvas);
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

        const startedAt = Date.now();

        const tick = () => {
            if (video.readyState < 2 || socket.readyState !== WebSocket.OPEN) return;

            // 모드는 벤치마크(약 5초)가 끝나야 정해진다. 준비 시간을 기다리지 않고 답변을
            // 시작하면 소켓이 열릴 때는 아직 미정이다. 그래서 매 프레임 다시 읽는다.
            // 한 번만 읽으면 그 답변 내내 서버 경로에 갇힌다.
            const useClient = !failed && getPostureMode() === "client";
            if (useClient) ensureLandmarkers();

            try {
                if (useClient && landmarkers) {
                    sendLandmarks();
                    return;
                }

                // 클라이언트 모드인데 랜드마커가 아직 준비 안 됐다면 잠깐 기다린다.
                // 여기서 JPEG를 한 장이라도 보내면 서버가 그 연결 전용 MediaPipe
                // 인스턴스(약 100MB)를 띄운다 — 곧 랜드마크로 갈아탈 텐데 낭비다.
                // 모델은 보통 벤치마크 때 이미 캐시에 올라와 있어 몇 프레임이면 준비된다.
                if (useClient && Date.now() - startedAt < LANDMARKER_GRACE_MS) return;

                sendJpeg();
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

        return () => {
            cancelled = true;
            if (interval) clearInterval(interval);
            socket.close();
        };
    }, [isAnswerActive, questionId]);
}
