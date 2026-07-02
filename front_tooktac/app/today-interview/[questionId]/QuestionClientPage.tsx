'use client';

import { useEffect, useState } from 'react';
import QuestionClientLoadingPage from './QuestionClientLoadingPage';
import Link from 'next/link';
import { useSttSocket } from '@/hooks/useSttSocket';
import { useExpressionSocket } from '@/hooks/useExpressionSocket';
import { useSearchParams } from 'next/navigation';

const questionMap: Record<string, string> = {
  '1': '자기소개를 해주세요.',
  '2': '장점과 단점은 무엇인가요?',
  '3': '가장 기억에 남는 경험은?',
  '4': '협업 경험에 대해 말해주세요.',
  '5': '갈등 상황을 어떻게 해결했나요?',
  '6': '지원 동기와 포부를 말해주세요.'
};

type Props = {
  questionId: string;
};

export default function QuestionClientPage({ questionId }: Props) {
  const searchParams = useSearchParams();
  const questionFromParam = searchParams.get('question');
  const question =
    questionFromParam || questionMap[questionId] || '선택한 질문이 없습니다';

  const [prepareTime, setPrepareTime] = useState(30);
  const [answerTime, setAnswerTime] = useState(90);
  const [isPrepareActive, setIsPrepareActive] = useState(true);
  const [isAnswerActive, setIsAnswerActive] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [isGazeActive, setGazeActive] = useState(false);
  const [isPostureActive, setPostureActive] = useState(false);
  const [isHandActive, setHandActive] = useState(false);

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
  const currentStep = Number(questionId);

  useSttSocket({
    isAnswerActive,
    questionId,
    onTranscriptUpdate: () => {},
    onFeedbackUpdate: () => {}
  });

  useExpressionSocket({
    isAnswerActive,
    questionId,
    setGazeActive,
    setPostureActive,
    setHandActive
  });

  useEffect(() => {
    const videoElement = document.getElementById(
      'webcam-video'
    ) as HTMLVideoElement;
    if (!videoElement) return;

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then((stream) => {
        videoElement.srcObject = stream;
      })
      .catch((err) => console.error('웹캠 접근 실패:', err));

    return () => {
      const tracks = (videoElement.srcObject as MediaStream)?.getTracks?.();
      tracks?.forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPrepareActive && prepareTime > 0) {
      interval = setInterval(() => {
        setPrepareTime((prev) => {
          if (prev <= 1) {
            setIsPrepareActive(false);
            setIsAnswerActive(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPrepareActive, prepareTime]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isAnswerActive && answerTime > 0) {
      interval = setInterval(() => {
        setAnswerTime((prev) => {
          if (prev <= 1) {
            setIsAnswerActive(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isAnswerActive, answerTime]);

  const handleStartAnswer = () => {
    setIsAnswerActive(true);
    setIsPrepareActive(false);
    setPrepareTime(0);
  };

  const handleSubmitAnswer = () => {
    setIsAnswerActive(false);
    setAnswerTime(0);
    setIsAnalyzing(true);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs
      .toString()
      .padStart(2, '0')}`;
  };

  if (isAnalyzing) return <QuestionClientLoadingPage questionId={questionId} />;

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      {/* 상단 진행도 표시 */}
      <div className="bg-white border-b border-gray-100 py-4">
        <div className="w-full px-4">
          <div className="flex items-center justify-between">
            <div className="max-w-5xl mx-auto flex-1">
              <div className="flex justify-between items-center mb-4 px-2">
                {steps.map((step, index) => (
                  <div key={index} className="flex flex-col items-center">
                    <div className="text-xs text-gray-600 mb-2 text-center whitespace-nowrap">
                      {step}
                    </div>
                    <div
                      className={`w-3 h-3 rounded-full border-2 ${
                        index <= currentStep
                          ? 'bg-[#27386d] border-[#27386d]'
                          : 'bg-white border-[#d0d0d0]'
                      }`}
                    ></div>
                  </div>
                ))}
              </div>
              <div className="relative">
                <div className="w-full h-2 bg-[#d0d0d0] rounded-full"></div>
                <div
                  className="absolute top-0 left-0 h-2 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
                ></div>
              </div>
              <div className="mt-4 text-center md:hidden">
                <span className="text-sm text-gray-600">
                  {currentStep + 1} / {steps.length} - {steps[currentStep]}
                </span>
              </div>
            </div>

            <div className="absolute right-56">
              <Link href="/" className="flex items-center">
                <span
                  className="text-2xl font-bold text-[#27386d]"
                  style={{ fontFamily: 'var(--font-pacifico)' }}
                >
                  TOOK TAC
                </span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 질문/영상 영역 */}
      <div className="p-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 min-h-[calc(100vh-200px)] items-center">
            {/* 질문 */}
            <div className="flex flex-col justify-center items-center text-center px-8">
              <h1 className="text-2xl font-bold text-[#27386d] mb-16 leading-relaxed max-w-[500px] break-keep">
                {question}
              </h1>
              <div className="flex space-x-4">
                <button
                  onClick={handleStartAnswer}
                  disabled={isAnswerActive}
                  className={`px-8 py-4 rounded-full text-lg font-semibold transition-all duration-300 whitespace-nowrap cursor-pointer ${
                    !isAnswerActive
                      ? 'bg-[#6ce5e8] text-[#27386d] hover:bg-[#6ce5e8]/90 shadow-lg'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  답변하기
                </button>

                {isAnswerActive && (
                  <button
                    onClick={handleSubmitAnswer}
                    className="px-8 py-4 rounded-full text-lg font-semibold bg-[#27386d] text-white hover:bg-[#27386d]/90 shadow-lg transition-all duration-300 whitespace-nowrap cursor-pointer"
                  >
                    답변 제출하기
                  </button>
                )}
              </div>
            </div>

            {/* 웹캠 + 피드백 상태 */}
            <div className="flex flex-col items-center justify-center">
              <div className="relative w-[600px] h-[450px] bg-black rounded-2xl mb-8 flex items-center justify-center">
                <video
                  id="webcam-video"
                  className="absolute w-full h-full object-cover rounded-2xl"
                  autoPlay
                  muted
                  playsInline
                />

                <div className="absolute top-4 right-4 flex space-x-2">
                  <div
                    className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                      isGazeActive
                        ? 'bg-red-500 shadow-lg shadow-red-500/50'
                        : 'bg-gray-600/50'
                    }`}
                  >
                    <i className="ri-eye-off-line text-white text-sm"></i>
                  </div>
                  <div
                    className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                      isPostureActive
                        ? 'bg-green-500 shadow-lg shadow-green-500/50'
                        : 'bg-gray-600/50'
                    }`}
                  >
                    <i className="ri-user-3-line text-white text-sm"></i>
                  </div>
                  <div
                    className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                      isHandActive
                        ? 'bg-orange-400 shadow-lg shadow-orange-400/50'
                        : 'bg-gray-600/50'
                    }`}
                  >
                    <i className="ri-hand text-white text-sm"></i>
                  </div>
                </div>
              </div>

              {/* 타이머 */}
              <div className="bg-white rounded-xl shadow-lg p-4 w-[600px]">
                <div className="grid grid-cols-2 gap-8">
                  <div className="text-center">
                    <div className="text-sm text-[#27386d]/70 mb-1">준비 시간</div>
                    <div
                      className={`text-2xl font-mono font-bold transition-all duration-300 ${
                        isPrepareActive ? 'text-[#6ce5e8]' : 'text-[#27386d]/50'
                      }`}
                    >
                      {formatTime(prepareTime)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-[#27386d]/70 mb-1">답변 시간</div>
                    <div
                      className={`text-2xl font-mono font-bold transition-all duration-300 ${
                        isAnswerActive ? 'text-[#6ce5e8]' : 'text-[#27386d]/50'
                      }`}
                    >
                      {formatTime(answerTime)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            {/* end webcam */}
          </div>
        </div>
      </div>
    </div>
  );
}
