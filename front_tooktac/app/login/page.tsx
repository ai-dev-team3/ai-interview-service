'use client';

import Link from 'next/link';
import { login } from '@/api/api';
import { useState } from 'react';
import { useUser } from '@/contexts/UserContext'
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext'; // ✅ 추가

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useUser()
  const { setIsLoggedIn } = useAuth(); // ✅ 로그인 상태 변경용 훅

  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const form = new FormData();
      form.append('username', formData.username);
      form.append('password', formData.password);

      await login(form);
      await refreshUser();

      setIsLoggedIn(true);      // ✅ 전역 상태 변경
      router.push('/');
    } catch (err) {
      alert('로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다.');
    }
  };

  return (
      <div className="min-h-screen" style={{ backgroundColor: '#e7f8ff' }}>
        {/* ❌ <Header /> 제거 */}

        <div className="px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-md mx-auto">
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h1 className="text-3xl font-bold text-[#27386d] text-center mb-8">로그인</h1>

              <form onSubmit={handleSubmit} className="space-y-6" id="login-form">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">아이디</label>
                  <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                      placeholder="아이디를 입력하세요"
                      required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">비밀번호</label>
                  <div className="relative">
                    <input
                        type={showPassword ? 'text' : 'password'}
                        name="password"
                        value={formData.password}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                        placeholder="비밀번호를 입력하세요"
                        required
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 flex items-center justify-center cursor-pointer"
                    >
                      <i className={`${showPassword ? 'ri-eye-off-line' : 'ri-eye-line'} text-gray-400`}></i>
                    </button>
                  </div>
                </div>

                <button
                    type="submit"
                    className="w-full bg-[#27386d] text-white py-3 rounded-lg font-semibold hover:bg-opacity-90 transition-colors whitespace-nowrap cursor-pointer"
                >
                  로그인
                </button>
              </form>

              <div className="mt-6 text-center space-y-4">
                <div className="flex justify-center space-x-4 text-sm">
                  <Link href="/forgot-password" className="text-gray-500 hover:text-[#27386d]">비밀번호 찾기</Link>
                  <span className="text-gray-300">|</span>
                  <Link href="/find-id" className="text-gray-500 hover:text-[#27386d]">아이디 찾기</Link>
                </div>
                <p className="text-gray-600">
                  아직 계정이 없으신가요?{' '}
                  <Link href="/signup" className="text-[#27386d] hover:underline cursor-pointer">회원가입</Link>
                </p>
              </div>

              <div className="mt-8 pt-6 border-t border-gray-100">
                <p className="text-center text-sm text-gray-500 mb-4">간편 로그인</p>
                <div className="space-y-3">
                  <button className="w-full flex items-center justify-center py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors whitespace-nowrap cursor-pointer">
                    <i className="ri-google-fill text-xl text-red-500 mr-3"></i>
                    구글로 로그인
                  </button>
                  <button className="w-full flex items-center justify-center py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors whitespace-nowrap cursor-pointer">
                    <i className="ri-kakao-talk-fill text-xl text-yellow-500 mr-3"></i>
                    카카오로 로그인
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
  );
}
