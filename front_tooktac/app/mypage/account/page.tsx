'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import api, {
  changePassword,
  deleteAccount,
  deleteCoverLetter,
  deleteResume,
  getAccount,
  getCoverLetters,
  getJobGroups,
  getResume,
  getResumeStatus,
  updateCoverLetter,
  updateResume,
  uploadCoverLetter,
  uploadResume,
  type AccountInfo,
  type CoverLetter,
  type JobGroup,
  type ResumeDocument,
} from '@/api/api';
import ResumeUploader from '@/components/ResumeUploader';
import { useAuth } from '@/contexts/AuthContext';
import { useUser } from '@/contexts/UserContext';

type CoverLetterPair = {
  question_text: string;
  answer_text: string;
};

export default function AccountPage() {
  const router = useRouter();
  const { setIsLoggedIn } = useAuth();
  const { clearUser } = useUser();
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [deleteSaving, setDeleteSaving] = useState(false);
  const [toast, setToast] = useState('');
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [hasCoverLetter, setHasCoverLetter] = useState<boolean | null>(null);
  const [resumeSaving, setResumeSaving] = useState(false);
  const [resumeEditSaving, setResumeEditSaving] = useState(false);
  const [resumeDeleting, setResumeDeleting] = useState(false);
  const [resumeEditorOpen, setResumeEditorOpen] = useState(false);
  const [resumeDocument, setResumeDocument] = useState<ResumeDocument | null>(null);
  const [resumeForm, setResumeForm] = useState({
    filename: '',
    content: '',
  });
  const [coverLetterSaving, setCoverLetterSaving] = useState(false);
  const [coverLetterDeletingId, setCoverLetterDeletingId] = useState<number | null>(null);
  const [editingCoverLetterId, setEditingCoverLetterId] = useState<number | null>(null);
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
  const [jobGroups, setJobGroups] = useState<JobGroup[]>([]);
  const [coverLetterForm, setCoverLetterForm] = useState({
    company_name: '',
    title: '',
    job_group_id: '',
  });
  const [coverLetterPairs, setCoverLetterPairs] = useState<CoverLetterPair[]>([
    { question_text: '', answer_text: '' },
  ]);
  const resumeSectionRef = useRef<HTMLDivElement>(null);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const refreshResumeDocument = async () => {
    try {
      const resume = await getResume();
      setResumeDocument(resume);
      setResumeForm({
        filename: resume.filename || '',
        content: resume.content || '',
      });
      setHasResume(true);
      return resume;
    } catch {
      setResumeDocument(null);
      setResumeForm({ filename: '', content: '' });
      return null;
    }
  };

  useEffect(() => {
    const loadAccount = async () => {
      try {
        const data = await getAccount();
        setAccount(data);
      } catch {
        router.replace('/login');
      } finally {
        setLoading(false);
      }
    };
    loadAccount();
  }, [router]);

  useEffect(() => {
    const loadResumeStatus = async () => {
      try {
        const data = await getResumeStatus();
        setHasResume(data.has_resume);
        setHasCoverLetter(data.has_cover_letter);
      } catch {
        setHasResume(null);
        setHasCoverLetter(null);
      }
    };
    loadResumeStatus();
  }, []);

  useEffect(() => {
    refreshResumeDocument();
  }, []);

  useEffect(() => {
    const loadCoverLetterData = async () => {
      try {
        const [groups, letters] = await Promise.all([
          getJobGroups(),
          getCoverLetters(),
        ]);
        setJobGroups(groups);
        setCoverLetters(letters);
        setHasCoverLetter(letters.length > 0);
        setCoverLetterForm(prev => ({
          ...prev,
          job_group_id: prev.job_group_id || (groups[0] ? String(groups[0].id) : ''),
        }));
      } catch {
        setJobGroups([]);
        setCoverLetters([]);
      }
    };
    loadCoverLetterData();
  }, []);

  useEffect(() => {
    if (loading) return;

    const params = new URLSearchParams(window.location.search);
    if (params.get('resume') === 'required') {
      setToast('이력서를 먼저 등록해야 면접을 시작할 수 있습니다.');
      setTimeout(() => resumeSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [loading]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 4000);
    return () => clearTimeout(timer);
  }, [toast]);

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPasswordForm(prev => ({ ...prev, [name]: value }));
  };

  const handleResumeExtracted = async (text: string, fileName?: string) => {
    setResumeSaving(true);
    try {
      const result = await uploadResume(text, fileName);
      await refreshResumeDocument();
      setHasResume(true);
      setResumeEditorOpen(false);
      setToast(
        result?.structured === false
          ? '이력서가 저장되었습니다. 분석은 면접 시작 시 자동으로 진행됩니다.'
          : '이력서가 등록되었습니다.'
      );
    } catch {
      setToast('이력서 등록에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setResumeSaving(false);
    }
  };

  const handleResumeFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setResumeForm(prev => ({ ...prev, [name]: value }));
  };

  const openResumeEditor = () => {
    if (!resumeDocument) return;
    setResumeForm({
      filename: resumeDocument.filename || '',
      content: resumeDocument.content || '',
    });
    setResumeEditorOpen(true);
  };

  const handleResumeUpdate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const content = resumeForm.content.trim();
    if (!content) {
      setToast('이력서 내용을 입력해주세요.');
      return;
    }

    setResumeEditSaving(true);
    try {
      const saved = await updateResume(content, resumeForm.filename.trim() || undefined);
      setResumeDocument(saved);
      setResumeForm({
        filename: saved.filename || '',
        content: saved.content || '',
      });
      setHasResume(true);
      setToast('이력서가 수정되었습니다.');
    } catch (err: any) {
      setToast(err?.response?.data?.detail || '이력서 수정에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setResumeEditSaving(false);
    }
  };

  const handleResumeDelete = async () => {
    if (!window.confirm('등록된 이력서를 삭제하시겠습니까?')) {
      return;
    }

    setResumeDeleting(true);
    try {
      await deleteResume();
      setResumeDocument(null);
      setResumeForm({ filename: '', content: '' });
      setResumeEditorOpen(false);
      setHasResume(false);
      setToast('이력서가 삭제되었습니다.');
    } catch (err: any) {
      setToast(err?.response?.data?.detail || '이력서 삭제에 실패했습니다.');
    } finally {
      setResumeDeleting(false);
    }
  };

  const handleCoverLetterChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setCoverLetterForm(prev => ({ ...prev, [name]: value }));
  };

  const handleCoverLetterPairChange = (
    index: number,
    field: keyof CoverLetterPair,
    value: string,
  ) => {
    setCoverLetterPairs(prev =>
      prev.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item
      )
    );
  };

  const addCoverLetterPair = () => {
    setCoverLetterPairs(prev => [...prev, { question_text: '', answer_text: '' }]);
  };

  const removeCoverLetterPair = (index: number) => {
    setCoverLetterPairs(prev =>
      prev.length === 1
        ? [{ question_text: '', answer_text: '' }]
        : prev.filter((_, itemIndex) => itemIndex !== index)
    );
  };

  const resetCoverLetterEditor = () => {
    setEditingCoverLetterId(null);
    setCoverLetterForm(prev => ({ ...prev, company_name: '', title: '' }));
    setCoverLetterPairs([{ question_text: '', answer_text: '' }]);
  };

  const selectCoverLetter = (letter: CoverLetter) => {
    setEditingCoverLetterId(letter.id);
    setCoverLetterForm({
      company_name: letter.company_name || '',
      title: letter.title || '',
      job_group_id: String(letter.job_group_id),
    });
    setCoverLetterPairs(
      letter.items.length > 0
        ? letter.items.map(item => ({
            question_text: item.question_text,
            answer_text: item.answer_text,
          }))
        : [{ question_text: '', answer_text: '' }]
    );
  };

  const handleCoverLetterDelete = async (id: number) => {
    if (!window.confirm('등록된 자소서를 삭제하시겠습니까?')) {
      return;
    }

    setCoverLetterDeletingId(id);
    try {
      await deleteCoverLetter(id);
      setCoverLetters(prev => {
        const next = prev.filter(letter => letter.id !== id);
        setHasCoverLetter(next.length > 0);
        return next;
      });
      if (editingCoverLetterId === id) {
        resetCoverLetterEditor();
      }
      setToast('자소서가 삭제되었습니다.');
    } catch (err: any) {
      setToast(err?.response?.data?.detail || '자소서 삭제에 실패했습니다.');
    } finally {
      setCoverLetterDeletingId(null);
    }
  };

  const handleCoverLetterSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!coverLetterForm.job_group_id) {
      setToast('자소서 직무군을 선택해주세요.');
      return;
    }

    const items = coverLetterPairs
      .map(item => ({
        question_text: item.question_text.trim(),
        answer_text: item.answer_text.trim(),
      }))
      .filter(item => item.question_text || item.answer_text);

    if (items.length === 0) {
      setToast('자소서 질문과 답변을 1개 이상 입력해주세요.');
      return;
    }
    if (items.some(item => !item.question_text || !item.answer_text)) {
      setToast('각 항목의 질문과 답변을 모두 입력해주세요.');
      return;
    }

    setCoverLetterSaving(true);
    try {
      const payload = {
        job_group_id: Number(coverLetterForm.job_group_id),
        company_name: coverLetterForm.company_name.trim() || undefined,
        title: coverLetterForm.title.trim() || undefined,
        items,
      };
      const saved = editingCoverLetterId
        ? await updateCoverLetter(editingCoverLetterId, payload)
        : await uploadCoverLetter(payload);

      setCoverLetters(prev =>
        editingCoverLetterId
          ? prev.map(letter => (letter.id === saved.id ? saved : letter))
          : [saved, ...prev]
      );
      setHasCoverLetter(true);
      if (!editingCoverLetterId) {
        resetCoverLetterEditor();
      } else {
        selectCoverLetter(saved);
      }
      setToast(editingCoverLetterId ? '자소서가 수정되었습니다.' : '자소서가 등록되었습니다.');
    } catch (err: any) {
      setToast(
        err?.response?.data?.detail ||
          (editingCoverLetterId
            ? '자소서 수정에 실패했습니다. 다시 시도해주세요.'
            : '자소서 등록에 실패했습니다. 다시 시도해주세요.')
      );
    } finally {
      setCoverLetterSaving(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setToast('새 비밀번호가 일치하지 않습니다.');
      return;
    }

    setPasswordSaving(true);
    try {
      await changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      setToast('비밀번호가 변경되었습니다.');
    } catch (err: any) {
      setToast(err?.response?.data?.detail || '비밀번호 변경에 실패했습니다.');
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!window.confirm('탈퇴하시겠습니까?')) {
      return;
    }

    setDeleteSaving(true);
    try {
      await deleteAccount();
      alert('탈퇴하셨습니다. 이용해주셔서 감사합니다.');
      clearUser();
      setIsLoggedIn(false);
      localStorage.setItem('auth:event', 'logout');
      // @ts-ignore
      delete api.defaults?.headers?.common?.Authorization;
      router.replace('/');
    } catch (err: any) {
      setToast(err?.response?.data?.detail || '회원 탈퇴에 실패했습니다.');
    } finally {
      setDeleteSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
        <p className="text-sm text-gray-600">계정 정보를 불러오는 중...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      {toast && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 bg-[#27386d] text-white px-6 py-3 rounded-full shadow-lg text-sm font-medium">
          {toast}
        </div>
      )}

      <div className="bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-center space-x-12 py-4">
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

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#27386d] mb-2">계정 관리</h1>
          <p className="text-gray-600">로그인 정보와 이력서 상태를 관리합니다.</p>
        </div>

        <div className="grid gap-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-[#27386d] mb-4">계정 정보</h2>
            <div className="grid gap-3">
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">아이디</p>
                <p className="text-base font-semibold text-[#27386d]">{account?.username}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">닉네임</p>
                <p className="text-sm text-gray-700">{account?.nickname || '-'}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 mb-1">이메일</p>
                <p className="text-sm text-gray-700">{account?.email || '-'}</p>
              </div>
            </div>
          </div>

          <div ref={resumeSectionRef} className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#27386d]">이력서 관리</h2>
              {hasResume !== null && (
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    hasResume ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {hasResume ? '등록됨' : '미등록'}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 mb-4">
              이력서를 등록하면 면접 질문 생성과 취업 준비도 진단에 활용됩니다.
              {hasResume ? ' 새 파일을 업로드하면 기존 이력서를 대체합니다.' : ''}
            </p>
            <ResumeUploader onExtracted={handleResumeExtracted} />
            {resumeSaving && (
              <p className="mt-2 text-sm text-gray-500 text-center">저장 중...</p>
            )}

            {resumeDocument && (
              <div className="mt-5 rounded-lg border border-gray-100 px-4 py-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[#27386d]">
                      등록된 이력서
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {resumeDocument.filename || '파일명 없음'} · {resumeDocument.content?.length || 0}자
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={openResumeEditor}
                      className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-[#27386d] hover:bg-blue-100"
                    >
                      내용 보기
                    </button>
                    <button
                      type="button"
                      onClick={handleResumeDelete}
                      disabled={resumeDeleting}
                      className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {resumeDeleting ? '삭제 중' : '삭제'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {resumeEditorOpen && (
              <form onSubmit={handleResumeUpdate} className="mt-4 space-y-3 rounded-lg border border-[#6ce5e8] bg-[#f3fdff] p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm font-semibold text-[#27386d]">이력서 내용 수정</p>
                  <button
                    type="button"
                    onClick={() => setResumeEditorOpen(false)}
                    className="self-start rounded-full border border-[#27386d]/20 px-3 py-1 text-xs font-medium text-[#27386d] hover:bg-white sm:self-auto"
                  >
                    닫기
                  </button>
                </div>
                <label className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">파일명</span>
                  <input
                    name="filename"
                    value={resumeForm.filename}
                    onChange={handleResumeFormChange}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8]"
                    placeholder="선택 입력"
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">이력서 내용</span>
                  <textarea
                    name="content"
                    value={resumeForm.content}
                    onChange={handleResumeFormChange}
                    rows={10}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] resize-y"
                    placeholder="이력서 내용을 입력하세요."
                  />
                </label>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={resumeEditSaving}
                    className="px-5 py-2 rounded-full bg-[#27386d] text-white text-sm font-medium hover:bg-opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {resumeEditSaving ? '저장 중...' : '수정 저장'}
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#27386d]">자소서 관리</h2>
              {hasCoverLetter !== null && (
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    hasCoverLetter ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {hasCoverLetter ? '등록됨' : '미등록'}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 mb-4">
              자기소개서는 이력서와 별도로 저장됩니다. 여러 개를 등록할 수 있고, 최신 자소서를 취업 준비도 진단에 함께 반영합니다.
            </p>

            <form onSubmit={handleCoverLetterSubmit} className="space-y-4">
              <div className="flex flex-col gap-2 rounded-lg bg-blue-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm font-medium text-[#27386d]">
                  {editingCoverLetterId
                    ? '선택한 자소서를 읽거나 수정 중입니다.'
                    : '새 자소서를 작성 중입니다.'}
                </p>
                {editingCoverLetterId && (
                  <button
                    type="button"
                    onClick={resetCoverLetterEditor}
                    className="self-start rounded-full border border-[#27386d]/20 px-3 py-1 text-xs font-medium text-[#27386d] hover:bg-white sm:self-auto"
                  >
                    새 자소서 작성
                  </button>
                )}
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">직무군</span>
                  <select
                    name="job_group_id"
                    value={coverLetterForm.job_group_id}
                    onChange={handleCoverLetterChange}
                    disabled={jobGroups.length === 0}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8]"
                  >
                    {jobGroups.length === 0 && (
                      <option value="">직무군 정보를 불러오지 못했습니다</option>
                    )}
                    {jobGroups.map(group => (
                      <option key={group.id} value={group.id}>
                        {group.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">회사명</span>
                  <input
                    name="company_name"
                    value={coverLetterForm.company_name}
                    onChange={handleCoverLetterChange}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8]"
                    placeholder="선택 입력"
                  />
                </label>

                <label className="block">
                  <span className="block text-xs font-medium text-gray-600 mb-1">제목</span>
                  <input
                    name="title"
                    value={coverLetterForm.title}
                    onChange={handleCoverLetterChange}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8]"
                    placeholder="선택 입력"
                  />
                </label>
              </div>

              {jobGroups.length === 0 && (
                <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  직무군 데이터가 아직 준비되지 않았습니다. 백엔드 마이그레이션을 최신 상태로 반영한 뒤 다시 시도해주세요.
                </p>
              )}

              <div className="space-y-4">
                {coverLetterPairs.map((pair, index) => (
                  <div key={index} className="rounded-lg border border-gray-100 p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-sm font-semibold text-[#27386d]">
                        문항 {index + 1}
                      </span>
                      {coverLetterPairs.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeCoverLetterPair(index)}
                          className="h-8 w-8 rounded-full text-gray-400 hover:bg-red-50 hover:text-red-600"
                          aria-label={`문항 ${index + 1} 삭제`}
                        >
                          <i className="ri-close-line" />
                        </button>
                      )}
                    </div>
                    <label className="block">
                      <span className="block text-xs font-medium text-gray-600 mb-1">질문</span>
                      <input
                        value={pair.question_text}
                        onChange={(e) => handleCoverLetterPairChange(index, 'question_text', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8]"
                        placeholder="예: 지원동기를 작성해주세요."
                      />
                    </label>
                    <label className="mt-3 block">
                      <span className="block text-xs font-medium text-gray-600 mb-1">답변</span>
                      <textarea
                        value={pair.answer_text}
                        onChange={(e) => handleCoverLetterPairChange(index, 'answer_text', e.target.value)}
                        rows={5}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] resize-y"
                        placeholder="답변을 입력하세요."
                      />
                    </label>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  disabled={coverLetterSaving || jobGroups.length === 0}
                  className="px-5 py-2 rounded-full bg-[#27386d] text-white text-sm font-medium hover:bg-opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {coverLetterSaving
                    ? '저장 중...'
                    : editingCoverLetterId
                      ? '수정 저장'
                      : '자소서 저장'}
                </button>
                <button
                  type="button"
                  onClick={addCoverLetterPair}
                  className="h-11 w-11 rounded-full bg-[#6ce5e8] text-[#27386d] shadow-sm hover:bg-opacity-90"
                  aria-label="질문 답변 추가"
                >
                  <i className="ri-add-line text-xl" />
                </button>
              </div>
            </form>

            {coverLetters.length > 0 && (
              <div className="mt-5 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-[#27386d]">등록된 자소서</p>
                  <span className="text-xs text-gray-500">{coverLetters.length}개</span>
                </div>
                {coverLetters.map(letter => (
                  <div
                    key={letter.id}
                    className={`flex items-start justify-between gap-3 rounded-lg border px-4 py-3 ${
                      editingCoverLetterId === letter.id
                        ? 'border-[#6ce5e8] bg-[#f3fdff]'
                        : 'border-gray-100'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => selectCoverLetter(letter)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="text-sm font-semibold text-[#27386d] truncate">{letter.title}</p>
                      <p className="text-xs text-gray-500">
                        {letter.company_name || '회사명 없음'} · {letter.created_at ? new Date(letter.created_at).toLocaleDateString() : '-'}
                      </p>
                      <p className="mt-1 text-xs text-gray-500">문항 {letter.items.length}개</p>
                    </button>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={() => selectCoverLetter(letter)}
                        className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-[#27386d] hover:bg-blue-100"
                      >
                        열기
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCoverLetterDelete(letter.id)}
                        disabled={coverLetterDeletingId === letter.id}
                        className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {coverLetterDeletingId === letter.id ? '삭제 중' : '삭제'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-[#27386d] mb-4">비밀번호 변경</h2>
            <form onSubmit={handlePasswordSubmit} className="grid gap-4">
              <label className="block">
                <span className="block text-sm font-medium text-gray-700 mb-2">현재 비밀번호</span>
                <input
                  type="password"
                  name="current_password"
                  value={passwordForm.current_password}
                  onChange={handlePasswordChange}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  required
                />
              </label>

              <label className="block">
                <span className="block text-sm font-medium text-gray-700 mb-2">새 비밀번호</span>
                <input
                  type="password"
                  name="new_password"
                  value={passwordForm.new_password}
                  onChange={handlePasswordChange}
                  minLength={8}
                  maxLength={72}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  required
                />
              </label>

              <label className="block">
                <span className="block text-sm font-medium text-gray-700 mb-2">새 비밀번호 확인</span>
                <input
                  type="password"
                  name="confirm_password"
                  value={passwordForm.confirm_password}
                  onChange={handlePasswordChange}
                  minLength={8}
                  maxLength={72}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  required
                />
              </label>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={passwordSaving}
                  className="px-5 py-2 rounded-full bg-[#27386d] text-white text-sm font-medium hover:bg-opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {passwordSaving ? '변경 중...' : '비밀번호 변경'}
                </button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-red-100">
            <h2 className="text-lg font-semibold text-red-600 mb-2">회원 탈퇴</h2>
            <p className="text-sm text-gray-600 mb-4">
              탈퇴하면 계정과 연결된 이력서, 면접 기록, 리포트, 일정이 삭제됩니다.
            </p>
            <form onSubmit={handleDeleteAccount} className="grid gap-4">
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={deleteSaving}
                  className="px-5 py-2 rounded-full bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {deleteSaving ? '처리 중...' : '회원 탈퇴'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
