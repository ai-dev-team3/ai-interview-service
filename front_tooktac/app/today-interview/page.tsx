
'use client';

import Link from 'next/link';
import { useUser } from '@/contexts/UserContext'

export default function TodayInterviewPage() {

  const {user} = useUser()
  const userNickname = user?.nickname ?? '사용자';

  return (
      <div className="min-h-screen bg-[#e7f8ff]">
        {/* 헤더 */}
        <div className="bg-white border-b border-gray-100">
          <div className="max-w-4xl mx-auto px-4">
            <div className="flex items-center justify-center space-x-12 py-4">
              <Link href="/" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
                홈화면
              </Link>
              <Link href="/today-interview" className="text-[#27386d] font-semibold cursor-pointer whitespace-nowrap">
                오늘의 면접
              </Link>
              <Link href="/practice-interview" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
                실전면접
              </Link>
              <Link href="/mypage" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
                마이페이지
              </Link>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="text-center">
            {/* 로고와 제목 */}
            <div className="mb-12">
              <h1 className="text-4xl font-bold text-[#27386d] mb-4"
                  style={{ textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)' }}
              >
                오늘의 면접
              </h1>
              <p className="text-lg text-gray-600">
                {userNickname} 님의 이력서·자기소개서 기반 면접 훈련이 시작됩니다!
              </p>
            </div>

            {/* 면접 시작 버튼 */}
            <div className="mb-12">
              <Link href="/today-interview/setup" className="block group">
                <div className="bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-2xl p-12 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer max-w-md mx-auto">
                  <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                    <i className="ri-play-fill text-3xl text-[#27386d]"></i>
                  </div>
                  <h3 className="text-2xl font-bold text-white mt-2 mb-2">면접 시작하기</h3>
                  <p className="text-white/90 leading-relaxed">
                  </p>
                </div>
              </Link>
            </div>

            {/* 면접 단계 안내 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-bold text-[#27386d] mb-6">면접 진행 단계</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="text-center">
                  <div className="w-12 h-12 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-3">
                    <i className="ri-settings-line text-lg text-[#27386d]"></i>
                  </div>
                  <div className="text-sm font-medium text-[#27386d] mb-1">1단계</div>
                  <div className="text-xs text-gray-600">환경 설정</div>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-3">
                    <i className="ri-user-smile-line text-lg text-[#27386d]"></i>
                  </div>
                  <div className="text-sm font-medium text-[#27386d] mb-1">2단계</div>
                  <div className="text-xs text-gray-600">아이스브레이킹</div>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-3">
                    <i className="ri-question-line text-lg text-[#27386d]"></i>
                  </div>
                  <div className="text-sm font-medium text-[#27386d] mb-1">3단계</div>
                  <div className="text-xs text-gray-600">면접 질문 (6개)</div>
                </div>
                <div className="text-center">
                  <div className="w-12 h-12 bg-[#27386d] rounded-full flex items-center justify-center mx-auto mb-3">
                    <i className="ri-medal-line text-lg text-white"></i>
                  </div>
                  <div className="text-sm font-medium text-[#27386d] mb-1">4단계</div>
                  <div className="text-xs text-gray-600">최종 평가</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
  );
}
