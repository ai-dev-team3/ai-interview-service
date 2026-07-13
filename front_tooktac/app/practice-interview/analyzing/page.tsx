'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { getInterviewSessionId, getRealAnalysisStatus } from '@/api/api';

/**
 * 마지막 답변 뒤, 남은 백그라운드 분석을 기다리는 화면.
 *
 * 면접 도중에는 분석이 뒤에서 돌았으므로 대부분 여기 도착할 때쯤 거의 끝나 있다.
 * 마지막 한두 문항만 기다리면 된다.
 *
 * 상한을 둔다. 서버가 재시작하거나 분석이 유실되면 결과 행이 영영 안 생기고,
 * 상한이 없으면 이 화면이 영원히 돈다 — 예전에 겪은 무한 로딩과 같은 실패다.
 * 상한을 넘으면 있는 결과만으로 리포트를 만든다.
 */
const POLL_INTERVAL_MS = 2000;
const MAX_WAIT_MS = 3 * 60 * 1000;

export default function AnalyzingPage() {
    const router = useRouter();
    const [status, setStatus] = useState<{ done: number; total: number } | null>(null);
    const [timedOut, setTimedOut] = useState(false);
    const startedAt = useRef(Date.now());

    useEffect(() => {
        const sessionId = getInterviewSessionId();
        if (!sessionId) {
            router.replace('/practice-interview');
            return;
        }

        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;

        const poll = async () => {
            if (cancelled) return;

            try {
                const s = await getRealAnalysisStatus(sessionId);
                if (cancelled) return;
                setStatus({ done: s.done, total: s.total });

                if (s.finished) {
                    router.push('/today-interview/final-evaluation');
                    return;
                }
            } catch (e) {
                // 일시적 실패는 다음 폴링에서 회복된다. 상한이 있으므로 무한히 돌지 않는다.
                console.warn('분석 상태 조회 실패', e);
            }

            if (Date.now() - startedAt.current > MAX_WAIT_MS) {
                // 분석이 유실됐다. 있는 결과만으로 리포트를 만든다.
                console.warn('분석 대기 상한 초과 — 부분 결과로 진행');
                setTimedOut(true);
                return;
            }

            timer = setTimeout(poll, POLL_INTERVAL_MS);
        };

        poll();

        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [router]);

    const percent = status && status.total > 0
        ? Math.round((status.done / status.total) * 100)
        : 0;

    return (
        <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center p-6">
            <div className="max-w-xl w-full bg-white rounded-2xl shadow-lg p-10 text-center">
                <h1 className="text-2xl font-bold text-[#27386d] mb-3">
                    {timedOut ? '분석이 일부 완료되지 않았습니다' : '답변을 분석하고 있습니다'}
                </h1>

                {timedOut ? (
                    <>
                        <p className="text-[#27386d]/70 mb-8 leading-relaxed">
                            일부 문항의 분석이 끝나지 않았습니다.
                            완료된 문항만으로 리포트를 만들어 드릴 수 있습니다.
                        </p>
                        <button
                            onClick={() => router.push('/today-interview/final-evaluation')}
                            className="w-full py-4 rounded-full text-lg font-semibold bg-[#27386d] text-white hover:bg-[#27386d]/90 shadow-lg cursor-pointer"
                        >
                            결과 보기
                        </button>
                    </>
                ) : (
                    <>
                        <p className="text-[#27386d]/70 mb-8">
                            면접 중에 대부분 끝났습니다. 잠시만 기다려주세요.
                        </p>

                        <div className="h-3 w-full bg-[#e7f8ff] rounded-full overflow-hidden mb-3">
                            <div
                                className="h-full bg-[#6ce5e8] transition-all duration-500"
                                style={{ width: `${percent}%` }}
                            />
                        </div>

                        <div className="text-sm text-[#27386d]/60">
                            {status ? `${status.done} / ${status.total} 문항` : '확인 중...'}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
