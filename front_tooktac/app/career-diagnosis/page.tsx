'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createCareerDiagnosis, type CareerDiagnosis } from '@/api/api';

const readinessColor = (score: number) => {
  if (score >= 80) return 'bg-green-500';
  if (score >= 60) return 'bg-[#6ce5e8]';
  if (score >= 40) return 'bg-amber-400';
  return 'bg-red-400';
};

export default function CareerDiagnosisPage() {
  const router = useRouter();
  const [diagnosis, setDiagnosis] = useState<CareerDiagnosis | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadDiagnosis = async () => {
      try {
        const result = await createCareerDiagnosis();
        if (!cancelled) {
          setDiagnosis(result);
        }
      } catch (err: any) {
        if (cancelled) return;

        if (err?.response?.status === 401) {
          router.replace('/login');
          return;
        }

        const message =
          err?.response?.data?.detail || '취업 준비도 진단을 불러오지 못했습니다.';
        setErrorMessage(message);
        alert(message);
        router.replace('/mypage');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadDiagnosis();

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl px-6 py-5 shadow-sm text-center">
          <div className="mx-auto mb-3 h-10 w-10 rounded-full border-4 border-[#6ce5e8] border-t-[#27386d] animate-spin" />
          <p className="text-sm font-medium text-[#27386d]">취업 준비도를 분석하는 중입니다.</p>
        </div>
      </div>
    );
  }

  if (!diagnosis) {
    return (
      <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
          <p className="text-sm text-gray-600">{errorMessage || '진단 결과가 없습니다.'}</p>
          <Link
            href="/mypage"
            className="mt-4 inline-flex items-center rounded-full bg-[#27386d] px-5 py-2 text-sm font-semibold text-white"
          >
            마이페이지로 이동
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4">
          <div className="flex items-center justify-center gap-8 py-4 text-sm md:text-base">
            <Link href="/" className="text-gray-600 hover:text-[#27386d] transition-colors whitespace-nowrap">
              홈화면
            </Link>
            <Link href="/today-interview" className="text-gray-600 hover:text-[#27386d] transition-colors whitespace-nowrap">
              오늘의 면접
            </Link>
            <Link href="/mypage" className="text-gray-600 hover:text-[#27386d] transition-colors whitespace-nowrap">
              마이페이지
            </Link>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#27386d]">AI 취업 준비도 진단</h1>
            <p className="mt-2 text-sm text-gray-600">
              {diagnosis.desired_job || diagnosis.job_group.name} · {diagnosis.job_group.description}
            </p>
          </div>
          <Link
            href="/mypage"
            className="inline-flex items-center justify-center rounded-full border border-[#27386d] px-5 py-2 text-sm font-semibold text-[#27386d] hover:bg-white"
          >
            마이페이지
          </Link>
        </div>

        <div className="grid gap-6">
          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-500">종합 취업 준비도</p>
                <div className="mt-2 flex items-end gap-2">
                  <span className="text-5xl font-bold text-[#27386d]">{diagnosis.total_score}</span>
                  <span className="mb-2 text-lg font-semibold text-gray-500">점</span>
                </div>
                <p className="mt-2 text-sm font-medium text-[#27386d]">{diagnosis.score_label}</p>
              </div>
              <div className="w-full md:max-w-md">
                <div className="h-4 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full rounded-full ${readinessColor(diagnosis.total_score)}`}
                    style={{ width: `${diagnosis.total_score}%` }}
                  />
                </div>
                <p className="mt-3 text-sm leading-6 text-gray-700">{diagnosis.summary}</p>
              </div>
            </div>
          </section>

          <div className="grid gap-6 md:grid-cols-2">
            <section className="bg-white rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-[#27386d]">강점</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {(diagnosis.strengths.length ? diagnosis.strengths : ['추가 정리 필요']).map((item) => (
                  <span key={item} className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
                    {item}
                  </span>
                ))}
              </div>
            </section>

            <section className="bg-white rounded-2xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-[#27386d]">보완 필요</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {diagnosis.weaknesses.map((item) => (
                  <span key={item} className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-700">
                    {item}
                  </span>
                ))}
              </div>
            </section>
          </div>

          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-[#27386d]">기준별 점수</h2>
            <div className="mt-5 grid gap-4">
              {diagnosis.criteria_results.map((item) => (
                <div key={item.criterion_name} className="rounded-xl border border-gray-100 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-[#27386d]">{item.criterion_name}</h3>
                      <p className="mt-1 text-xs text-gray-500">비중 {item.weight}%</p>
                    </div>
                    <span className="text-xl font-bold text-[#27386d]">{item.score}점</span>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full ${readinessColor(item.score)}`}
                      style={{ width: `${item.score}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-gray-700">{item.feedback}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-[#27386d]">이번 주 액션 플랜</h2>
            <div className="mt-5 grid gap-3">
              {diagnosis.action_plan.map((item, index) => (
                <label
                  key={`${item.title}-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-gray-100 p-4"
                >
                  <input type="checkbox" className="mt-1 h-4 w-4 accent-[#27386d]" />
                  <span>
                    <span className="block font-semibold text-[#27386d]">{item.title}</span>
                    <span className="mt-1 block text-sm leading-6 text-gray-700">{item.detail}</span>
                  </span>
                </label>
              ))}
            </div>
          </section>

          <p className="rounded-2xl bg-white px-5 py-4 text-sm leading-6 text-gray-600 shadow-sm">
            {diagnosis.caution}
          </p>
        </div>
      </main>
    </div>
  );
}

