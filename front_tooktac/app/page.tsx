'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function HomePage() {
  const { isLoggedIn } = useAuth();
  const router = useRouter();

  const requireLogin = (callback: () => void) => {
    if (!isLoggedIn) {
      router.push('/login');
    } else {
      callback();
    }
  };

  const handleTodayInterview = () => {
    requireLogin(() => router.push('/today-interview'));
  };

  const handlePracticeInterview = () => {
    requireLogin(() => router.push('/practice-interview'));
  };

  const handleMyPage = () => {
    requireLogin(() => router.push('/mypage'));
  };

  return (
      <>
        <style jsx global>{`
          @keyframes zoomIn {
            0% {
              transform: scale(1);
            }
            50% {
              transform: scale(1.1);
            }
            100% {
              transform: scale(1);
            }
          }

          .zoom-in-once {
            animation: zoomIn 1s ease-out 1;
            animation-fill-mode: both;
          }

          .zoom-in-delay {
            animation: zoomIn 1s ease-out 1;
            animation-delay: 1s;
            animation-fill-mode: both;
          }
        `}</style>
        <div className="min-h-screen bg-[#e7f8ff]">
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-64px)] px-4">
            <div className="text-center mb-24">
              <h1 className="text-7xl font-bold text-[#27386d] text-center mb-8">
              <span
                  className="text-9xl zoom-in-once inline-block mr-1 font-bold tracking-[0.04em]"
                  style={{textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)'}}
              >
                툭
              </span>
                <span className="tracking-[0.04em]">치면</span>
                <span
                    className="text-9xl zoom-in-delay inline-block mx-1 font-bold tracking-[0.04em]"
                    style={{textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)'}}
                >
                탁
              </span>
                <span className="tracking-[0.04em]">나올 때까지</span>
              </h1>

              <p className="text-2xl text-gray-700 mt-16 mb-0" // mb-24 -> mb-0으로 수정
                 style={{textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)'}}
              >
                매일 12분, AI 기반 맞춤 피드백으로<br/>
                면접 역량을 습관처럼 쌓아가는 훈련 서비스
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-8 mb-16">
              <button
                  onClick={handleTodayInterview}
                  className="group relative overflow-hidden bg-white rounded-3xl shadow-lg hover:shadow-xl transition-all duration-300 p-8 w-80 h-64 flex flex-col items-center justify-center text-center cursor-pointer hover:-translate-y-2"
              >
                <div
                    className="absolute inset-0 bg-gradient-to-br from-[#6ce5e8]/20 to-[#27386d]/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative z-10">
                  <div
                      className="w-20 h-20 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                    <i className="ri-calendar-todo-line text-3xl text-[#27386d]"></i>
                  </div>
                  <h2 className="text-2xl font-bold text-[#27386d] mb-4">오늘의 면접</h2>
                  <p className="text-gray-600 leading-relaxed">
                    매일 12분씩 진행되는<br/>
                    AI 맞춤형 면접 훈련
                  </p>
                </div>
              </button>

              <button
                  //onClick={handlePracticeInterview}
                  className="group relative overflow-hidden bg-white rounded-3xl shadow-lg hover:shadow-xl transition-all duration-300 p-8 w-80 h-64 flex flex-col items-center justify-center text-center cursor-pointer hover:-translate-y-2"
              >
                <div
                    className="absolute inset-0 bg-gradient-to-br from-[#27386d]/20 to-[#6ce5e8]/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative z-10">
                  <div
                      className="w-20 h-20 bg-[#27386d] rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                    <i className="ri-briefcase-line text-3xl text-white"></i>
                  </div>
                  <h2 className="text-2xl font-bold text-[#27386d] mb-4">실전면접</h2>
                  <p className="text-gray-600 leading-relaxed">
                    실제 면접과 같은 환경에서<br/>
                    집중 훈련하기
                  </p>
                </div>
              </button>

              <button
                  onClick={handleMyPage}
                  className="group relative overflow-hidden bg-white rounded-3xl shadow-lg hover:shadow-xl transition-all duration-300 p-8 w-80 h-64 flex flex-col items-center justify-center text-center cursor-pointer hover:-translate-y-2"
              >
                <div
                    className="absolute inset-0 bg-gradient-to-br from-[#6ce5e8]/20 to-[#27386d]/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative z-10">
                  <div
                      className="w-20 h-20 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                    <i className="ri-user-line text-3xl text-white"></i>
                  </div>
                  <h2 className="text-2xl font-bold text-[#27386d] mb-4">마이페이지</h2>
                  <p className="text-gray-600 leading-relaxed">
                    나의 면접 실력 향상 과정과<br/>
                    훈련 기록 확인하기
                  </p>
                </div>
              </button>
            </div>

            <div className="text-center">
              <p className="text-gray-600 mb-6 text-lg">
                매일 꾸준한 연습으로 면접에 대한 자신감을 키워보세요
              </p>
              <div className="flex justify-center space-x-8 text-sm text-gray-500">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-[#6ce5e8] rounded-full"></div>
                  <span>AI 맞춤 분석</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-[#27386d] rounded-full"></div>
                  <span>실시간 피드백</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full"></div>
                  <span>성장 추적</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
  );
}
