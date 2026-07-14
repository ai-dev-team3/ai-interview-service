'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import QuestionClientResultPage from './QuestionClientResultPage';
import { fetchFullResult } from '@/api/api';

type Props = { questionId: string; totalQuestions: number };

const POLL_INTERVAL_MS = 2000;
const MAX_ATTEMPTS = 90; // 약 3분. 넘어가면 무한 로딩 대신 에러를 보여준다.

export default function QuestionClientLoadingPage({ questionId, totalQuestions }: Props) {
  const [resultData, setResultData] = useState<any | null>(null);
  const [timedOut, setTimedOut] = useState(false);

  const current = parseInt(questionId, 10);
  const nextLink =
    current < totalQuestions
      ? `/today-interview/${current + 1}`
      : `/today-interview/final-report`;

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts += 1;
      if (attempts > MAX_ATTEMPTS) {
        if (!cancelled) {
          setTimedOut(true);
          clearInterval(interval);
        }
        return;
      }

      try {
        // 이 질문의 결과만 조회한다. 세션의 질문이 모두 미리 만들어지므로
        // "가장 마지막 질문"을 보면 1번을 답해도 영원히 processing이 된다.
        const data = await fetchFullResult(current);

        // 클라이언트 방어: model_answer가 없으면 아직 준비 안 된 상태로 간주하고 계속 폴링
        const hasModelAnswer =
          typeof data?.model_answer === 'string' && data.model_answer.trim().length > 0;

        // 백엔드가 분석 실패(failed)를 알려주면 더 기다리지 않고 현재 결과로 표시
        if (hasModelAnswer || data?.status === 'failed') {
          if (!cancelled) {
            setResultData(data);
            clearInterval(interval);
          }
        }
        // 준비 안 되었으면(processing) 다음 interval에서 재시도
      } catch (err: any) {
        // 404는 아직 준비 전이니 무시하고 재시도
        if (err?.response?.status !== 404) {
          console.error('결과 요청 실패:', err);
        }
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [current]);

  if (resultData) {
    return <QuestionClientResultPage result={resultData} nextLink={nextLink} totalQuestions={totalQuestions} />;
  }

  if (timedOut) {
    return (
      <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center px-4">
        <h2 className="text-2xl font-bold text-[#27386d] mb-2">분석이 지연되고 있습니다</h2>
        <p className="text-[#27386d]/70 mb-8 text-center">
          잠시 후 다시 시도해주세요. 문제가 계속되면 마이페이지에서 결과를 확인할 수 있습니다.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => window.location.reload()}
            className="bg-[#27386d] text-white rounded-xl px-6 py-3"
          >
            다시 시도
          </button>
          <Link href="/mypage" className="border border-[#27386d] text-[#27386d] rounded-xl px-6 py-3">
            마이페이지로
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center">
      <div className="relative w-24 h-24 mb-8">
        <div className="absolute inset-0 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full animate-spin"></div>
        <div className="absolute inset-4 bg-[#e7f8ff] rounded-full flex items-center justify-center">
          <i className="ri-mic-line text-2xl text-[#27386d]"></i>
        </div>
      </div>
      <h2 className="text-2xl font-bold text-[#27386d] mb-2">답변을 분석 중입니다...</h2>
      <p className="text-[#27386d]/70">AI가 피드백을 생성하고 있어요. 잠시만 기다려주세요.</p>
    </div>
  );
}
