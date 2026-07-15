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

const readinessTone = (score: number) => {
  if (score >= 80) return 'bg-green-100 text-green-700';
  if (score >= 60) return 'bg-[#e7f8ff] text-[#27386d]';
  if (score >= 40) return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-600';
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
        const storedCoverLetterId = window.sessionStorage.getItem('careerDiagnosisCoverLetterId');
        const coverLetterId = storedCoverLetterId ? Number(storedCoverLetterId) : undefined;
        const result = await createCareerDiagnosis(
          coverLetterId && Number.isFinite(coverLetterId)
            ? { cover_letter_id: coverLetterId }
            : undefined
        );
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
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#27386d]">AI 취업 준비도 진단</h1>
            <p className="mt-2 text-sm text-gray-600">
              {diagnosis.desired_job || diagnosis.job_group.name} · {diagnosis.job_group.description}
            </p>
            {diagnosis.source_cover_letter && (
              <p className="mt-1 text-xs text-gray-500">
                사용 자소서: {diagnosis.source_cover_letter.title}
                {diagnosis.source_cover_letter.company_name
                  ? ` · ${diagnosis.source_cover_letter.company_name}`
                  : ''}
              </p>
            )}
          </div>
          <Link
            href="/mypage"
            className="inline-flex items-center justify-center rounded-full border border-[#27386d] px-5 py-2 text-sm font-semibold text-[#27386d] hover:bg-white"
          >
            마이페이지
          </Link>
        </div>

        {diagnosis.evaluation_available === false ? (
          <div className="grid gap-6">
            <section className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-500">진단 상태</p>
                  <h2 className="mt-2 text-3xl font-bold text-[#27386d]">평가 불가</h2>
                  <p className="mt-3 text-sm leading-6 text-gray-700">{diagnosis.summary}</p>
                </div>
                <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700">
                  자료 보완 필요
                </span>
              </div>
              <div className="mt-5 rounded-xl border border-amber-100 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-800">평가할 수 없는 이유</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-amber-800">
                  {(diagnosis.unavailable_reasons?.length
                    ? diagnosis.unavailable_reasons
                    : ['이력서와 자소서에 평가 가능한 실제 경험 근거가 부족합니다.']
                  ).map((reason) => (
                    <li key={reason} className="flex gap-2">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                <Link
                  href="/mypage/account"
                  className="inline-flex items-center justify-center rounded-full bg-[#27386d] px-5 py-2 text-sm font-semibold text-white hover:bg-opacity-90"
                >
                  이력서/자소서 보완하기
                </Link>
                <Link
                  href="/mypage"
                  className="inline-flex items-center justify-center rounded-full border border-[#27386d] px-5 py-2 text-sm font-semibold text-[#27386d] hover:bg-white"
                >
                  마이페이지로 돌아가기
                </Link>
              </div>
            </section>

            <p className="rounded-2xl bg-white px-5 py-4 text-sm leading-6 text-gray-600 shadow-sm">
              {diagnosis.caution}
            </p>
          </div>
        ) : (
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

          {diagnosis.job_fit && (
            <section className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-[#27386d]">직무 적합성 검토</h2>
                  <p className="mt-2 text-sm leading-6 text-gray-700">{diagnosis.job_fit.feedback}</p>
                </div>
                <span
                  className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
                    diagnosis.job_fit.cap < 100
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-green-100 text-green-700'
                  }`}
                >
                  적합성 {diagnosis.job_fit.score}점
                  {diagnosis.job_fit.cap < 100 ? ` · 상한 ${diagnosis.job_fit.cap}점` : ''}
                </span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-gray-100 p-4">
                  <p className="text-sm font-semibold text-[#27386d]">선택 직무 근거</p>
                  <p className="mt-2 text-sm leading-6 text-gray-600">
                    {diagnosis.job_fit.evidence_keywords.length
                      ? diagnosis.job_fit.evidence_keywords.join(', ')
                      : '직접 연결된 근거 키워드가 부족합니다.'}
                  </p>
                </div>
                <div className="rounded-xl border border-gray-100 p-4">
                  <p className="text-sm font-semibold text-[#27386d]">다른 직군 신호</p>
                  <p className="mt-2 text-sm leading-6 text-gray-600">
                    {diagnosis.job_fit.competing_keywords.length
                      ? diagnosis.job_fit.competing_keywords.join(', ')
                      : '두드러진 다른 직군 신호는 없습니다.'}
                  </p>
                </div>
              </div>
            </section>
          )}

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
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#27386d]">기준별 점수</h2>
                <p className="mt-1 text-sm leading-6 text-gray-600">
                  각 기준이 어떤 근거로 평가되었는지 세부 반영 요소와 함께 확인합니다.
                </p>
              </div>
              {diagnosis.llm_reviewed && (
                <span className="inline-flex w-fit rounded-full bg-[#e7f8ff] px-3 py-1 text-xs font-semibold text-[#27386d]">
                  AI 검토 반영
                </span>
              )}
            </div>
            <div className="mt-5 overflow-hidden rounded-xl border border-gray-100">
              {diagnosis.criteria_results.map((item) => (
                <div key={item.criterion_name} className="border-b border-gray-100 p-5 last:border-b-0">
                  <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_120px] md:items-start">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-[#27386d]">{item.criterion_name}</h3>
                        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                          비중 {item.weight}%
                        </span>
                        {item.criterion_cap && item.criterion_cap < 100 && (
                          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                            기준 상한 {item.criterion_cap}점
                          </span>
                        )}
                        {item.job_fit_capped && item.job_fit_cap && (
                          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                            직무 상한 {item.job_fit_cap}점
                          </span>
                        )}
                        {item.llm_reviewed && (
                          <span className="rounded-full bg-[#e7f8ff] px-2.5 py-1 text-xs font-medium text-[#27386d]">
                            AI 검토
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-gray-600">{item.description}</p>
                    </div>
                    <div className="flex items-baseline gap-1 md:justify-end">
                      <span className={`rounded-full px-3 py-1 text-sm font-semibold ${readinessTone(item.score)}`}>
                        {item.score}점
                      </span>
                      {typeof item.rule_score === 'number' && item.llm_reviewed && (
                        <span className="text-xs text-gray-500">룰 {item.rule_score}</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full ${readinessColor(item.score)}`}
                      style={{ width: `${item.score}%` }}
                    />
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                      ['근거 키워드', item.keyword_score],
                      ['구체성', item.specificity_score],
                      ['자료 증거', item.material_score],
                      ['자소서 답변', item.qa_score],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg bg-gray-50 px-3 py-2">
                        <p className="text-xs font-medium text-gray-500">{label}</p>
                        <p className="mt-1 text-sm font-semibold text-[#27386d]">
                          {typeof value === 'number' ? `${value}점` : '-'}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                    <div>
                      <p className="text-xs font-semibold text-gray-500">확인된 근거</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {(item.evidence_keywords?.length
                          ? item.evidence_keywords
                          : item.matched_keywords?.length
                            ? item.matched_keywords
                            : ['근거 키워드 부족']
                        ).slice(0, 6).map((keyword) => (
                          <span
                            key={keyword}
                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                              item.evidence_keywords?.length
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg bg-[#f8fbff] px-4 py-3">
                      <p className="text-xs font-semibold text-[#27386d]">평가 메모</p>
                      <p className="mt-2 text-sm leading-6 text-gray-700">{item.feedback}</p>
                    </div>
                  </div>
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
        )}
      </main>
    </div>
  );
}

