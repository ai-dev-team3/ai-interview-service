'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ResumeQuestion,
  addResumeQuestion,
  deleteResumeQuestion,
  getResumeQuestions,
  startInterview,
  updateResumeQuestion,
} from '@/api/api';

const MAX_QUESTIONS = 7;

export default function ComposeQuestionsClient() {
  const router = useRouter();

  const [pool, setPool] = useState<ResumeQuestion[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]); // 자기소개 제외, 배열 순서 = 출제 순서
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [newText, setNewText] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  const defaultQuestion = pool.find((q) => q.is_default) ?? null;
  const optional = pool.filter((q) => !q.is_default);
  const byId = new Map(pool.map((q) => [q.id, q]));
  const selected = selectedIds.map((id) => byId.get(id)).filter(Boolean) as ResumeQuestion[];

  // 자기소개는 항상 1번으로 고정 포함된다
  const totalCount = selected.length + (defaultQuestion ? 1 : 0);
  const overLimit = totalCount > MAX_QUESTIONS;

  useEffect(() => {
    getResumeQuestions()
      .then((data) => setPool(data.questions))
      .catch(() => setError('질문 목록을 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: number) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  const move = (index: number, delta: number) =>
    setSelectedIds((prev) => {
      const next = [...prev];
      const target = index + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });

  const handleAdd = async () => {
    const text = newText.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const created = await addResumeQuestion(text);
      setPool((prev) => [...prev, created]);
      setSelectedIds((prev) => [...prev, created.id]);
      setNewText('');
    } catch {
      setError('질문을 추가하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const handleSaveEdit = async (id: number) => {
    const text = editText.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const updated = await updateResumeQuestion(id, text);
      setPool((prev) => prev.map((q) => (q.id === id ? updated : q)));
      setEditingId(null);
    } catch {
      setError('질문을 수정하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (busy) return;
    setBusy(true);
    try {
      await deleteResumeQuestion(id);
      setPool((prev) => prev.filter((q) => q.id !== id));
      setSelectedIds((prev) => prev.filter((x) => x !== id));
    } catch {
      setError('질문을 삭제하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const handleStart = async () => {
    if (overLimit || busy) return;
    setBusy(true);
    try {
      await startInterview(selectedIds);
      router.push('/today-interview/1');
    } catch {
      setError('면접을 시작하지 못했습니다.');
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
        <p className="text-[#27386d]">질문을 불러오는 중입니다...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#e7f8ff] py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-[#27386d] mb-2">면접 질문 구성</h1>
        <p className="text-[#27386d]/70 mb-8">
          답변할 질문을 고르고 순서를 정하세요. 1분 자기소개는 항상 첫 질문으로 포함됩니다.
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-6">{error}</div>
        )}

        {/* 선택된 질문 (출제 순서) */}
        <section className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#27386d]">출제 순서</h2>
            <span className={`text-sm font-medium ${overLimit ? 'text-red-600' : 'text-[#27386d]/70'}`}>
              {totalCount} / {MAX_QUESTIONS}
            </span>
          </div>

          {defaultQuestion && (
            <div className="flex items-center gap-3 bg-[#f8fafc] rounded-xl p-4 mb-2">
              <span className="w-7 h-7 rounded-full bg-[#27386d] text-white text-sm flex items-center justify-center">1</span>
              <span className="flex-1 text-[#27386d]">{defaultQuestion.question_text}</span>
              <span className="text-xs text-gray-500">고정</span>
            </div>
          )}

          {selected.map((q, i) => (
            <div key={q.id} className="flex items-center gap-3 bg-[#f8fafc] rounded-xl p-4 mb-2">
              <span className="w-7 h-7 rounded-full bg-[#6ce5e8] text-[#27386d] text-sm flex items-center justify-center">
                {i + 2}
              </span>
              <span className="flex-1 text-[#27386d]">{q.question_text}</span>
              <button onClick={() => move(i, -1)} disabled={i === 0} className="px-2 disabled:opacity-30" aria-label="위로">
                ↑
              </button>
              <button
                onClick={() => move(i, 1)}
                disabled={i === selected.length - 1}
                className="px-2 disabled:opacity-30"
                aria-label="아래로"
              >
                ↓
              </button>
              <button onClick={() => toggle(q.id)} className="px-2 text-gray-500" aria-label="선택 해제">
                ✕
              </button>
            </div>
          ))}

          {overLimit && (
            <p className="text-sm text-red-600 mt-3">
              질문을 {MAX_QUESTIONS}개 이하로 줄여주세요.
            </p>
          )}
        </section>

        {/* 질문 풀 */}
        <section className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold text-[#27386d] mb-4">질문 목록</h2>

          {optional.length === 0 && (
            <p className="text-sm text-gray-500 mb-4">저장된 질문이 없습니다. 아래에서 직접 추가해보세요.</p>
          )}

          {optional.map((q) => (
            <div key={q.id} className="flex items-center gap-3 border-b border-gray-100 py-3">
              {editingId === q.id ? (
                <>
                  <input
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
                  />
                  <button onClick={() => handleSaveEdit(q.id)} disabled={busy} className="text-[#27386d] px-2">
                    저장
                  </button>
                  <button onClick={() => setEditingId(null)} className="text-gray-500 px-2">
                    취소
                  </button>
                </>
              ) : (
                <>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(q.id)}
                    onChange={() => toggle(q.id)}
                    className="w-4 h-4"
                  />
                  <div className="flex-1">
                    <div className="text-[#27386d]">{q.question_text}</div>
                    <div className="text-xs text-gray-500">{q.question_type}</div>
                  </div>
                  <button
                    onClick={() => {
                      setEditingId(q.id);
                      setEditText(q.question_text);
                    }}
                    className="text-gray-500 px-2"
                  >
                    수정
                  </button>
                  <button onClick={() => handleDelete(q.id)} disabled={busy} className="text-gray-500 px-2">
                    삭제
                  </button>
                </>
              )}
            </div>
          ))}

          <div className="flex gap-2 mt-5">
            <input
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="직접 질문 추가"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
            />
            <button
              onClick={handleAdd}
              disabled={busy || !newText.trim()}
              className="bg-[#27386d] text-white rounded-lg px-5 disabled:opacity-40"
            >
              추가
            </button>
          </div>
        </section>

        <button
          onClick={handleStart}
          disabled={overLimit || busy}
          className="w-full bg-gradient-to-r from-[#6ce5e8] to-[#27386d] text-white font-semibold rounded-xl py-4 disabled:opacity-40"
        >
          면접 시작하기
        </button>
      </div>
    </div>
  );
}
