'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import api, {
  changePassword,
  deleteAccount,
  getAccount,
  getResumeStatus,
  uploadResume,
  type AccountInfo,
} from '@/api/api';
import ResumeUploader from '@/components/ResumeUploader';
import { useAuth } from '@/contexts/AuthContext';
import { useUser } from '@/contexts/UserContext';

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
  const [resumeSaving, setResumeSaving] = useState(false);
  const resumeSectionRef = useRef<HTMLDivElement>(null);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

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
      } catch {
        setHasResume(null);
      }
    };
    loadResumeStatus();
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
      setHasResume(true);
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
              이력서를 등록하면 이력서·자기소개서 기반 맞춤 면접 질문이 생성됩니다.
              {hasResume ? ' 새 파일을 업로드하면 기존 이력서를 대체합니다.' : ''}
            </p>
            <ResumeUploader onExtracted={handleResumeExtracted} />
            {resumeSaving && (
              <p className="mt-2 text-sm text-gray-500 text-center">저장 중...</p>
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
