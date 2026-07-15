'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';
import api, { getCoverLetter } from '@/api/api';

interface DraftEntry {
    id: number;
    question: string;
    answer: string;
}

interface ResultEntry {
    dbId: number;
    questionText: string;
    questionType: string;
    revisedAnswer: string;
    feedback: string;
}

type Mode = 'form' | 'loading' | 'result';

const JOB_OPTIONS = ['프론트엔드', '백엔드', 'AI/ML', '데이터', '기획', '디자인'];

// prefix("/cover-letter/feedback") + @router.post("/") 조합이라 마지막 슬래시 포함
const FEEDBACK_ENDPOINT = '/cover-letter/feedback/';

let nextId = 1;

function CoverLetterContent() {
    const { user } = useUser();
    const userNickname = user?.nickname ?? '사용자';

    const searchParams = useSearchParams();
    const coverLetterId = searchParams.get('id');

    const [mode, setMode] = useState<Mode>('form');

    const [companyName, setCompanyName] = useState('');
    const [selectedJob, setSelectedJob] = useState<string | null>(null);
    const [entries, setEntries] = useState<DraftEntry[]>([
        { id: 0, question: '', answer: '' },
    ]);

    const [results, setResults] = useState<ResultEntry[]>([]);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);

    // 마이페이지에서 등록 자소서로 넘어온 경우(?id=): 회사명/문항/답변을 채워 넣는다.
    // 직무는 첨삭 직무 목록과 등록 직무군 체계가 달라 자동 매핑하지 않고 사용자가 고르게 둔다.
    useEffect(() => {
        if (!coverLetterId) return;
        (async () => {
            try {
                const coverLetter = await getCoverLetter(Number(coverLetterId));
                setCompanyName(coverLetter.company_name ?? '');
                const loaded = coverLetter.items.map((item, index) => ({
                    id: index,
                    question: item.question_text,
                    answer: item.answer_text,
                }));
                nextId = loaded.length;
                setEntries(loaded.length > 0 ? loaded : [{ id: 0, question: '', answer: '' }]);
            } catch {
                // 로드 실패 시 빈 폼을 유지한다.
            }
        })();
    }, [coverLetterId]);

    const toggleJob = (job: string) => {
        setSelectedJob((prev) => (prev === job ? null : job));
    };

    const updateEntry = (id: number, field: 'question' | 'answer', value: string) => {
        setEntries((prev) =>
            prev.map((entry) => (entry.id === id ? { ...entry, [field]: value } : entry))
        );
    };

    const addEntry = () => {
        setEntries((prev) => [...prev, { id: nextId++, question: '', answer: '' }]);
    };

    const removeEntry = (id: number) => {
        setEntries((prev) => (prev.length > 1 ? prev.filter((entry) => entry.id !== id) : prev));
    };

    const handleSubmit = async () => {
        if (!companyName.trim()) {
            alert('기업명을 입력해주세요.');
            return;
        }
        if (!selectedJob) {
            alert('직무를 선택해주세요.');
            return;
        }
        const emptyEntry = entries.find((entry) => !entry.question.trim() || !entry.answer.trim());
        if (emptyEntry) {
            alert('모든 문항의 질문과 답변을 입력해주세요.');
            return;
        }

        setSubmitError(null);
        setMode('loading');

        try {
            const { data } = await api.post(FEEDBACK_ENDPOINT, {
                company_name: companyName,
                job_role: selectedJob,
                entries: entries.map((entry) => ({
                    question_text: entry.question,
                    existing_answer: entry.answer,
                })),
            });

            const nextResults: ResultEntry[] = data.items.map((item: any) => ({
                dbId: item.id,
                questionText: item.question_text,
                questionType: item.question_type,
                revisedAnswer: item.revised_answer,
                feedback: item.feedback,
            }));

            setResults(nextResults);
            setMode('result');
        } catch (err: any) {
            const message =
                err?.response?.data?.detail ?? '첨삭 요청 중 오류가 발생했어요. 다시 시도해주세요.';
            setSubmitError(message);
            setMode('form');
        }
    };

    const updateResultAnswer = (dbId: number, value: string) => {
        setResults((prev) =>
            prev.map((r) => (r.dbId === dbId ? { ...r, revisedAnswer: value } : r))
        );
    };

    const handleSave = async () => {
        setIsSaving(true);
        setSaveError(null);

        try {
            await api.patch(FEEDBACK_ENDPOINT, {
                items: results.map((r) => ({ id: r.dbId, revised_answer: r.revisedAnswer })),
            });
            alert('저장됐어요.');
        } catch (err: any) {
            const message =
                err?.response?.data?.detail ?? '저장 중 오류가 발생했어요. 다시 시도해주세요.';
            setSaveError(message);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="min-h-screen bg-white">
            {/* 헤더 */}
            <div className="bg-white border-b border-gray-100">
                <div className="max-w-4xl mx-auto px-4 py-6 text-center">
                    <h1
                        className="text-3xl font-bold text-[#27386d] mb-2"
                        style={{ textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)' }}
                    >
                        자소서첨삭
                    </h1>
                    <p className="text-gray-600">
                        {userNickname} 님의 자기소개서를 AI가 꼼꼼하게 첨삭해드려요
                    </p>
                </div>
            </div>

            {/* 로딩 화면 */}
            {mode === 'loading' && (
                <div className="max-w-3xl mx-auto px-4 py-24 flex flex-col items-center">
                    <div className="w-12 h-12 border-4 border-[#e7f8ff] border-t-[#27386d] rounded-full animate-spin mb-6"></div>
                    <p className="text-gray-600">AI가 자기소개서를 분석하고 있어요...</p>
                </div>
            )}

            {/* 입력 폼 */}
            {mode === 'form' && (
                <div className="max-w-3xl mx-auto px-4 py-10">
                    {/* 기업명 */}
                    <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
                        <label className="block text-sm font-semibold text-[#27386d] mb-2">기업명</label>
                        <input
                            type="text"
                            value={companyName}
                            onChange={(e) => setCompanyName(e.target.value)}
                            placeholder="지원할 기업명을 입력하세요"
                            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent transition-all"
                        />
                    </div>

                    {/* 직무 선택 */}
                    <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
                        <label className="block text-sm font-semibold text-[#27386d] mb-3">직무 선택</label>
                        <div className="flex flex-wrap gap-3">
                            {JOB_OPTIONS.map((job) => {
                                const isSelected = selectedJob === job;
                                return (
                                    <button
                                        key={job}
                                        onClick={() => toggleJob(job)}
                                        className={`px-5 py-2 rounded-full text-sm font-medium transition-all cursor-pointer whitespace-nowrap ${
                                            isSelected
                                                ? 'bg-[#27386d] text-white shadow-md'
                                                : 'bg-[#e7f8ff] text-[#27386d] hover:bg-[#6ce5e8]/30'
                                        }`}
                                    >
                                        {job}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* 자소서 문항/답변 컴포넌트 목록 */}
                    <div className="space-y-6">
                        {entries.map((entry, index) => (
                            <div
                                key={entry.id}
                                className="relative bg-white border border-gray-100 rounded-2xl p-6 shadow-sm"
                            >
                                {entries.length > 1 && (
                                    <button
                                        onClick={() => removeEntry(entry.id)}
                                        className="absolute top-4 right-4 w-7 h-7 flex items-center justify-center rounded-full text-gray-400 hover:text-red-500 hover:bg-white transition-colors cursor-pointer"
                                        aria-label="문항 삭제"
                                    >
                                        <i className="ri-close-line text-lg"></i>
                                    </button>
                                )}

                                <label className="block text-xs font-semibold text-[#27386d] mb-1">
                                    자소서 문항 {index + 1}
                                </label>
                                <input
                                    type="text"
                                    value={entry.question}
                                    onChange={(e) => updateEntry(entry.id, 'question', e.target.value)}
                                    placeholder="자기소개서 문항을 입력하세요"
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 mb-4 text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent transition-all"
                                />

                                <label className="block text-xs font-semibold text-[#27386d] mb-1">
                                    답변 {index + 1}
                                </label>
                                <textarea
                                    value={entry.answer}
                                    onChange={(e) => updateEntry(entry.id, 'answer', e.target.value)}
                                    placeholder="작성한 답변을 입력하세요"
                                    rows={6}
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent transition-all"
                                />
                            </div>
                        ))}
                    </div>

                    {/* 문항 추가 버튼 */}
                    <div className="flex justify-center mt-6">
                        <button
                            onClick={addEntry}
                            className="w-14 h-14 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer"
                            aria-label="문항 추가"
                        >
                            <i className="ri-add-line text-2xl text-white"></i>
                        </button>
                    </div>

                    {submitError && (
                        <p className="text-center text-sm text-red-500 mt-6">{submitError}</p>
                    )}

                    {/* 첨삭 요청 버튼 */}
                    <div className="flex justify-center mt-10">
                        <button
                            onClick={handleSubmit}
                            className="bg-[#27386d] text-white px-10 py-3 rounded-full font-semibold hover:bg-opacity-90 transition-colors cursor-pointer whitespace-nowrap"
                        >
                            첨삭 요청하기
                        </button>
                    </div>
                </div>
            )}

            {/* 결과 화면 (와이어프레임: 기업명/직무 읽기전용, 답변만 수정 가능) */}
            {mode === 'result' && (
                <div className="max-w-3xl mx-auto px-4 py-10">
                    <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
                        <p className="text-sm text-gray-500 mb-1">기업명</p>
                        <p className="text-base font-semibold text-[#27386d]">{companyName}</p>
                    </div>

                    <div className="mb-6">
                        <span className="inline-block px-5 py-2 rounded-full text-sm font-medium bg-[#27386d] text-white shadow-md">
                            {selectedJob}
                        </span>
                    </div>

                    <div className="space-y-6">
                        {results.map((result, index) => (
                            <div
                                key={result.dbId}
                                className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm"
                            >
                                <p className="text-xs font-semibold text-[#27386d] mb-1">
                                    자소서 문항 {index + 1}
                                </p>
                                <p className="w-full border border-gray-100 bg-gray-50 rounded-xl px-4 py-3 mb-4 text-gray-700">
                                    {result.questionText}
                                </p>

                                <label className="block text-xs font-semibold text-[#27386d] mb-1">
                                    답변 {index + 1} (수정 가능)
                                </label>
                                <textarea
                                    value={result.revisedAnswer}
                                    onChange={(e) => updateResultAnswer(result.dbId, e.target.value)}
                                    rows={8}
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent transition-all"
                                />

                                <p className="text-xs text-gray-400 mt-2 leading-relaxed">
                                    {result.feedback}
                                </p>
                            </div>
                        ))}
                    </div>

                    {saveError && (
                        <p className="text-center text-sm text-red-500 mt-6">{saveError}</p>
                    )}

                    <div className="flex justify-center mt-10">
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="bg-[#27386d] text-white px-10 py-3 rounded-full font-semibold hover:bg-opacity-90 transition-colors cursor-pointer whitespace-nowrap disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {isSaving ? '저장 중...' : '저장'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function CoverLetterPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white" />}>
            <CoverLetterContent />
        </Suspense>
    );
}
