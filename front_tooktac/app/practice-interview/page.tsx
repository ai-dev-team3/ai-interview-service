'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { startRealInterview } from '@/api/api';

/**
 * 실전 면접 시작 화면.
 *
 * 여기서 카메라·마이크를 확인하고 시작한다. 시작하면 첫 질문과 함께 진행 화면으로
 * 넘어가고, 거기서 준비 10초 동안 자세 분석 모드 벤치마크(5초)가 돈다.
 */
export default function PracticeInterviewPage() {
    const router = useRouter();
    const [starting, setStarting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleStart = async () => {
        setStarting(true);
        setError(null);
        try {
            const start = await startRealInterview();
            // 첫 질문은 진행 화면으로 넘긴다. 다시 요청하면 세션이 하나 더 생긴다.
            sessionStorage.setItem('real_interview_start', JSON.stringify(start));
            router.push('/practice-interview/session');
        } catch (e: any) {
            const detail = e?.response?.data?.detail;
            setError(detail || '면접을 시작하지 못했습니다. 잠시 후 다시 시도해주세요.');
            setStarting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center p-6">
            <div className="max-w-2xl w-full bg-white rounded-2xl shadow-lg p-10">
                <h1 className="text-3xl font-bold text-[#27386d] mb-4">실전 면접</h1>

                <p className="text-[#27386d]/80 mb-8 leading-relaxed">
                    실제 면접처럼 진행됩니다. 질문은 이력서를 바탕으로 면접관이 정하며,
                    미리 볼 수 없습니다. 답변에 따라 꼬리질문이 이어질 수 있습니다.
                </p>

                <ul className="space-y-3 mb-10 text-[#27386d]">
                    <li className="flex gap-3">
                        <span className="text-[#6ce5e8] font-bold">·</span>
                        질문마다 준비 10초, 답변 90초입니다. 최대 7문항, 약 12분 걸립니다.
                    </li>
                    <li className="flex gap-3">
                        <span className="text-[#6ce5e8] font-bold">·</span>
                        진행 중에는 피드백이 표시되지 않습니다. 결과는 끝난 뒤 리포트로 봅니다.
                    </li>
                    <li className="flex gap-3">
                        <span className="text-[#6ce5e8] font-bold">·</span>
                        중간에 나가면 면접이 종료되며 다시 이어서 볼 수 없습니다.
                    </li>
                </ul>

                {error && (
                    <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-700 text-sm">
                        {error}
                    </div>
                )}

                <button
                    onClick={handleStart}
                    disabled={starting}
                    className={`w-full py-4 rounded-full text-lg font-semibold transition-all ${
                        starting
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-[#27386d] text-white hover:bg-[#27386d]/90 shadow-lg cursor-pointer'
                    }`}
                >
                    {starting ? '면접을 준비하는 중...' : '실전 면접 시작하기'}
                </button>
            </div>
        </div>
    );
}
