'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import Link from 'next/link';
import QuestionClientLoadingPage from "@/today-interview/[questionId]/QuestionClientLoadingPage";
import Page from "@/today-interview/make-question/page";
import { useExpressionSocket } from "@/hooks/useExpressionSocket";

function AnswerPageContent() {
  const searchParams = useSearchParams();
  const question = searchParams?.get('question') || '선택한 질문이 없습니다';

  const [prepareTime, setPrepareTime] = useState(30);
  const [answerTime, setAnswerTime] = useState(90);
  const [isPrepareActive, setIsPrepareActive] = useState(true);
  const [isAnswerActive, setIsAnswerActive] = useState(false);

  const [isGazeActive, setGazeActive] = useState(false);
  const [isPostureActive, setPostureActive] = useState(false);
  const [isHandActive, setHandActive] = useState(false);

  const router = useRouter();

  useExpressionSocket({
    isAnswerActive,
    questionId: "0",
    setGazeActive,
    setPostureActive,
    setHandActive
  });

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

  useEffect(() => {
    const videoElement = document.getElementById("webcam-video") as HTMLVideoElement;
    if (!videoElement) return;

    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then((stream) => {
          videoElement.srcObject = stream;
        })
        .catch((err) => {
          console.error("웹캠 접근 실패:", err);
        });

    return () => {
      const tracks = (videoElement.srcObject as MediaStream)?.getTracks?.();
      tracks?.forEach((track) => track.stop());
    };
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStartAnswer = () => {
    setIsAnswerActive(true);
    setIsPrepareActive(false);
    setPrepareTime(0);
  };

  const handleSubmitAnswer = () => {
    setIsAnswerActive(false);
    setAnswerTime(0);
    router.push(`/today-interview/make-question?next=/today-interview/1`);
  };

  return (
      <div className="min-h-screen bg-[#e7f8ff]">
        <div className="p-6">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 min-h-[calc(100vh-200px)] items-center">
              <div className="flex flex-col justify-center items-center text-center px-8">
                <h1 className="text-4xl font-bold text-[#27386d] mb-16 leading-relaxed max-w-[500px]">
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
                        면접 시작하기
                      </button>
                  )}
                </div>
              </div>

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
                    <div className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                        isGazeActive ? 'bg-red-500 shadow-lg shadow-red-500/50' : 'bg-gray-600/50'
                    }`}>
                      <i className="ri-eye-off-line text-white text-sm"></i>
                    </div>
                    <div className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                        isPostureActive ? 'bg-green-500 shadow-lg shadow-green-500/50' : 'bg-gray-600/50'
                    }`}>
                      <i className="ri-user-3-line text-white text-sm"></i>
                    </div>
                    <div className={`w-10 h-10 rounded-full border-2 border-white/30 flex items-center justify-center transition-all duration-300 ${
                        isHandActive ? 'bg-orange-400 shadow-lg shadow-orange-400/50' : 'bg-gray-600/50'
                    }`}>
                      <i className="ri-hand text-white text-sm"></i>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-lg p-4 w-[600px]">
                  <div className="grid grid-cols-2 gap-8">
                    <div className="text-center">
                      <div className="text-sm text-[#27386d]/70 mb-1">준비 시간</div>
                      <div className={`text-2xl font-mono font-bold transition-all duration-300 ${isPrepareActive ? 'text-[#6ce5e8]' : 'text-[#27386d]/50'}`}>{formatTime(prepareTime)}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-[#27386d]/70 mb-1">답변 시간</div>
                      <div className={`text-2xl font-mono font-bold transition-all duration-300 ${isAnswerActive ? 'text-[#6ce5e8]' : 'text-[#27386d]/50'}`}>{formatTime(answerTime)}</div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
  );
}

export default function AnswerPage() {
  return (
      <Suspense
          fallback={
            <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
              <div className="text-[#27386d] text-xl">로딩 중...</div>
            </div>
          }
      >
        <AnswerPageContent />
      </Suspense>
  );
}
