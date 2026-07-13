/**
 * 답변이 끝났는지 판정한다.
 *
 * 실전 면접의 90초는 상한이지 길이가 아니다. 할 말이 30초에 끝난 사람이 60초를
 * 앉아 있어야 하면 답답하다. 그래서 말이 끝나면 자동으로 다음 질문으로 넘어간다.
 *
 * "답변 완료" 버튼은 두지 않는다 — 실제 면접에서 그런 버튼을 누르는 행위가 없다.
 * 대신 되돌릴 수단이 없으므로, 잘못 자르는 쪽이 답답한 쪽보다 훨씬 나쁘다.
 * 판정은 보수적으로 한다.
 *
 * 이 파일에는 오디오 API가 없다. 숫자만 받아 결정한다 — 그래야 테스트할 수 있다.
 */

export const DEFAULT_CONFIG = {
    /** 시작 직후 이 구간의 음량으로 배경 소음 기준선을 잡는다 */
    calibrationMs: 1000,

    /** 기준선 대비 이 배수를 넘으면 발화로 본다 */
    speechFactor: 2.5,

    /** 기준선이 아주 조용할 때의 하한. 이게 없으면 미세한 잡음도 발화가 된다 */
    minSpeechRms: 0.008,

    /** 이 시간이 지나기 전에는 끝내지 않는다. 첫 마디 전 침묵으로 끊기는 것을 막는다 */
    minAnswerMs: 15_000,

    /** 실제로 이만큼은 말했어야 한다. 기침 한 번으로 끝나지 않게 */
    minSpeechMs: 3_000,

    /**
     * 마지막 발화 이후 이만큼 조용하면 끝났다고 본다.
     *
     * 가장 위험한 값이다. 짧으면 생각하느라 멈춘 사람의 말을 자르고,
     * 길면 답답함이 남는다. 버튼이 없어 잘리면 되돌릴 수 없다.
     *
     * 다만 침묵이 쌓이면 화면에 "답변을 마치는 중" 진행 바가 뜬다. 사용자는 잘리기
     * 전에 보고 말을 이어갈 수 있다. 그 예고 덕분에 무작정 길게 잡지 않아도 된다.
     */
    endSilenceMs: 10_000,

    /** 상한 (기존 동작) */
    maxAnswerMs: 90_000,
} as const;

/**
 * "답변을 마치는 중"을 화면에 띄우기 시작하는 지점 (침묵 진행도).
 *
 * 0 부터 띄우면 말하다 잠깐 숨 쉴 때마다 깜빡인다. 어느 정도 쌓인 뒤에 알린다.
 */
export const ENDING_HINT_RATIO = 0.3;

export type AnswerEndConfig = typeof DEFAULT_CONFIG;

export type AnswerState = {
    /** 답변 시작 후 흐른 시간 */
    elapsedMs: number;
    /** 배경 소음 기준선 (보정 중이면 null) */
    noiseFloor: number | null;
    /** 발화로 판정된 시간의 누적 */
    speechMs: number;
    /** 마지막으로 발화가 감지된 시각 (없으면 null) */
    lastSpeechAtMs: number | null;
};

export type EndReason = 'silence' | 'timeout';

/** 지금 프레임의 음량이 발화인가 */
export function isSpeech(
    rms: number,
    noiseFloor: number | null,
    config: AnswerEndConfig = DEFAULT_CONFIG,
): boolean {
    if (noiseFloor === null) return false; // 아직 기준선을 못 잡았다
    const threshold = Math.max(noiseFloor * config.speechFactor, config.minSpeechRms);
    return rms >= threshold;
}

/** 지금 침묵이 얼마나 이어졌나 (발화가 한 번도 없었으면 0) */
export function silenceMs(state: AnswerState): number {
    if (state.lastSpeechAtMs === null) return 0;
    return Math.max(0, state.elapsedMs - state.lastSpeechAtMs);
}

/**
 * 답변을 끝낼 것인가. 끝내면 이유를, 아니면 null.
 *
 * 무음 종료는 세 조건을 '모두' 만족해야 한다. 하나라도 빠지면 끝내지 않는다.
 */
export function decideEnd(
    state: AnswerState,
    config: AnswerEndConfig = DEFAULT_CONFIG,
): EndReason | null {
    if (state.elapsedMs >= config.maxAnswerMs) return 'timeout';

    if (state.elapsedMs < config.minAnswerMs) return null;
    if (state.speechMs < config.minSpeechMs) return null;
    if (silenceMs(state) < config.endSilenceMs) return null;

    return 'silence';
}

/**
 * 사용자에게 "곧 끝난다"를 보여줄 시점.
 *
 * 아무 예고 없이 화면이 넘어가면 잘렸다고 느낀다. 종료 조건 중 침묵만 남았을 때
 * 그 진행도를 0~1로 돌려준다. 종료할 수 없는 상태면 0.
 */
export function endingProgress(
    state: AnswerState,
    config: AnswerEndConfig = DEFAULT_CONFIG,
): number {
    if (state.elapsedMs < config.minAnswerMs) return 0;
    if (state.speechMs < config.minSpeechMs) return 0;

    const silent = silenceMs(state);
    if (silent <= 0) return 0;
    return Math.min(1, silent / config.endSilenceMs);
}
