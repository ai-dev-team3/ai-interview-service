'use client';

import Link from 'next/link';

export default function AboutPage() {
  return (
      <div className="min-h-screen" style={{ backgroundColor: '#e7f8ff' }}>
        {/* ❌ Header 제거 */}

        <div className="px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-4xl mx-auto">
            {/* Hero Section */}
            <div className="text-center mb-20">
              <h1 className="text-5xl font-bold text-[#27386d] mb-6">
                TOOK TAC
              </h1>
              <p className="text-2xl text-gray-700 mb-8">
                매일 12분, AI 기반 맞춤 피드백으로<br />
                면접 역량을 습관처럼 쌓아가는 훈련 서비스
              </p>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                툭 치면 탁 나올 때까지 훈련시켜주는<br />
                루틴 기반 AI 면접 트레이닝 플랫폼
              </p>
            </div>

            {/* Service Purpose */}
            <section className="mb-20">
              <h2 className="text-3xl font-bold text-[#27386d] text-center mb-12">
                서비스 목적
              </h2>
              <div className="bg-white rounded-2xl p-8">
                <p className="text-lg text-gray-700 leading-relaxed text-center">
                  취업 준비생들이 면접에서 자신감을 잃지 않도록 돕고,<br />
                  꾸준한 연습을 통해 자연스럽고 논리적인 답변 능력을 기르는 것이 목표입니다.<br />
                  매일 짧은 시간의 훈련으로 면접 실력을 체계적으로 향상시킬 수 있습니다.
                </p>
              </div>
            </section>

            {/* Core Features */}
            <section className="mb-20">
              <h2 className="text-3xl font-bold text-[#27386d] text-center mb-12">
                핵심 특징
              </h2>
              <div className="space-y-8">
                <div className="bg-white rounded-2xl p-8">
                  <h3 className="text-2xl font-bold text-[#27386d] mb-4">
                    1. AI 기반 개인 맞춤 훈련
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                    개인의 답변 패턴과 약점을 분석하여 맞춤형 질문과 피드백을 제공합니다.
                    반복 학습을 통해 개인별 최적화된 면접 준비가 가능합니다.
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-8">
                  <h3 className="text-2xl font-bold text-[#27386d] mb-4">
                    2. 매일 12분 루틴 훈련
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                    부담 없는 짧은 시간의 일일 훈련으로 꾸준한 학습 습관을 만들어갑니다.
                    바쁜 일상 속에서도 지속 가능한 면접 준비가 가능합니다.
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-8">
                  <h3 className="text-2xl font-bold text-[#27386d] mb-4">
                    3. 실전과 동일한 환경
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                    실제 면접과 같은 환경에서 연습하여 본번에서도 당황하지 않고
                    자신감 있게 답변할 수 있도록 도와줍니다.
                  </p>
                </div>

                <div className="bg-white rounded-2xl p-8">
                  <h3 className="text-2xl font-bold text-[#27386d] mb-4">
                    4. 체계적인 성장 관리
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                    개인의 면접 실력 향상 과정을 데이터로 확인하고,
                    지속적인 동기부여와 목표 설정이 가능합니다.
                  </p>
                </div>
              </div>
            </section>

            {/* How It Works */}
            <section className="mb-20">
              <h2 className="text-3xl font-bold text-[#27386d] text-center mb-12">
                이용 방법
              </h2>
              <div className="grid md:grid-cols-3 gap-8">
                <div className="text-center">
                  <div className="w-16 h-16 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-6">
                    <span className="text-2xl font-bold text-[#27386d]">1</span>
                  </div>
                  <h3 className="text-xl font-bold text-[#27386d] mb-4">회원가입</h3>
                  <p className="text-gray-700">
                    개인 정보와 희망 직무를<br />
                    입력하여 계정을 만듭니다
                  </p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-6">
                    <span className="text-2xl font-bold text-[#27386d]">2</span>
                  </div>
                  <h3 className="text-xl font-bold text-[#27386d] mb-4">매일 훈련</h3>
                  <p className="text-gray-700">
                    하루 12분씩 AI가 제공하는<br />
                    맞춤 질문으로 연습합니다
                  </p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-6">
                    <span className="text-2xl font-bold text-[#27386d]">3</span>
                  </div>
                  <h3 className="text-xl font-bold text-[#27386d] mb-4">성장 확인</h3>
                  <p className="text-gray-700">
                    피드백을 받고 실력 향상<br />
                    과정을 확인합니다
                  </p>
                </div>
              </div>
            </section>

            {/* CTA Section */}
            <section className="text-center">
              <div className="bg-white rounded-2xl p-12">
                <h2 className="text-3xl font-bold text-[#27386d] mb-6">
                  지금 바로 시작해보세요
                </h2>
                <p className="text-lg text-gray-700 mb-8 max-w-2xl mx-auto">
                  매일 12분의 작은 습관이<br />
                  당신의 면접 실력을 완전히 바꿔놓을 것입니다
                </p>
                <Link
                    href="/signup"
                    className="bg-[#6ce5e8] text-[#27386d] px-8 py-4 rounded-full text-lg font-semibold hover:bg-opacity-90 transition-colors inline-block whitespace-nowrap cursor-pointer"
                >
                  무료로 시작하기
                </Link>
              </div>
            </section>
          </div>
        </div>
      </div>
  );
}
