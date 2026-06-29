'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchFinalReport } from '@/api/api';

export default function FinalReportLoadingPage() {
    const router = useRouter();

    useEffect(() => {
        let isCancelled = false;

        const fetchAndRedirect = async () => {
            try {
                const report = await fetchFinalReport(); // 최종 리포트 요청
                if (!isCancelled && report) {
                    // 성공 시: 다음 페이지로 이동
                    router.push('/today-interview/final-evaluation');
                }
            } catch (err: any) {
                // 404면 아직 리포트가 준비되지 않은 상태 → 재시도
                if (err?.response?.status === 404) {
                    setTimeout(() => {
                        if (!isCancelled) {
                            fetchAndRedirect(); // 재귀적 재시도
                        }
                    }, 5000);
                } else {
                    console.error('최종 리포트 호출 실패:', err);
                    // router.push('/error');
                }
            }
        };

        fetchAndRedirect();

        return () => {
            isCancelled = true;
        };
    }, [router]);

    return (
        <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center">
            <div className="w-24 h-24 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mb-8 animate-spin">
                <div className="w-16 h-16 bg-[#e7f8ff] rounded-full flex items-center justify-center">
                    <i className="ri-file-chart-line text-2xl text-[#27386d]"></i>
                </div>
            </div>
            <h2 className="text-2xl font-bold text-[#27386d] mb-2">최종 분석 중입니다...</h2>
            <p className="text-[#27386d]/70">AI가 종합 평가 보고서를 생성 중이에요. 잠시만 기다려주세요.</p>
        </div>
    );
}
