import { useEffect } from 'react';

/**
 * #webcam-video 엘리먼트에 웹캠 미리보기를 붙인다.
 *
 * `active`가 false가 되거나 언마운트되면 트랙을 정지해 카메라를 끈다.
 *
 * getUserMedia가 resolve하기 전에 정리가 시작될 수 있다. 그때 스트림을 그냥
 * 두면 카메라가 영영 켜진 채로 남으므로, cancelled 플래그로 잡아서 즉시 끈다.
 */
export function useWebcamPreview(active: boolean = true) {
    useEffect(() => {
        if (!active) return;

        const video = document.getElementById('webcam-video') as HTMLVideoElement | null;
        if (!video) return;

        let cancelled = false;
        let stream: MediaStream | null = null;

        navigator.mediaDevices
            .getUserMedia({ video: true, audio: false })
            .then((s) => {
                if (cancelled) {
                    s.getTracks().forEach((track) => track.stop());
                    return;
                }
                stream = s;
                video.srcObject = s;
            })
            .catch((err) => console.error('웹캠 접근 실패:', err));

        return () => {
            cancelled = true;
            stream?.getTracks().forEach((track) => track.stop());
            video.srcObject = null;
        };
    }, [active]);
}
