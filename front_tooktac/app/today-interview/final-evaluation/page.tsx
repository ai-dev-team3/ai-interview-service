'use client';

import { useEffect, useState } from 'react';
import { useUser } from "@/contexts/UserContext";
import { fetchFinalReport } from '@/api/api';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip
} from 'recharts';
import Link from "next/link";

export type QuestionScore = {
  name: string;
  score: number;
  type: string;
  question: string;
  myAnswer: string;
  modelAnswer: string;
  summary: string;
};

export type FinalReportResponse = {
  evaluationData: {
    totalScore: number;
    rank: string;
    grade: string;
    gradeMessage: string;
    areaScores: {
      text: { total: number; similarity: number; accuracy: number; understanding: number };
      voice: { total: number; speed: number; fluency: number; tone: number };
      video: { total: number; gaze_rate: number; posture: number };
      emotion: { total: number; positive: number; neutral: number; nervous: number; negative: number };
    };
    questionScores: {
      name: string;
      score: number;
      type: string;
      question: string;
      myAnswer: string;
      modelAnswer: string;
      summary: string;
    }[];
  };
  aiAdvice: {
    personalizedMessage: string;
    topStrengths: {
      title: string;
      description: string;
      score: number;
    }[];
    improvements: {
      priority: number;
      title: string;
      description: string;
      score: number;
    }[];
  };
};

