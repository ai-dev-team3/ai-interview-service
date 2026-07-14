import { describe, expect, it } from 'vitest';

import {
    DEFAULT_CONFIG,
    type AnswerState,
    decideEnd,
    endingProgress,
    isSpeech,
    silenceMs,
} from './answerEnd';

const C = DEFAULT_CONFIG;

function state(over: Partial<AnswerState> = {}): AnswerState {
    return {
        elapsedMs: 0,
        noiseFloor: 0.002,
        speechMs: 0,
        lastSpeechAtMs: null,
        ...over,
    };
}

describe('발화 판정', () => {
    it('기준선을 못 잡았으면 발화가 아니다', () => {
        expect(isSpeech(0.9, null)).toBe(false);
    });

    it('기준선 대비 충분히 크면 발화다', () => {
        expect(isSpeech(0.05, 0.002)).toBe(true);
        expect(isSpeech(0.002, 0.002)).toBe(false);
    });

    it('조용한 방에서도 미세한 잡음을 발화로 보지 않는다', () => {
        // 기준선이 거의 0이면 배수만으로는 아주 작은 소리도 통과해버린다.
        // 그래서 절대 하한(minSpeechRms)이 있다.
        const nearSilent = 0.0001;
        expect(isSpeech(0.001, nearSilent)).toBe(false);
        expect(isSpeech(C.minSpeechRms, nearSilent)).toBe(true);
    });

    it('시끄러운 방에서는 기준선이 올라가 잡음을 걸러낸다', () => {
        const noisy = 0.02;
        expect(isSpeech(0.03, noisy)).toBe(false); // 배경 수준
        expect(isSpeech(0.08, noisy)).toBe(true); // 말소리
    });
});

describe('답변 종료 판정', () => {
    it('말이 끝나면 종료한다', () => {
        const s = state({
            elapsedMs: 30_000,
            speechMs: 20_000,
            lastSpeechAtMs: 30_000 - C.endSilenceMs,
        });
        expect(decideEnd(s)).toBe('silence');
    });

    it('상한에 닿으면 종료한다', () => {
        const s = state({ elapsedMs: C.maxAnswerMs, speechMs: 60_000, lastSpeechAtMs: 89_000 });
        expect(decideEnd(s)).toBe('timeout');
    });

    it('말하다 잠깐 멈춘 것으로는 끝내지 않는다', () => {
        // 이게 가장 중요한 케이스다. 생각하느라 멈춘 사람의 말을 자르면 되돌릴 수 없다.
        // 3초, 8초를 쉬어도 안 잘려야 한다.
        for (const pauseMs of [3_000, 8_000, C.endSilenceMs - 1]) {
            const s = state({
                elapsedMs: 40_000,
                speechMs: 25_000,
                lastSpeechAtMs: 40_000 - pauseMs,
            });
            expect(decideEnd(s), `${pauseMs}ms 멈춤에서 잘렸다`).toBeNull();
        }
    });

    it('말을 이어가면 침묵이 리셋된다', () => {
        // 3초 쉬었다가 다시 말하기 시작 -> lastSpeechAtMs 가 갱신된다
        const paused = state({
            elapsedMs: 40_000,
            speechMs: 25_000,
            lastSpeechAtMs: 37_000,
        });
        expect(silenceMs(paused)).toBe(3_000);

        const resumed = { ...paused, elapsedMs: 41_000, lastSpeechAtMs: 41_000 };
        expect(silenceMs(resumed)).toBe(0);
        expect(decideEnd(resumed)).toBeNull();
    });

    it('시작 직후의 침묵으로는 끝내지 않는다', () => {
        // 질문을 읽고 생각하는 동안 조용하다. 여기서 끊기면 아예 답변을 못 한다.
        const s = state({
            elapsedMs: C.minAnswerMs - 1,
            speechMs: 5_000,
            lastSpeechAtMs: 1_000,
        });
        expect(decideEnd(s)).toBeNull();
    });

    it('말을 거의 안 했으면 끝내지 않는다', () => {
        // 기침 한 번, 헛기침 정도로 답변이 끝나면 안 된다
        const s = state({
            elapsedMs: 30_000,
            speechMs: C.minSpeechMs - 1,
            lastSpeechAtMs: 5_000,
        });
        expect(decideEnd(s)).toBeNull();
    });

    it('한 마디도 안 했으면 상한까지 기다린다', () => {
        const s = state({ elapsedMs: 60_000, speechMs: 0, lastSpeechAtMs: null });
        expect(decideEnd(s)).toBeNull();
        expect(silenceMs(s)).toBe(0);
    });

    it('시끄러운 환경이면 무음이 안 잡혀 상한으로 떨어진다', () => {
        // 배경 소음 때문에 계속 발화로 판정된다 -> lastSpeechAtMs 가 계속 갱신
        const s = state({ elapsedMs: 80_000, speechMs: 79_000, lastSpeechAtMs: 80_000 });
        expect(decideEnd(s)).toBeNull(); // 아직 상한 전
        expect(decideEnd({ ...s, elapsedMs: C.maxAnswerMs })).toBe('timeout');
    });
});

describe('종료 예고', () => {
    it('침묵이 쌓일수록 진행도가 오른다', () => {
        const base = state({ elapsedMs: 30_000, speechMs: 20_000 });

        expect(endingProgress({ ...base, lastSpeechAtMs: 30_000 })).toBe(0);
        expect(
            endingProgress({ ...base, lastSpeechAtMs: 30_000 - C.endSilenceMs / 2 }),
        ).toBeCloseTo(0.5);
        expect(
            endingProgress({ ...base, lastSpeechAtMs: 30_000 - C.endSilenceMs }),
        ).toBe(1);
    });

    it('끝낼 수 없는 상태면 예고하지 않는다', () => {
        // 말을 충분히 안 했는데 "곧 끝납니다"가 뜨면 사용자가 혼란스럽다
        const s = state({ elapsedMs: 30_000, speechMs: 1_000, lastSpeechAtMs: 5_000 });
        expect(endingProgress(s)).toBe(0);
    });
});
