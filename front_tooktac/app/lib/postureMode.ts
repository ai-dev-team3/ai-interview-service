/**
 * 자세 분석을 브라우저에서 할지 서버에서 할지 결정한다.
 *
 * 아이스브레이킹 답변 중에 재는 이유:
 *   - 그 구간의 영상 결과는 저장되지 않는다(question_order=0 은 질문 행이 없다).
 *     따라서 벤치마크 프레임이 점수를 오염시키지 않는다.
 *   - 사용자가 이미 카메라 앞에 앉아 있어 실제 조명·얼굴로 잰다.
 *   - 5초(워밍업 5 + 측정 20 = 25프레임 × 200ms)면 준비 시간(30초) 안에 여유롭게 끝난다.
 *
 * 결정은 면접 시작 전에 끝나고 sessionStorage 에 남는다.
 * 아이스브레이킹을 건너뛰거나 새로고침으로 값을 잃으면 서버 모드로 폴백한다.
 */
export type PostureMode = 'client' | 'server';

const MODE_KEY = 'posture_mode';

export const WARMUP_FRAMES = 5;
/** 워밍업 5 + 측정 20 = 25프레임 × 200ms = 5초. */
export const MIN_MEASURED_FRAMES = 20;
/** 5fps 예산 200ms 의 60%. 40% 여유를 남긴다. */
export const P95_THRESHOLD_MS = 120;

export function percentile(values: number[], p: number): number {
    if (values.length === 0) return Infinity;
    const sorted = [...values].sort((a, b) => a - b);
    // 최근접 순위법: 20개 표본의 p95 는 19번째(0-based 18)
    const rank = Math.ceil((p / 100) * sorted.length);
    return sorted[Math.min(sorted.length - 1, Math.max(0, rank - 1))];
}

export function decideMode(measuredMs: number[]): PostureMode {
    if (measuredMs.length < MIN_MEASURED_FRAMES) return 'server';
    return percentile(measuredMs, 95) <= P95_THRESHOLD_MS ? 'client' : 'server';
}

/** 저장된 모드. 없으면 서버 모드(안전한 쪽). */
export function getPostureMode(): PostureMode {
    if (typeof window === 'undefined') return 'server';
    return sessionStorage.getItem(MODE_KEY) === 'client' ? 'client' : 'server';
}

export function setPostureMode(mode: PostureMode): void {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(MODE_KEY, mode);
}

export function isPostureModeDecided(): boolean {
    if (typeof window === 'undefined') return false;
    return sessionStorage.getItem(MODE_KEY) !== null;
}
