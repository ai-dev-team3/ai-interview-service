'use client';

import Link from 'next/link';
import { useState } from 'react';
import { signup, checkUsername } from '@/api/api';
import { useRouter } from 'next/navigation';

export default function SignupPage() {
  const router = useRouter();

  // 1) formData 안에서 desiredJob을 단일 소스로 관리합니다.
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    name: '',
    nickname: '',
    email: '',
    birthdate: '',
    desiredJob: '',       // 영문 코드(frontend, backend, ...)
    resume: null as File | null,
  });

  // 2) 중복 상태 제거: showPassword, showConfirmPassword, usernameStatus만 유지
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState<'none' | 'checking' | 'available' | 'taken'>('none');

  // 3) 공통 인풋 핸들러: username 변경 시 중복 상태 초기화
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (name === 'username') setUsernameStatus('none');
  };

  // 4) 희망 직무 전용 핸들러: 영문 코드 그대로 저장
  const handleDesiredJobChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value; // 예: 'frontend'
    setFormData(prev => ({ ...prev, desiredJob: value }));
  };

  // 5) 파일 변경 핸들러
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData(prev => ({ ...prev, resume: e.target.files![0] }));
    }
  };

  // 6) 아이디 중복 확인
  const checkUsernameAvailability = async () => {
    if (!formData.username.trim()) {
      alert('아이디를 입력해주세요.');
      return;
    }

    setUsernameStatus('checking');
    try {
      const data = await checkUsername(formData.username);
      setUsernameStatus(data.available ? 'available' : 'taken');
    } catch {
      alert('중복확인 중 오류가 발생했습니다.');
      setUsernameStatus('none');
    }
  };

  // 7) 제출
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      alert('비밀번호가 일치하지 않습니다.');
      return;
    }

    if (usernameStatus !== 'available') {
      alert('아이디 중복확인을 완료해주세요.');
      return;
    }

    const form = new FormData();
    form.append('username', formData.username);
    form.append('password', formData.password);
    form.append('name', formData.name);
    form.append('nickname', formData.nickname);
    form.append('email', formData.email);
    form.append('birthdate', formData.birthdate);
    form.append('desiredJob', formData.desiredJob); // 영문 코드 전송
    if (formData.resume) form.append('resume', formData.resume);

    try {
      const result = await signup(form);
      alert(result.message);
      router.push('/login');
    } catch (err: any) {
      alert(err.message || '회원가입 실패');
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#e7f8ff' }}>
      <div className="px-4 sm:px-6 lg:px-8 py-12">
        <div className="max-w-md mx-auto">
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h1 className="text-3xl font-bold text-[#27386d] text-center mb-8">회원가입</h1>

            <form onSubmit={handleSubmit} className="space-y-6" id="signup-form">
              {/* 아이디 입력 및 중복 확인 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">아이디</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    className="flex-1 px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                    placeholder="아이디를 입력하세요"
                    required
                  />
                  <button
                    type="button"
                    onClick={checkUsernameAvailability}
                    disabled={usernameStatus === 'checking'}
                    className="px-4 py-3 bg-[#27386d] text-white text-sm rounded-lg hover:bg-opacity-90 transition-colors whitespace-nowrap cursor-pointer disabled:opacity-50"
                  >
                    {usernameStatus === 'checking' ? '확인중...' : '중복확인'}
                  </button>
                </div>
                {usernameStatus === 'available' && (
                  <p className="mt-2 text-sm text-green-600 flex items-center">
                    <i className="ri-check-line mr-1"></i> 사용 가능한 아이디입니다.
                  </p>
                )}
                {usernameStatus === 'taken' && (
                  <p className="mt-2 text-sm text-red-600 flex items-center">
                    <i className="ri-close-line mr-1"></i> 이미 사용중인 아이디입니다.
                  </p>
                )}
              </div>

              {/* 비밀번호 */}
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

              {/* 비밀번호 확인 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">비밀번호 확인</label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                    placeholder="비밀번호를 다시 입력하세요"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 flex items-center justify-center cursor-pointer"
                  >
                    <i className={`${showConfirmPassword ? 'ri-eye-off-line' : 'ri-eye-line'} text-gray-400`}></i>
                  </button>
                </div>
              </div>

              {/* 이름 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">이름</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  placeholder="이름을 입력하세요"
                  required
                />
              </div>

              {/* 닉네임 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">닉네임</label>
                <input
                  type="text"
                  name="nickname"
                  value={formData.nickname}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  placeholder="닉네임을 입력하세요"
                  required
                />
              </div>

              {/* 이메일 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">이메일</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  placeholder="이메일을 입력하세요"
                  required
                />
              </div>


              {/* 생년월일 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">생년월일</label>
                <input
                  type="date"
                  name="birthdate"
                  value={formData.birthdate}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  required
                />
              </div>

              {/* 희망 직무 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                희망직무
                </label>
                <div className="relative">
                  <select
                    name="desiredJob"
                    value={formData.desiredJob}
                    onChange={handleDesiredJobChange}
                    className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent text-gray-700 bg-white appearance-none"
                    required
                  >
                    <option value="">직무를 선택해주세요</option>
                    <option value="프론트엔드 개발자">프론트엔드 개발자</option>
                    <option value="백엔드 개발자">백엔드 개발자</option>
                    <option value="풀스택 개발자">풀스택 개발자</option>
                    <option value="모바일 개발자">모바일 개발자</option>
                    <option value="DevOps 엔지니어">DevOps 엔지니어</option>
                    <option value="데이터 분석가">데이터 분석가</option>
                    <option value="AI/ML 엔지니어">AI/ML 엔지니어</option>
                    <option value="프로덕트 매니저">프로덕트 매니저</option>
                    <option value="UI/UX 디자이너">UI/UX 디자이너</option>
                    <option value="마케터">마케터</option>
                    <option value="영업">영업</option>
                    <option value="인사담당자">인사담당자</option>
                  </select>
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 flex items-center justify-center pointer-events-none">
                <i className="ri-arrow-down-s-line text-gray-400"></i>
                </div>
                </div>
              </div>

              {/* 이력서 업로드 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">이력서 업로드</label>
                <div className="relative">
                  <input
                    type="file"
                    name="resume"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    id="resume-upload"
                    required
                  />
                  <div className="w-full px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-[#6ce5e8] hover:bg-blue-50/50 transition-colors cursor-pointer">
                    <div className="flex flex-col items-center justify-center">
                      <div className="w-12 h-12 flex items-center justify-center bg-gray-100 rounded-full mb-3">
                        <i className="ri-upload-cloud-2-line text-2xl text-gray-400"></i>
                      </div>
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        {formData.resume ? formData.resume.name : '파일을 선택하거나 드래그해서 업로드'}
                      </p>
                      <p className="text-xs text-gray-500">
                        PDF, HWPX 파일만 업로드 가능 (최대 10MB)
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-[#27386d] text-white py-3 rounded-lg font-semibold hover:bg-opacity-90 transition-colors whitespace-nowrap cursor-pointer"
              >
                회원가입
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-gray-600">
                이미 계정이 있으신가요?{' '}
                <Link href="/login" className="text-[#27386d] hover:underline cursor-pointer">
                  로그인
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

