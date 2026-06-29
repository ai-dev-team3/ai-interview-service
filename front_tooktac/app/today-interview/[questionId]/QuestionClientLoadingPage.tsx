'use client';

import { useEffect, useState } from 'react';
import QuestionClientResultPage from './QuestionClientResultPage';
import { fetchFullLatestResult } from '@/api/api';

type Props = { questionId: string };

export default function QuestionClientLoadingPage({ questionId }: Props) {
  const [resultData, setResultData] = useState<any | null>(null);
  const current = parseInt(questionId, 10);
  const nextLink = current < 6
    ? `/today-interview/${current + 1}?questionId=${questionId}`
    : `/today-interview/final-report`;

  useEffect(() => {
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const data = await fetchFullLatestResult();

        // 클라이언트 방어: model_answer가 없으면 아직 준비 안 된 상태로 간주하고 계속 폴링
        const hasModelAnswer =
          typeof data?.model_answer === 'string' && data.model_answer.trim().length > 0;

        if (hasModelAnswer) {
          if (!cancelled) {
            setResultData(data);
            clearInterval(interval);
          }
        }
        // 준비 안 되었으면 그냥 다음 interval에서 재시도
      } catch (err: any) {
        // 404는 아직 준비 전이니 무시하고 재시도
        if (err?.response?.status !== 404) {
          console.error('결과 요청 실패:', err);
          // 네트워크 오류 등은 잠깐 멈추고 다음 tick에 재시도
        }
      }
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [questionId]);

  if (resultData) {
    return <QuestionClientResultPage result={resultData} nextLink={nextLink} />;
  }

  return (
    <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center">
      <div className="w-24 h-24 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mb-8 animate-spin">
        <div className="w-16 h-16 bg-[#e7f8ff] rounded-full flex items-center justify-center">
          <i className="ri-mic-line text-2xl text-[#27386d]"></i>
        </div>
      </div>
      <h2 className="text-2xl font-bold text-[#27386d] mb-2">답변을 분석 중입니다...</h2>
      <p className="text-[#27386d]/70">AI가 피드백을 생성하고 있어요. 잠시만 기다려주세요.</p>
    </div>
  );
}