export default function FinalEvaluationPage() {
  const {user} = useUser();
  const userNickname = user?.nickname ?? '사용자';
  const handleQuestionClick = (question: QuestionScore) => {
    setSelectedQuestion(question);
    setModalOpen(true);
  };
  const [report, setReport] = useState<FinalReportResponse | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<FinalReportResponse['evaluationData']['questionScores'][0] | null>(null);

  const steps = ['아이스브레이킹', '질문 1', '질문 2', '질문 3', '질문 4', '질문 5', '질문 6', '최종 평가'];
  const currentStep = steps.length - 1;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetchFinalReport();
        setReport(res);
      } catch (err) {
        console.error("최종 리포트 로딩 실패:", err);
      }
    };
    fetchData();
  }, []);

  if (!report) {
    return (
        <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
          <div className="text-[#27386d] text-xl">최종 리포트를 불러오는 중입니다...</div>
        </div>
    );
  }

  const { evaluationData, aiAdvice } = report;
  const radarData = [
    { subject: '답변 내용', score: evaluationData.areaScores.text.total, fullMark: 100 },
    { subject: '음성', score: evaluationData.areaScores.voice.total, fullMark: 100 },
    { subject: '영상', score: evaluationData.areaScores.video.total, fullMark: 100 },
    { subject: '감정', score: evaluationData.areaScores.emotion.total, fullMark: 100 },
  ];

  const getGradeMessage = (score: number) => {
    if (score >= 95) return "S등급 - 면접관도 감탄할만큼 완벽한 응답이네요!";
    if (score >= 90) return "A+등급 - 완벽에 가까운 훌륭한 답변입니다!";
    if (score >= 85) return "A등급 - 우수한 답변이에요! 약간만 다듬으면 더 좋아질 수 있어요.";
    if (score >= 80) return "B+등급 - 매일 연습하면 더좋은 답변을 할 수 있어요!";
    if (score >= 75) return "B등급 - 기본기는 탄탄해요! 조금 더 연습해보세요.";
    if (score >= 70) return "C+등급 - 시작이 반이에요. 한걸음씩 함께 노력해요!";
    return "C등급 - 꾸준한 연습으로 실력을 키워나가세요!";
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedQuestion(null);
  };

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
          {/* 최종 평가 헤더 */}
          <div className="text-center mb-12">
            <div className="w-24 h-24 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mx-auto mb-8">
              <i className="ri-trophy-line text-4xl text-white"></i>
            </div>
            <h1 className="text-4xl font-bold text-[#27386d] mb-6">
              🎉 {userNickname}님, 수고하셨습니다!
            </h1>
            <p className="text-xl text-[#27386d]/70 mb-4">
              오늘의 면접이 완료되었습니다
            </p>
            <p className="text-lg text-gray-600">
              AI가 분석한 종합 평가 결과를 확인해보세요
            </p>
          </div>

          {/* 총 점수 및 등급 */}
          <div className="bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-3xl p-8 mb-8 text-white">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-6">종합 점수</h2>
              <div className="text-8xl font-bold mb-4">{evaluationData.totalScore}</div>
              <div className="text-2xl font-semibold mb-6">/ 100점</div>
              <div className="bg-white/20 rounded-2xl px-8 py-4 inline-block">
                <div className="text-xl font-semibold">{evaluationData.rank} 달성!</div>
              </div>
              <div className="mt-4 text-lg">
                {getGradeMessage(evaluationData.totalScore)}
              </div>
            </div>
          </div>

          {/* 4영역 레이더 차트 + AI 조언 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* 4영역 레이더 차트 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm">
              <h3 className="text-2xl font-bold text-[#27386d] mb-8 text-center">4영역 역량 분석</h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 14, fill: '#27386d' }} />
                    <Radar
                        name="점수"
                        dataKey="score"
                        stroke="#27386d"
                        fill="#6ce5e8"
                        fillOpacity={0.3}
                        strokeWidth={3}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 개인 맞춤 조언 - 하얀색 배경으로 변경 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm">
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-[#27386d] rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className="ri-user-star-line text-2xl text-white"></i>
                </div>
                <h3 className="text-2xl font-bold text-[#27386d]">{userNickname}님만을 위한 AI 조언</h3>
              </div>
              <div className="bg-[#f8fafc] rounded-xl p-6">
                <p className="text-lg text-gray-800 leading-relaxed">
                  {report?.aiAdvice?.personalizedMessage}
                </p>
              </div>
            </div>
          </div>

          {/* 종합 피드백 - 위치 이동 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* TOP 3 강점 */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex items-center mb-6">
                <div className="w-12 h-12 bg-[#6ce5e8] rounded-full flex items-center justify-center mr-4">
                  <i className="ri-thumb-up-line text-2xl text-[#27386d]"></i>
                </div>
                <h3 className="text-xl font-semibold text-[#27386d]">TOP 3 강점</h3>
              </div>

              <div className="space-y-4">
                {report?.aiAdvice?.topStrengths?.map((strength, index) => (
                    <div key={index} className="flex items-start space-x-3">
                      <div className="w-6 h-6 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">
                        {index + 1}
                      </div>
                      <div>
                        <h4 className="font-semibold text-gray-800 mb-1">
                          {strength.title} ({strength.score}점)
                        </h4>
                        <p className="text-sm text-gray-600">{strength.description}</p>
                      </div>
                    </div>
                ))}
              </div>
            </div>

            {/* 우선순위별 개선점 */}
            {/* 우선순위별 개선점 */}
            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <div className="flex items-center mb-6">
                <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mr-4">
                  <i className="ri-lightbulb-line text-2xl text-orange-500"></i>
                </div>
                <h3 className="text-xl font-semibold text-[#27386d]">우선순위별 개선점</h3>
              </div>

              <div className="space-y-4">
                {report?.aiAdvice?.improvements?.map((item, index) => (
                    <div key={index} className="flex items-start space-x-3">
                      <div className="w-6 h-6 bg-orange-400 rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">
                        {item.priority}
                      </div>
                      <div>
                        <h4 className="font-semibold text-gray-800 mb-1">
                          {item.title} ({item.score}점)
                        </h4>
                        <p className="text-sm text-gray-600">{item.description}</p>
                      </div>
                    </div>
                ))}
              </div>
            </div>
          </div>

          {/* 영역별 상세 점수 */}
          <div className="bg-white rounded-2xl p-8 mb-8 shadow-sm">
            <h3 className="text-2xl font-bold text-[#27386d] mb-8 text-center">영역별 상세 분석</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

              {/* 답변 내용 분석 */}
              <div className="border border-gray-200 rounded-xl p-6">
                <div className="flex items-center mb-6">
                  <div className="w-12 h-12 bg-[#e7f8ff] rounded-full flex items-center justify-center mr-4">
                    <i className="ri-chat-3-line text-2xl text-[#27386d]"></i>
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold text-[#27386d]">답변 내용</h4>
                    <div className="text-3xl font-bold text-[#27386d]">{evaluationData.areaScores.text.total}점</div>
                  </div>
                </div>
                <div className="min-h-[180px] flex flex-col justify-center space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">모범답안 유사도</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.similarity * 10}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.similarity * 10}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">지식 정확도</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.accuracy * 10}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.accuracy * 10}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">질문의도 파악</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.understanding * 10}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.understanding * 10}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 음성 */}
              <div className="border border-gray-200 rounded-xl p-6">
                <div className="flex items-center mb-6">
                  <div className="w-12 h-12 bg-[#e7f8ff] rounded-full flex items-center justify-center mr-4">
                    <i className="ri-mic-line text-2xl text-[#27386d]"></i>
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold text-[#27386d]">음성</h4>
                    <div className="text-3xl font-bold text-[#27386d]">{evaluationData.areaScores.voice.total}점</div>
                  </div>
                </div>
                <div className="min-h-[180px] flex flex-col justify-center space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">발화 속도</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.voice.speed}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">적절</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">유창성</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.voice.fluency}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right whitespace-pre-line">매끄
                        러움</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">음성 톤</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.voice.tone}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">밝음</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 영상 */}
              <div className="border border-gray-200 rounded-xl p-6">
                <div className="flex items-center mb-6">
                  <div className="w-12 h-12 bg-[#e7f8ff] rounded-full flex items-center justify-center mr-4">
                    <i className="ri-eye-line text-2xl text-[#27386d]"></i>
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold text-[#27386d]">영상</h4>
                    <div className="text-3xl font-bold text-[#27386d]">{evaluationData.areaScores.video.total}점</div>
                  </div>
                </div>
                <div className="min-h-[180px] flex flex-col justify-center space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">화면 응시율</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.video.gaze_rate}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.video.gaze_rate}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">자세 안정성</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.video.posture}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.video.posture}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 감정 */}
              <div className="border border-gray-200 rounded-xl p-6">
                <div className="flex items-center mb-6">
                  <div className="w-12 h-12 bg-[#e7f8ff] rounded-full flex items-center justify-center mr-4">
                    <i className="ri-emotion-happy-line text-2xl text-[#27386d]"></i>
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold text-[#27386d]">감정</h4>
                    <div className="text-3xl font-bold text-[#27386d]">{evaluationData.areaScores.emotion.total}점</div>
                  </div>
                </div>
                <div className="min-h-[180px] flex flex-col justify-center space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">긍정적</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.emotion.positive}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.emotion.positive}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">무표정</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.emotion.neutral}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.emotion.neutral}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">긴장감</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.emotion.nervous}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.emotion.nervous}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 w-24">부정적</span>
                    <div className="flex items-center flex-1 justify-end">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                        <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.emotion.negative}%`}}></div>
                      </div>
                      <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.emotion.negative}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 질문별 점수 추이 */}
          <div className="bg-white rounded-2xl p-8 mb-8 shadow-sm">
            <h3 className="text-2xl font-bold text-[#27386d] mb-8 text-center">질문별 점수 추이</h3>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={evaluationData.questionScores} margin={{ left: 30, right: 30, top: 20, bottom: 20 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[70, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#27386d"
                      strokeWidth={3}
                      dot={{ fill: '#6ce5e8', strokeWidth: 2, r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 질문별 상세 리뷰 - 바 그래프 제거하고 한줄평으로 대체 */}
          <div className="bg-white rounded-2xl p-8 mb-8 shadow-sm">
            <h3 className="text-2xl font-bold text-[#27386d] mb-8 text-center">질문별 상세 리뷰</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {evaluationData.questionScores.map((question, index) => (
                  <div
                      key={index}
                      className="bg-[#f8fafc] rounded-xl p-4 border border-gray-200 cursor-pointer hover:bg-[#f1f5f9] transition-colors"
                      onClick={() => handleQuestionClick(question)}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-[#27386d]">{question.name}</h4>
                      <span className="text-xs bg-[#6ce5e8] text-[#27386d] px-2 py-1 rounded-full">
                    {question.type}
                  </span>
                    </div>
                    <div className="text-3xl font-bold text-[#27386d] mb-3">{question.score}점</div>
                    <p className="text-sm text-gray-600">
                      {question.summary}
                    </p>
                  </div>
              ))}
            </div>
          </div>

          {/* 하단 액션 버튼 - 버튼 변경 */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
                href="/mypage"
                className="px-8 py-4 bg-[#27386d] text-white rounded-full font-semibold hover:bg-[#27386d]/90 transition-colors cursor-pointer whitespace-nowrap"
            >
              마이페이지
            </Link>
            <Link
                href="/"
                className="px-8 py-4 bg-white text-[#27386d] border-2 border-[#27386d] rounded-full font-semibold hover:bg-[#27386d]/10 transition-colors cursor-pointer whitespace-nowrap"
            >
              면접 끝내기
            </Link>
          </div>

          {/* 격려 메시지 */}
          <div className="text-center mt-12">
            <div className="bg-gradient-to-r from-[#6ce5e8]/20 to-[#27386d]/20 rounded-2xl p-8">
              <h3 className="text-2xl font-bold text-[#27386d] mb-4">
                🌟 면접 연습을 완료하셨습니다!
              </h3>
              <p className="text-lg text-gray-700 mb-4">
                매일 12분씩 꾸준한 연습으로 면접 실력을 키워보세요
              </p>
              <p className="text-gray-600">
                내일도 더 나은 모습으로 만나요! 💪
              </p>
            </div>
          </div>
        </div>

        {/* 질문 상세 모달 */}
        {modalOpen && selectedQuestion && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
                {/* 모달 헤더 */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center">
                      <i className="ri-question-line text-2xl text-white"></i>
                    </div>
                    <div className="flex items-center space-x-3">
                      <h3 className="text-2xl font-bold text-[#27386d]">{selectedQuestion.name}</h3>
                      <span className="text-sm bg-[#6ce5e8] text-[#27386d] px-3 py-1 rounded-full">
                    {selectedQuestion.type}
                  </span>
                    </div>
                  </div>
                  <button
                      onClick={closeModal}
                      className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
                  >
                    <i className="ri-close-line text-xl text-gray-600"></i>
                  </button>
                </div>

                {/* 모달 내용 */}
                <div className="p-6 space-y-6">
                  {/* 질문 */}
                  <div className="bg-[#f8fafc] rounded-xl p-6 border border-[#6ce5e8]/30">
                    <h4 className="text-lg font-semibold text-[#27386d] mb-3 flex items-center">
                      <i className="ri-questionnaire-line mr-2"></i>
                      면접 질문
                    </h4>
                    <p className="text-gray-800 leading-relaxed">
                      {selectedQuestion.question}
                    </p>
                  </div>

                  {/* 내 답안 */}
                  <div className="bg-gradient-to-br from-[#e7f8ff] to-[#f0f9ff] rounded-xl p-6 border border-[#6ce5e8]/50">
                    <h4 className="text-lg font-semibold text-[#27386d] mb-3 flex items-center">
                      <i className="ri-user-voice-line mr-2"></i>
                      내 답안
                    </h4>
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-gray-800 leading-relaxed">
                        {selectedQuestion.myAnswer}
                      </p>
                    </div>
                  </div>

                  {/* 모범답안 */}
                  <div className="bg-gradient-to-br from-[#f0fdf4] to-[#f7fee7] rounded-xl p-6 border border-green-200">
                    <h4 className="text-lg font-semibold text-[#27386d] mb-3 flex items-center">
                      <i className="ri-medal-line mr-2"></i>
                      모범답안
                    </h4>
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-gray-800 leading-relaxed">
                        {selectedQuestion.modelAnswer}
                      </p>
                    </div>
                  </div>

                  {/* 점수 정보 */}
                  <div className="bg-gradient-to-r from-[#6ce5e8]/10 to-[#27386d]/10 rounded-xl p-6 border border-[#27386d]/20">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-[#27386d] rounded-full flex items-center justify-center">
                          <i className="ri-bar-chart-line text-white"></i>
                        </div>
                        <div>
                          <h4 className="text-lg font-semibold text-[#27386d]">평가 점수</h4>
                          <p className="text-sm text-gray-600">AI 종합 분석 결과</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-4xl font-bold text-[#27386d]">{selectedQuestion.score}점</div>
                        <div className="text-sm text-gray-600">/ 100점</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        )}
      </div>
  );
}
