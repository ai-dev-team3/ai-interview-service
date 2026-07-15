'use client';

import { useState } from 'react';
import { useUser } from '@/contexts/UserContext';

interface CoverLetterEntry {
    id: number;
    question: string;
    answer: string;
}

const JOB_OPTIONS = ['프론트엔드', '백엔드', 'AI/ML', '데이터', '기획', '디자인'];

let nextId = 1;

export default function CoverLetterPage() {
    const { user } = useUser();
    const userNickname = user?.nickname ?? '사용자';

    const [companyName, setCompanyName] = useState('');
    const [selectedJob, setSelectedJob] = useState<string | null>(null);
    const [entries, setEntries] = useState<CoverLetterEntry[]>([
        { id: 0, question: '', answer: '' },
    ]);

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

    const handleSubmit = () => {
        // TODO: 백엔드 연동 (자소서 첨삭 요청 API 호출)
        console.log({ companyName, selectedJob, entries });
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
        </div>
    );
}
