'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/contexts/UserContext';

export default function IcebreakingPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const {user} = useUser()
  const userNickname = user?.nickname || '사용자';

  useEffect(() => {
    setMounted(true);
  }, []);

  const steps = [
    '아이스브레이킹',
    '질문 1',
    '질문 2',
    '질문 3',
    '질문 4',
    '질문 5',
    '질문 6',
    '최종 평가'
  ];

  const icebreakerQuestions = [
    "오늘 아침 어떻게 시작하셨어요?",
    "1분 자기소개 부탁드릴게요.",
    "요즘 즐겨 보는 콘텐츠가 있다면요?",
    "존경하는 인물이 있다면 누구인지,\n그리고 이유도 말씀해 주세요.",
    "본인을 어떤 사물에 비유할 수 있을까요?",
    "요즘 뉴스 중에 관심 있게 본 \n이슈가 있을까요?",
    "최근에 읽은 책 중 \n인상 깊었던 책을 소개해 주세요.",
    "스트레스를 받을 때 보통 어떻게 푸세요?",
    "회사에 어떤 복지가 있으면 \n좋겠다고 생각하세요?",
    "학창시절에 해보신 아르바이트가 \n있다면 소개해주세요.",
    "본인을 색깔로 표현한다면 어떤 색일까요?",
    "최근에 화났던 일이 있다면, \n어떤 상황이었나요?"
  ];

  const handleQuestionSelect = (question: string) => {
    if (!mounted) return;

    setSelectedQuestion(question);
    router.push(`/today-interview/answer?question=${encodeURIComponent(question)}`);
  };

  if (!mounted) {
    return (
        <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
          <div className="text-[#27386d] text-lg">로딩 중...</div>
        </div>
    );
  }

  return (
      <div className="min-h-screen bg-[#e7f8ff]">
        {/* 진행 바 */}
        <div className="bg-white border-b border-gray-100 py-4">
          <div className="w-full px-4">
            <div className="flex items-center justify-between">
              {/* 진행바 영역 */}
              <div className="max-w-5xl mx-auto flex-1">
                {/* 단계 라벨들 */}
                <div className="flex justify-between items-center mb-4 px-2">
                  {steps.map((step, index) => (
                      <div key={index} className="flex flex-col items-center">
                        <div className="text-xs text-gray-600 mb-2 text-center whitespace-nowrap">
                          {step}
                        </div>
                        <div className={`w-3 h-3 rounded-full border-2 ${
                            index <= currentStep
                                ? 'bg-[#27386d] border-[#27386d]'
                                : 'bg-white border-[#d0d0d0]'
                        }`}></div>
                      </div>
                  ))}
                </div>
                {/* 진행 바 */}
                <div className="relative">
                  {/* 배경 바 */}
                  <div className="w-full h-2 bg-[#d0d0d0] rounded-full"></div>
                  {/* 진행된 부분 */}
                  <div
                      className="absolute top-0 left-0 h-2 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${((currentStep) / (steps.length - 1)) * 100}%` }}
                  ></div>
                </div>
                {/* 모바일용 현재 단계 표시 */}
                <div className="mt-4 text-center md:hidden">
                <span className="text-sm text-gray-600">
                  {currentStep + 1} / {steps.length} - {steps[currentStep]}
                </span>
                </div>
              </div>

              {/* 로고 영역 - 화면 맨 오른쪽 */}
              <div className="absolute right-56">
                <Link href="/" className="flex items-center">
                <span className="text-2xl font-bold text-[#27386d]" style={{ fontFamily: 'var(--font-pacifico)' }}>
                  TOOK TAC
                </span>
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨테이너 - 하늘색 배경 적용 */}
        <div className="max-w-6xl mx-auto px-4 py-8">
          {/* 메인 컨텐츠 */}
          <div className="bg-white rounded-2xl p-8 shadow-sm">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-[#27386d] mb-4"
                  style={{ textShadow: '2px 2px 6px rgba(39, 56, 109, 0.3)' }}
              >
                {steps[currentStep]}
              </h1>

              {currentStep === 0 && (
                  <div className="space-y-6">
                    <p className="text-lg text-gray-700 mb-8 whitespace-pre-line">
                      {`안녕하세요, ${userNickname}님! 툭 치듯 가볍게 시작해볼까요?\n`}
                      <span className="font-bold">마음가는 질문을 골라 편하게 답해보세요.</span>
                    </p>

                    {/* 질문 카드 그리드 */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
                      {icebreakerQuestions.map((question, index) => (
                          <div
                              key={index}
                              onClick={() => handleQuestionSelect(question)}
                              className="bg-[#e7f8ff] hover:bg-[#d0f2ff] border border-[#6ce5e8] rounded-3xl p-6 cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 min-h-[140px] flex items-center justify-center text-center group"
                          >
                            <p className="text-[#27386d] font-medium text-sm leading-relaxed group-hover:text-[#1e2852] transition-colors whitespace-pre-line">
                              {question}
                            </p>
                          </div>
                      ))}
                    </div>

                    <div className="bg-[#f8fafc] border border-[#64748b] rounded-lg p-4">
                      <p className="text-[#334155] font-medium">
                        TIP: 진지하게 말하려고 애쓰기보단, 솔직하고 자연스럽게 말하는 게 더 좋아요.
                      </p>
                    </div>
                  </div>
              )}

              {currentStep > 0 && currentStep < 7 && (
                  <div className="space-y-6">
                    <div className="w-20 h-20 bg-[#27386d] rounded-full flex items-center justify-center mx-auto mb-6">
                      <i className="ri-question-line text-3xl text-white"></i>
                    </div>
                    {selectedQuestion && currentStep === 1 ? (
                        <div>
                          <p className="text-lg text-gray-700 mb-6">
                            선택하신 아이스브레이킹 질문입니다
                          </p>
                          <div className="bg-[#e7f8ff] rounded-lg p-6 mb-6">
                            <p className="text-[#27386d] font-medium text-left">
                              {selectedQuestion}
                            </p>
                          </div>
                          <div className="bg-white border-2 border-[#e7f8ff] rounded-lg p-4">
                      <textarea
                          placeholder="답변을 입력해주세요..."
                          className="w-full h-32 p-4 border border-gray-200 rounded-lg resize-none focus:outline-none focus:border-[#6ce5e8] text-gray-700"
                          maxLength={500}
                      ></textarea>
                          </div>
                        </div>
                    ) : (
                        <div>
                          <p className="text-lg text-gray-700 mb-6">
                            {currentStep}번째 질문을 준비 중입니다...
                          </p>
                          <div className="bg-[#e7f8ff] rounded-lg p-6">
                            <p className="text-[#27386d] font-medium text-left">
                              질문 예시: "회사에 지원하게 된 동기는 무엇인가요?"
                            </p>
                          </div>
                        </div>
                    )}
                  </div>
              )}

              {currentStep === 7 && (
                  <div className="space-y-6">
                    <div className="w-20 h-20 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mx-auto mb-6">
                      <i className="ri-medal-line text-3xl text-white"></i>
                    </div>
                    <p className="text-lg text-gray-700 mb-6">
                      수고하셨습니다! 오늘의 면접이 완료되었습니다.<br/>
                      AI가 여러분의 답변을 분석하여 피드백을 준비 중입니다.
                    </p>
                    <div className="bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-lg p-6 text-white">
                      <p className="font-medium">
                        오늘도 한 걸음 더 성장했어요!
                      </p>
                    </div>
                  </div>
              )}
            </div>
          </div>

          {/* 하단 정보 */}
          <div className="mt-8 text-center">
            <p className="text-gray-600 mb-4">매일 12분, 꾸준한 면접 연습으로 자신감을 키워보세요</p>
            <div className="flex justify-center space-x-6 text-sm text-gray-500">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full"></div>
                <span>진행중</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-[#d0d0d0] rounded-full"></div>
                <span>대기</span>
              </div>
            </div>
          </div>
        </div>
      </div>
  );
}
