'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
    type InterviewQuestion,
    type RealInterviewStart,
    submitClosingRemark,
    submitRealAnswer,
} from '@/api/api';
import { useAnswerRecorder } from '@/hooks/useAnswerRecorder';
import { ENDING_HINT_RATIO, type EndReason } from '@/lib/answerEnd';
import { useExpressionSocket } from '@/hooks/useExpressionSocket';
import { usePostureBenchmark } from '@/hooks/usePostureBenchmark';
import { useWebcamPreview } from '@/hooks/useWebcamPreview';

type Phase = 'prepare' | 'answer' | 'sending';

/**
 * 실전 면접 진행 화면.
 *
 * 연습과 다른 점:
 *   - 질문이 한 번에 하나씩만 온다. 다음 질문은 답변을 올려야 정해진다(꼬리질문 때문).
 *   - 실시간 피드백을 보여주지 않는다. 자세 분석은 뒤에서 계속 돌아 점수에 반영된다.
 *   - 문항별 결과 화면이 없다. 분석은 백그라운드에서 돌고 끝나야 리포트를 본다.
 */
export default function RealInterviewSessionPage() {
    const router = useRouter();

    const [start, setStart] = useState<RealInterviewStart | null>(null);
    const [question, setQuestion] = useState<InterviewQuestion | null>(null);
    // 마무리 질문. 채점하지 않으므로 질문 행이 없다 — 텍스트만 온다.
    const [closingQuestion, setClosingQuestion] = useState<string | null>(null);
    const [phase, setPhase] = useState<Phase>('prepare');
    const [seconds, setSeconds] = useState(0);
    const [error, setError] = useState<string | null>(null);

    // 진행 중 이탈 방지. 실전이라 재개를 허용하지 않으므로 나가면 그 세션은 끝이다.
    const leavingRef = useRef(false);

    useWebcamPreview();

    // 준비 10초 안에 자세 분석 모드를 정한다(측정 5초). 연습에서는 아이스브레이킹이
    // 그 자리였지만 실전에는 아이스브레이킹이 없다. 여기서 안 하면 실전 사용자는
    // 전원 서버 모드로 떨어져 1인당 100MB 넘게 먹는다.
    usePostureBenchmark(true);

    // 자세는 계속 분석하되 화면에는 표시하지 않는다 (setter를 넘기지 않는다).
    useExpressionSocket({
        isAnswerActive: phase === 'answer',
        questionId: String(question?.question_order ?? 0),
    });

    useEffect(() => {
        const raw = sessionStorage.getItem('real_interview_start');
        if (!raw) {
            router.replace('/practice-interview');
            return;
        }
        const parsed = JSON.parse(raw) as RealInterviewStart;
        setStart(parsed);
        setQuestion(parsed.question);
        setSeconds(parsed.prepare_seconds);
    }, [router]);

    useEffect(() => {
        const warn = (e: BeforeUnloadEvent) => {
            if (leavingRef.current) return;
            e.preventDefault();
            e.returnValue = '';
        };
        window.addEventListener('beforeunload', warn);
        return () => window.removeEventListener('beforeunload', warn);
    }, []);

    // 준비 시간 카운트다운. 답변 시간은 녹음 훅이 관리한다 —
    // 말이 끝나면 90초를 다 채우지 않고 끝나기 때문이다.
    useEffect(() => {
        if (!start || phase !== 'prepare') return;

        if (seconds <= 0) {
            setPhase('answer');
            return;
        }

        const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
        return () => clearTimeout(t);
    }, [seconds, phase, start]);

    const handleRecorded = useCallback(
        async (audio: Blob, reason: EndReason) => {
            if (!start) return;
            setPhase('sending');
            console.info(`[answer] 답변 종료 (${reason}) — 전송`);

            try {
                // 마지막 한마디는 채점하지 않는다. 따로 올리고 면접을 끝낸다.
                if (closingQuestion) {
                    await submitClosingRemark(start.session_id, audio);
                    leavingRef.current = true;
                    router.push('/practice-interview/analyzing');
                    return;
                }

                if (!question) return;
                const result = await submitRealAnswer(
                    start.session_id,
                    question.question_order,
                    audio,
                );

                // 시간이 다 되면 마무리 질문이 온다. 질문 행은 없다.
                if (result.closing && result.closing_question) {
                    setClosingQuestion(result.closing_question);
                    setQuestion(null);
                    setPhase('prepare');
                    setSeconds(start.prepare_seconds);
                    return;
                }

                if (!result.question) {
                    leavingRef.current = true;
                    router.push('/practice-interview/analyzing');
                    return;
                }

                setQuestion(result.question);
                setPhase('prepare');
                setSeconds(start.prepare_seconds);
            } catch (e) {
                console.error('답변 전송 실패', e);
                setError('답변을 전송하지 못했습니다. 네트워크를 확인해주세요.');
            }
        },
        [start, question, closingQuestion, router],
    );

    const { ending, remainingSec } = useAnswerRecorder({
        active: phase === 'answer',
        questionOrder: closingQuestion ? -1 : (question?.question_order ?? 0),
        onComplete: handleRecorded,
    });

    // 아무 예고 없이 화면이 넘어가면 "잘렸다"고 느낀다. 침묵이 쌓이기 시작하면 알린다.
    const isEnding = phase === 'answer' && ending >= ENDING_HINT_RATIO;

    const label = isEnding
        ? '답변을 마치는 중'
        : phase === 'prepare'
          ? '준비'
          : phase === 'answer'
            ? '답변 중'
            : '전송 중';

    // 비디오 엘리먼트는 항상 렌더한다. 로딩 중이라고 화면을 통째로 갈아끼우면
    // #webcam-video 가 DOM 에 없는 렌더가 생기고, 그러면 웹캠이 영영 안 붙는다.
    return (
        <div className="min-h-screen bg-[#e7f8ff] p-6">
            <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-48px)]">
                <div className="flex flex-col justify-center items-center text-center px-8">
                    {closingQuestion ? (
                        <>
                            <div className="text-sm text-[#27386d]/60 mb-6">마지막 질문</div>
                            <h1 className="text-3xl font-bold text-[#27386d] leading-relaxed max-w-[520px]">
                                {closingQuestion}
                            </h1>
                        </>
                    ) : question && start ? (
                        <>
                            <div className="text-sm text-[#27386d]/60 mb-6">
                                질문 {question.question_order}
                                {question.is_follow_up ? ' · 꼬리질문' : ''}
                            </div>
                            <h1 className="text-3xl font-bold text-[#27386d] leading-relaxed max-w-[520px]">
                                {question.question_text}
                            </h1>
                        </>
                    ) : (
                        <div className="text-[#27386d] text-xl">면접을 불러오는 중...</div>
                    )}

                    {error && (
                        <div className="mt-8 p-4 rounded-lg bg-red-50 text-red-700 text-sm">
                            {error}
                        </div>
                    )}
                </div>

                <div className="flex flex-col items-center justify-center">
                    <div className="relative w-[600px] h-[450px] bg-black rounded-2xl mb-8">
                        <video
                            id="webcam-video"
                            className="absolute w-full h-full object-cover rounded-2xl"
                            autoPlay
                            muted
                            playsInline
                        />
                        {phase === 'answer' && (
                            <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/90">
                                <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />
                                <span className="text-white text-sm font-medium">녹음 중</span>
                            </div>
                        )}
                    </div>

                    <div className="bg-white rounded-xl shadow-lg p-6 w-[600px] text-center">
                        <div className="text-sm text-[#27386d]/70 mb-1">{label}</div>

                        <div className="text-4xl font-mono font-bold text-[#27386d]">
                            {phase === 'sending' || !start
                                ? '...'
                                : phase === 'answer'
                                  ? `${remainingSec}초`
                                  : `${seconds}초`}
                        </div>

                        {isEnding && (
                            <>
                                <div className="mt-4 h-1.5 w-full bg-[#e7f8ff] rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-[#6ce5e8] transition-[width] duration-150"
                                        style={{ width: `${Math.round(ending * 100)}%` }}
                                    />
                                </div>
                                <div className="mt-2 text-xs text-[#27386d]/60">
                                    말을 이어가면 계속 녹음됩니다
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
