'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useUser } from '@/contexts/UserContext';
import api from '@/api/api';
import { useRouter, usePathname } from 'next/navigation';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { isLoggedIn, setIsLoggedIn } = useAuth(); // ✅ 전역 상태 사용
  const { clearUser } = useUser();
  const router = useRouter();
  const pathname = usePathname();
  const hideHeaderRoutes = ['/mypage', '/today-interview/icebreaking', '/today-interview'];
  const shouldHideHeader = hideHeaderRoutes.some(route => pathname.startsWith(route));

  if (isLoggedIn === undefined) return null;
  if (shouldHideHeader) return null;

  const handleProtectedRoute = (path: string) => {
    if (!isLoggedIn) {
      alert('로그인이 필요합니다');
      router.push('/login');
    } else {
      setIsMenuOpen(false);
      router.push(path);
    }
  };

  const handleLogout = async () => {
    try {
      await api.post('/logout');   // ② 서버 세션 종료(쿠키 무효화)
    } catch {
      // 네트워크 오류여도 클라이언트 상태는 정리
    }
    clearUser();                   // ③ UserContext 즉시 비우기(이전 사용자 스냅샷 제거)
    setIsLoggedIn(false);          // ④ 전역 로그인 플래그 false
    localStorage.setItem('auth:event', 'logout'); // ⑤ 다른 탭/창 동기화

    // ⑥ 만약 api.ts에서 Authorization: Bearer ... 를 쓰는 구조라면 헤더를 즉시 제거
    // 쿠키 인증만 쓰면 이 줄은 없어도 됩니다.
    // @ts-ignore
    delete api.defaults?.headers?.common?.Authorization;

    setIsMenuOpen(false);          // ⑦ 모바일 메뉴 닫기
    router.replace('/');           // ⑧ 홈(또는 /login)으로 이동
  };

  return (
      <header className="w-full bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center">
            <span className="text-2xl font-bold text-[#27386d]" style={{ fontFamily: 'var(--font-pacifico)' }}>
              TOOK TAC
            </span>
            </Link>

            <nav className="hidden md:flex items-center space-x-8">
              <Link href="/about" className="text-gray-700 hover:text-[#27386d] transition-colors">서비스 소개</Link>
              <button onClick={() => handleProtectedRoute('/today-interview')} className="text-gray-700 hover:text-[#27386d] transition-colors">오늘의 면접</button>
              {/* <button onClick={() => handleProtectedRoute('/practice-interview')} className="text-gray-700 hover:text-[#27386d] transition-colors">실전면접</button> */}
              <button className="text-gray-700 hover:text-[#27386d] transition-colors">실전면접</button>
              <button onClick={() => handleProtectedRoute('/mypage')} className="text-gray-700 hover:text-[#27386d] transition-colors">마이페이지</button>

              {!isLoggedIn ? (
                  <>
                    <Link href="/login" className="text-gray-700 hover:text-[#27386d] transition-colors">로그인</Link>
                    <Link href="/signup" className="bg-[#27386d] text-white px-6 py-2 rounded-full hover:bg-opacity-90 transition-colors">회원가입</Link>
                  </>
              ) : (
                  <button onClick={handleLogout} className="text-gray-700 hover:text-red-500 transition-colors">로그아웃</button>
              )}
            </nav>

            <button
                className="md:hidden w-6 h-6 flex items-center justify-center cursor-pointer"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              <i className="ri-menu-line text-xl"></i>
            </button>
          </div>

          {isMenuOpen && (
              <div className="md:hidden absolute top-16 left-0 right-0 bg-white border-b border-gray-100 z-50">
                <div className="px-4 py-4 space-y-4">
                  <Link href="/about" className="text-gray-700 hover:text-[#27386d] transition-colors">서비스 소개</Link>
                  <button onClick={() => handleProtectedRoute('/today-interview')} className="text-gray-700 hover:text-[#27386d] transition-colors">오늘의 면접</button>
                  {/* <button onClick={() => handleProtectedRoute('/practice-interview')} className="text-gray-700 hover:text-[#27386d] transition-colors">실전면접</button> */}
                  <button className="text-gray-700 hover:text-[#27386d] transition-colors">실전면접</button>
                  <button onClick={() => handleProtectedRoute('/mypage')} className="text-gray-700 hover:text-[#27386d] transition-colors">마이페이지</button>

                  {!isLoggedIn ? (
                      <>
                        <Link href="/login" className="block text-gray-700 hover:text-[#27386d]">로그인</Link>
                        <Link href="/signup" className="block bg-[#27386d] text-white px-6 py-2 rounded-full text-center hover:bg-opacity-90">회원가입</Link>
                      </>
                  ) : (
                      <button onClick={handleLogout} className="block text-red-500 text-left w-full">로그아웃</button>
                  )}
                </div>
              </div>
          )}
        </div>
      </header>
  );
}
