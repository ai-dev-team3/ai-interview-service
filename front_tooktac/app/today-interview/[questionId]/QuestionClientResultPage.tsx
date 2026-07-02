'use client';

import Link from 'next/link';
import { useUser } from "@/contexts/UserContext";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from 'react';

type EvaluationResult = {
    session_id: number;
    question_order: number;
    question: string;
    user_answer: string;
    model_answer: string;
    strengths: string[];
    improvements: string[];
    final_feedback: string;
    labels: {
        speed: string;
        fluency: string;
        tone: string;
    };
    video: {
        gaze_score: number | null;
        shoulder_warning: number | null;
        hand_warning: number | null;
    };
    best_emotion: string | null;
    weighted_score: number;
};

type Props = {
    result: EvaluationResult;
    nextLink: string;
};

export default function QuestionClientResultPage({ result, nextLink }: Props ) {
    const {user} = useUser()
    const userNickname = user?.nickname ?? '사용자';

    const searchParams = useSearchParams()
    const questionFromParam = searchParams.get('question')
    const question = questionFromParam || '자기소개를 해주세요.';
    const questionId = searchParams.get('questionId');
    const isFinalStep = nextLink?.startsWith('/today-interview/final-report');
    let currentStep = 1;
    if (nextLink.includes('/today-interview/')) {
        const match = nextLink.match(/\/today-interview\/(\d+)/);
        if (match) {
            const nextId = parseInt(match[1], 10);
            currentStep = nextId - 1;
        } else if (nextLink.startsWith('/today-interview/final-report')) {
            currentStep = 6;
        }
    }

    // 현재 점수와 감정 상태 (임시 데이터)
    const currentScore = result?.weighted_score ?? 0;
    const currentEmotion = result?.best_emotion ?? "분석중"; // "긍정적", "무표정", "긴장됨", "부정적"

    // 음성 분석 데이터 (임시)
    const voiceAnalysis = {
        speed: result?.labels?.speed ?? '분석중',
        fluency: result?.labels?.fluency ?? '분석중',
        tone: result?.labels?.tone ?? '분석중'
    };

    // 영상 분석 데이터 (임시)
    const videoAnalysis = {
        gazeRate: result.video?.gaze_score ?? 0,
        shoulderWarnings: result.video?.shoulder_warning ?? 0,
        handWarnings: result.video?.hand_warning ?? 0
    };
    const TrafficLight = ({ options, current }: { options: string[], current: string }) => {
        const getColor = (option: string) => {
            if (option !== current) return 'bg-gray-300';

            // 색상 매핑
            if (['적절', '매끄러움', '밝음'].includes(option)) return 'bg-green-500';
            if (['무난', '단조로움'].includes(option)) return 'bg-yellow-500';
            if (['느림', '빠름', '버벅거림'].includes(option)) return 'bg-red-500';
            return 'bg-gray-300';
        };

        return (
            <div className="flex justify-center space-x-1">
                {options.map((option, index) => (
                    <div
                        key={index}
                        className={`w-3 h-3 rounded-full ${getColor(option)}`}
                    />
                ))}
            </div>
        );
    };

    // 속도 게이지 컴포넌트
    const SpeedGauge = ({ value }: { value: string }) => {
        const getAngle = (speed: string) => {
            switch (speed) {
                case '느림': return -60;
                case '적절': return 0;
                case '빠름': return 60;
                default: return 0;
            }
        };

        const getColor = (speed: string) => {
            switch (speed) {
                case '느림': return '#6ce5e8';
                case '적절': return '#6ce5e8';
                case '빠름': return '#6ce5e8';
                default: return '#6ce5e8';
            }
        };

        const angle = getAngle(value);
        const color = getColor(value);

        return (
            <div className="flex flex-col items-center h-16">
                <svg width="70" height="40" viewBox="0 0 70 40">
                    {/* 배경 반원 */}
                    <path
                        d="M 10 35 A 25 25 0 0 1 60 35"
                        stroke="#e5e7eb"
                        strokeWidth="3"
                        fill="none"
                    />
                    {/* 진행 반원 */}
                    <path
                        d="M 10 35 A 25 25 0 0 1 60 35"
                        stroke={color}
                        strokeWidth="3"
                        fill="none"
                        strokeDasharray="78.5"
                        strokeDashoffset={angle < 0 ? 39.25 + (angle * 0.65) : 39.25 - (angle * 0.65)}
                    />
                    {/* 바늘 */}
                    <line
                        x1="35"
                        y1="35"
                        x2="35"
                        y2="15"
                        stroke={color}
                        strokeWidth="2"
                        transform={`rotate(${angle} 35 35)`}
                    />
                    {/* 중심점 */}
                    <circle cx="35" cy="35" r="2" fill={color} />
                </svg>
            </div>
        );
    };

    // 유창성 파형 컴포넌트
    const FluencyWave = ({ value }: { value: string }) => {
        const getPath = (fluency: string) => {
            switch (fluency) {
                case '버벅거림': return 'M5,25 L15,15 L25,25 L35,15 L45,25 L55,15 L65,25';
                case '무난': return 'M5,25 Q20,15 35,20 Q50,25 65,18';
                case '매끄러움': return 'M5,22 Q20,12 35,18 Q50,24 65,15';
                default: return 'M5,20 L65,20';
            }
        };

        const getColor = (fluency: string) => {
            switch (fluency) {
                case '버벅거림': return '#6ce5e8';
                case '무난': return '#6ce5e8';
                case '매끄러움': return '#6ce5e8';
                default: return '#6ce5e8';
            }
        };

        return (
            <div className="flex flex-col items-center h-16 justify-center">
                <svg width="70" height="40" viewBox="0 0 70 40">
                    <path
                        d={getPath(value)}
                        stroke={getColor(value)}
                        strokeWidth="3"
                        fill="none"
                        strokeLinecap="round"
                    />
                </svg>
            </div>
        );
    };

    // 음조 파형 컴포넌트
    const ToneWave = ({ value }: { value: string }) => {
        const getBars = (tone: string) => {
            if (tone === '단조로움') {
                return [18, 20, 19, 21, 18, 20, 19];
            } else {
                return [12, 25, 15, 30, 18, 28, 22];
            }
        };

        const getColor = (tone: string) => {
            return '#6ce5e8';
        };

        const bars = getBars(value);
        const color = getColor(value);

        return (
            <div className="flex flex-col items-center h-16 justify-center">
                <svg width="70" height="40" viewBox="0 0 70 40">
                    {bars.map((height, index) => (
                        <rect
                            key={index}
                            x={index * 10 + 5}
                            y={40 - height}
                            width="6"
                            height={height}
                            fill={color}
                            rx="1"
                        />
                    ))}
                </svg>
            </div>
        );
    };

    // 점수별 메시지 함수
    const getScoreMessage = (score: number) => {
        if (score === 100) return "면접관도 감탄할만큼 완벽한 응답이네요!";
        if (score >= 90) return "완벽에 가까운 훌륭한 답변입니다!";
        if (score >= 70) return "우수한 답변이에요! 약간만 다듬으면 더 좋아질 수 있어요.";
        if (score >= 50) return "매일 연습하면 더좋은 답변을 할 수 있어요!";
        return "시작이 반이에요. 한걸음씩 함께 노력해요!";
    };

    // 감정별 아이콘과 메시지 함수
    const getEmotionData = (emotion: string) => {
        switch (emotion) {
            case "긍정":
                return {
                    icon: "ri-emotion-happy-line",
                    message: "자신감 있고 긍정적인 표정이네요!"
                };
            case "중립":
                return {
                    icon: "ri-emotion-normal-line",
                    message: "표정에 생기를 넣어볼까요?"
                };
            case "긴장":
                return {
                    icon: "ri-emotion-sad-line",
                    message: "조금 더 편하게 답변해도 괜찮아요."
                };
            case "부정":
                return {
                    icon: "ri-emotion-unhappy-line",
                    message: "다음 질문에는 웃으며 답변해주세요!"
                };
            default:
                return {
                    icon: "ri-emotion-normal-line",
                    message: "감정을 분석중입니다."
                };
        }
    };

    // 단계 정의
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
    useEffect(() => {
    }, []);
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

            <div className="max-w-6xl mx-auto px-6 py-8">
                {/* 분석 결과 헤더 */}
                <div className="text-center mb-8">
                    <div
                        className="w-20 h-20 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mx-auto mb-6">
                        <i className="ri-check-line text-3xl text-white"></i>
                    </div>
                    <h1 className="text-3xl font-bold text-[#27386d] mb-4">
                        {userNickname}님의 답변 분석 결과
                    </h1>
                    <p className="text-lg text-[#27386d]/70">
                        AI가 분석한 상세한 피드백을 확인해보세요
                    </p>
                </div>

                {/* 질문과 답변 섹션 */}
                <div className="bg-white rounded-2xl p-6 mb-8 shadow-sm">
                    <h3 className="text-lg font-semibold text-[#27386d] mb-6">내 답변과 모범답안</h3>

                    {/* 질문 */}
                    <div className="mb-6">
                        <div className="flex items-start space-x-3 mb-3">
                            <div
                                className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center flex-shrink-0">
                                <i className="ri-question-line text-lg text-[#27386d]"></i>
                            </div>
                            <div className="flex-1">
                                <h4 className="text-sm font-medium text-[#27386d]/70 mb-2">질문</h4>
                                <div className="bg-[#e7f8ff] rounded-xl p-4">
                                    <p className="text-[#27386d] font-medium">{question}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    {/* 나의 답변 */}
                    <div className="mb-6">
                        <div className="flex items-start space-x-3">
                            <div
                                className="w-8 h-8 bg-[#27386d] rounded-full flex items-center justify-center flex-shrink-0">
                                <i className="ri-user-line text-lg text-white"></i>
                            </div>
                            <div className="flex-1">
                                <h4 className="text-sm font-medium text-[#27386d]/70 mb-2">나의 답변</h4>
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                    <p className="text-[#27386d] leading-relaxed">
                                        {result?.user_answer.trim()
                                            ? result?.user_answer
                                            : "답변을 불러올 수 없습니다."}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    {/* ai 모범답변 */}
                    <div className="mb-4">
                        <div className="flex items-start space-x-3">
                            <div
                                className="w-8 h-8 bg-[#27386d] rounded-full flex items-center justify-center flex-shrink-0">
                                <i className="ri-mic-line text-lg text-white"></i>
                            </div>
                            <div className="flex-1">
                                <h4 className="text-sm font-medium text-[#27386d]/70 mb-2">AI가 생성한 모범답안</h4>
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                    <p className="text-gray-800 leading-relaxed">
                                        {result?.model_answer.trim()
                                            ? result?.model_answer
                                            : "AI 모범답안을 불러올 수 없습니다."}
                                    </p>
                                </div>
                                <div className="mt-3 text-sm text-[#27386d]/70 bg-[#e7f8ff] rounded-lg p-3">
                                    <p>모범답안은 답변의 구조와 흐름을 익히는데 도움이 됩니다. 나만의 진심을 더해보세요!</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 분석 결과 카드들 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    {/* 전체 점수 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">전체 점수</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-star-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-bold text-[#27386d] mb-2">{currentScore}/100</div>
                            <div className="text-sm text-gray-600">{getScoreMessage(currentScore)}</div>
                        </div>
                    </div>

                    {/* 감정 분석 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">감정 분석</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-emotion-happy-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="text-center">
                            <div
                                className="text-2xl font-bold text-[#27386d] mb-2 flex items-center justify-center space-x-2">
                                <i className={`${getEmotionData(currentEmotion).icon} text-[#6ce5e8] text-3xl`}></i>
                                <span>{currentEmotion}</span>
                            </div>
                            <div className="text-sm text-gray-600">{getEmotionData(currentEmotion).message}</div>
                        </div>
                    </div>

                    {/* 음성 분석 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">음성 분석</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-mic-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                            {/* 속도 */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">속도</div>
                                <SpeedGauge value={voiceAnalysis.speed}/>
                                <div className="text-sm font-medium text-[#27386d] mt-2">{voiceAnalysis.speed}</div>
                            </div>

                            {/* 유창성 */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">유창성</div>
                                <FluencyWave value={voiceAnalysis.fluency}/>
                                <div className="text-sm font-medium text-[#27386d] mt-2">{voiceAnalysis.fluency}</div>
                            </div>

                            {/* 음조 */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">음조</div>
                                <ToneWave value={voiceAnalysis.tone}/>
                                <div className="text-sm font-medium text-[#27386d] mt-2">{voiceAnalysis.tone}</div>
                            </div>
                        </div>
                    </div>

                    {/* 영상 분석 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">영상 분석</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-eye-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                            {/* 화면응시율 */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">화면응시율</div>
                                <div className="relative w-16 h-16 mx-auto mb-2">
                                    <svg className="w-16 h-16 transform -rotate-90">
                                        <circle
                                            cx="32"
                                            cy="32"
                                            r="28"
                                            stroke="#e5e7eb"
                                            strokeWidth="4"
                                            fill="none"
                                        />
                                        <circle
                                            cx="32"
                                            cy="32"
                                            r="28"
                                            stroke="#6ce5e8"
                                            strokeWidth="4"
                                            fill="none"
                                            strokeDasharray={`${2 * Math.PI * 28 * (videoAnalysis.gazeRate / 100)} ${2 * Math.PI * 28}`}
                                            strokeLinecap="round"
                                        />
                                    </svg>
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <span
                                            className="text-lg font-bold text-[#27386d]">{videoAnalysis.gazeRate}</span>
                                    </div>
                                </div>
                                <div className="text-xs text-gray-600">%</div>
                            </div>

                            {/* 자세경고(어깨) */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">자세경고(어깨)</div>
                                <div className="flex flex-col items-center">
                                    <i className="ri-user-3-line text-2xl text-[#27386d] mb-1"></i>
                                    <div
                                        className="text-2xl font-bold text-[#27386d]">{videoAnalysis.shoulderWarnings}</div>
                                    <div className="text-xs text-gray-600">회</div>
                                </div>
                            </div>

                            {/* 자세경고(손) */}
                            <div className="text-center">
                                <div className="text-xs text-gray-600 mb-2">자세경고(손)</div>
                                <div className="flex flex-col items-center">
                                    <i className="ri-hand text-2xl text-[#27386d] mb-1"></i>
                                    <div
                                        className="text-2xl font-bold text-[#27386d]">{videoAnalysis.handWarnings}</div>
                                    <div className="text-xs text-gray-600">회</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 강점, 개선점, 한줄 피드백 섹션 */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    {/* 강점 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">강점</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-thumb-up-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="space-y-3">
                            {(result?.strengths && result?.strengths.length > 0
                                    ? result?.strengths
                                    : ["자연스럽고 진정성 있는 답변", "높은 화면 응시율"]
                            ).map((strength, index) => (
                                <div key={index} className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-[#6ce5e8] rounded-full mt-2 flex-shrink-0"></div>
                                    <p className="text-sm text-gray-700">{strength}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 개선점 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-[#27386d]">개선점</h3>
                            <div className="w-8 h-8 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                                <i className="ri-lightbulb-line text-lg text-[#27386d]"></i>
                            </div>
                        </div>
                        <div className="space-y-3">
                            {(result?.improvements && result?.improvements.length > 0
                                    ? result?.improvements
                                    : ["좀 더 구체적인 예시 추가", "답변 구조화 연습"]
                            ).map((improvement, index) => (
                                <div key={index} className="flex items-start space-x-2">
                                    <div className="w-2 h-2 bg-[#6ce5e8] rounded-full mt-2 flex-shrink-0"></div>
                                    <p className="text-sm text-gray-700">{improvement}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 피드백 */}
                    <div className="bg-[#27386d] rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-white">피드백</h3>
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                                <i className="ri-chat-quote-line text-lg text-white"></i>
                            </div>
                        </div>
                        <div className="text-center">
                            <p className="text-lg font-medium leading-relaxed text-white">
                                {result?.final_feedback || "자연스럽고 진실한 답변이에요! 조금 더 구체적인 경험을 추가하면 완벽할 것 같아요."}
                            </p>
                        </div>
                    </div>
                </div>

                {/* 하단 버튼들 */}
                <div className="flex justify-center">
                    {isFinalStep ? (
                        <Link
                            href={nextLink}
                            className="px-8 py-4 bg-[#6ce5e8] text-white rounded-full font-semibold hover:bg-[#6ce5e8]/90 transition-colors cursor-pointer whitespace-nowrap"
                        >
                            최종 리포트 받아보기
                        </Link>
                    ) : (
                        <Link
                            href={`/today-interview/make-question?next=${encodeURIComponent(nextLink)}`}
                            className="px-8 py-4 bg-[#6ce5e8] text-white rounded-full font-semibold hover:bg-[#6ce5e8]/90 transition-colors cursor-pointer whitespace-nowrap"
                        >
                            다음 질문으로 이동
                        </Link>
                    )}
                </div>
            </div>
        </div>
    );
}