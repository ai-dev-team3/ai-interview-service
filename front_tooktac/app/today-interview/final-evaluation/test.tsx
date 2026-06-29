'use client';

import { useState, useEffect } from 'react';
import { Suspense } from 'react';
import Link from 'next/link';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

function FinalEvaluationPageContent() {
    const [isAnalyzing, setIsAnalyzing] = useState(true);
    const [analysisComplete, setAnalysisComplete] = useState(false);
    const [modalOpen, setModalOpen] = useState(false);

    type QuestionScore = {
        name: string;
        score: number;
        type: string;
        question: string;
        myAnswer: string;
        modelAnswer: string;
    };

    const [selectedQuestion, setSelectedQuestion] = useState<QuestionScore | null>(null);

    // 사용자 닉네임 (임시)
    const userNickname = "김면접";

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

    const currentStep = 7; // 최종 평가 단계

    // 평가 데이터
    const evaluationData = {
        totalScore: 89,
        rank: "상위 15%",
        areaScores: {
            text: { total: 92, similarity: 85, accuracy: 92, understanding: 88 },
            voice: { total: 87, speed: 85, fluency: 90, tone: 86 },
            video: { total: 85, gazeRate: 92, posture: 91, focus: 78 },
            emotion: { total: 91, positive: 65, neutral: 25, nervous: 8, negative: 2 }
        },
        questionScores: [
            {
                name: '질문 1',
                score: 88,
                type: '개념설명형',
                question: '프로젝트 관리에서 가장 중요하다고 생각하는 요소는 무엇인가요?',
                myAnswer: '프로젝트 관리에서 가장 중요한 요소는 명확한 목표 설정과 팀원 간의 소통이라고 생각합니다. 먼저 프로젝트의 목적과 범위를 명확히 정의하고, 각 팀원의 역할과 책임을 분명히 해야 합니다. 또한 정기적인 회의와 진행상황 공유를 통해 문제점을 조기에 발견하고 해결할 수 있도록 해야 한다고 봅니다.',
                modelAnswer: '프로젝트 관리의 핵심 요소는 크게 세 가지로 나눌 수 있습니다. 첫째, 명확한 목표와 범위 설정입니다. 프로젝트의 목적, 산출물, 일정, 예산을 구체적으로 정의해야 합니다. 둘째, 효과적인 커뮤니케이션입니다. 이해관계자들과의 지속적인 소통과 정보 공유가 필수적입니다. 셋째, 위험 관리입니다. 잠재적 위험을 사전에 식별하고 대응 계획을 수립하여 프로젝트의 성공 가능성을 높여야 합니다.'
            },
            {
                name: '질문 2',
                score: 91,
                type: '기술형',
                question: '최근 배운 기술이나 도구 중에서 가장 인상 깊었던 것은 무엇인가요?',
                myAnswer: '최근에 배운 React의 Custom Hook이 가장 인상 깊었습니다. 기존에 컴포넌트마다 반복되는 로직을 발견했는데, Custom Hook을 만들어서 재사용 가능한 로직으로 분리할 수 있었습니다. 특히 API 호출과 로딩 상태 관리를 하는 useApi Hook을 만들어서 여러 컴포넌트에서 활용했더니 코드의 가독성과 유지보수성이 크게 향상되었습니다.',
                modelAnswer: '새로운 기술을 학습할 때는 그 기술이 해결하고자 하는 문제와 기존 방식 대비 장점을 명확히 이해하는 것이 중요합니다. 학습한 기술을 실제 프로젝트에 적용해보고, 그 과정에서 발생한 문제점과 해결 방법을 정리하는 것이 좋습니다. 또한 해당 기술의 한계점도 파악하여 언제 사용하고 언제 사용하지 말아야 하는지 판단할 수 있는 능력을 기르는 것이 중요합니다.'
            },
            {
                name: '질문 3',
                score: 84,
                type: '꼬리질문',
                question: '팀 프로젝트에서 의견 충돌이 발생했을 때 어떻게 해결하시나요?',
                myAnswer: '팀 프로젝트에서 의견 충돌이 발생하면 먼저 각자의 의견을 충분히 들어보려고 합니다. 감정적이 되지 않도록 차분하게 각 의견의 장단점을 객관적으로 분석하고, 프로젝트 목표에 가장 부합하는 방향을 찾으려고 노력합니다. 필요시 프로토타입을 만들어서 실제로 테스트해보거나, 팀 리더나 멘토에게 조언을 구하기도 합니다.',
                modelAnswer: '의견 충돌 상황에서는 먼저 각 의견의 근거와 배경을 명확히 파악해야 합니다. 감정적 대립보다는 데이터와 사실에 기반한 토론을 유도하고, 프로젝트의 목표와 우선순위를 기준으로 판단합니다. 타협점을 찾기 어려울 때는 작은 실험이나 프로토타입을 통해 검증하거나, 외부 전문가의 의견을 구하는 것도 좋은 방법입니다. 무엇보다 팀의 화합과 프로젝트 성공이라는 공통 목표를 잊지 않는 것이 중요합니다.'
            },
            {
                name: '질문 4',
                score: 94,
                type: '상황형',
                question: '가장 어려웠던 프로젝트 경험과 그것을 어떻게 극복했는지 말씀해주세요.',
                myAnswer: '가장 어려웠던 프로젝트는 졸업작품으로 진행한 실시간 채팅 애플리케이션 개발이었습니다. WebSocket 연결이 자주 끊어지고 메시지가 누락되는 문제가 발생했었습니다. 처음에는 혼자 해결하려고 했지만 한계를 느껴서 온라인 커뮤니티에 질문을 올리고, 관련 문서를 더 자세히 읽어보았습니다. 결국 연결 상태 모니터링과 재연결 로직을 추가하고, 메시지 큐 시스템을 도입해서 문제를 해결할 수 있었습니다.',
                modelAnswer: '어려운 프로젝트를 극복하는 과정에서는 문제를 명확히 정의하고 우선순위를 정하는 것이 중요합니다. 혼자 해결하기 어려운 문제는 적극적으로 도움을 요청하고, 다양한 관점에서 접근해보는 것이 필요합니다. 실패를 두려워하지 말고 빠른 시행착오를 통해 학습하며, 각 단계에서 얻은 교훈을 정리하여 향후 유사한 상황에 활용할 수 있도록 해야 합니다. 무엇보다 포기하지 않는 끈기와 지속적인 학습 의지가 중요합니다.'
            },
            {
                name: '질문 5',
                score: 90,
                type: '행동형',
                question: '방금 말씀하신 프로젝트에서 다시 하게 된다면 어떤 부분을 다르게 하시겠어요?',
                myAnswer: '다시 하게 된다면 프로젝트 초기에 더 철저한 기술 검토를 했을 것 같습니다. WebSocket의 특성과 한계를 미리 파악하고, 대안 기술도 함께 고려했다면 문제 발생을 예방할 수 있었을 것입니다. 또한 초기부터 테스트 코드를 작성하고, 다양한 네트워크 환경에서 테스트해봤다면 더 안정적인 애플리케이션을 만들 수 있었을 것이라고 생각합니다.',
                modelAnswer: '프로젝트 회고를 통한 개선점 도출은 매우 중요한 학습 과정입니다. 기술적 측면뿐만 아니라 프로세스, 커뮤니케이션, 시간 관리 등 다양한 관점에서 개선점을 찾아보는 것이 좋습니다. 특히 예방 가능했던 문제들을 식별하고, 향후 프로젝트에서 활용할 수 있는 체크리스트나 가이드라인을 만드는 것이 유용합니다. 실패나 어려움을 겪은 경험을 성장의 기회로 전환하는 능력이 중요합니다.'
            },
            {
                name: '질문 6',
                score: 87,
                type: '꼬리질문',
                question: '개발자로서 5년 후의 목표는 무엇인가요?',
                myAnswer: '5년 후에는 풀스택 개발자로서 전문성을 갖춘 시니어 개발자가 되고 싶습니다. 기술적으로는 클라우드 아키텍처와 마이크로서비스에 대한 깊은 이해를 바탕으로 확장 가능한 시스템을 설계할 수 있는 능력을 기르고 싶습니다. 또한 후배 개발자들을 멘토링하며 팀의 기술 역량 향상에 기여하고, 오픈소스 프로젝트에도 꾸준히 참여해서 개발 커뮤니티에 기여하고 싶습니다.',
                modelAnswer: '명확한 커리어 목표 설정은 개발자로서의 성장에 매우 중요합니다. 단순히 기술적 스킬 향상뿐만 아니라 리더십, 커뮤니케이션, 비즈니스 이해도 등 종합적인 역량 개발을 고려해야 합니다. 구체적이고 측정 가능한 목표를 설정하고, 이를 달성하기 위한 단계별 계획을 수립하는 것이 좋습니다. 또한 변화하는 기술 트렌드에 적응하면서도 본인만의 전문 영역을 구축하는 것이 중요합니다.'
            }
        ]
    };

    // 등급별 메시지 함수
    const getGradeMessage = (score: number) => {
        if (score >= 95) return "S등급 - 면접관도 감탄할만큼 완벽한 응답이네요!";
        if (score >= 90) return "A+등급 - 완벽에 가까운 훌륭한 답변입니다!";
        if (score >= 85) return "A등급 - 우수한 답변이에요! 약간만 다듬으면 더 좋아질 수 있어요.";
        if (score >= 80) return "B+등급 - 매일 연습하면 더좋은 답변을 할 수 있어요!";
        if (score >= 75) return "B등급 - 기본기는 탄탄해요! 조금 더 연습해보세요.";
        if (score >= 70) return "C+등급 - 시작이 반이에요. 한걸음씩 함께 노력해요!";
        return "C등급 - 꾸준한 연습으로 실력을 키워나가세요!";
    };

    // 레이더 차트 데이터
    const radarData = [
        { subject: '답변 내용', score: evaluationData.areaScores.text.total, fullMark: 100 },
        { subject: '음성', score: evaluationData.areaScores.voice.total, fullMark: 100 },
        { subject: '영상', score: evaluationData.areaScores.video.total, fullMark: 100 },
        { subject: '감정', score: evaluationData.areaScores.emotion.total, fullMark: 100 },
    ];

    useEffect(() => {
        // 3초 후 분석 완료
        const timer = setTimeout(() => {
            setIsAnalyzing(false);
            setAnalysisComplete(true);
        }, 3000);

        return () => clearTimeout(timer);
    }, []);

    // 질문 클릭 핸들러
    const handleQuestionClick = (question: QuestionScore) => {
        setSelectedQuestion(question);
        setModalOpen(true);
    };

    // 모달 닫기 핸들러
    const closeModal = () => {
        setModalOpen(false);
        setSelectedQuestion(null);
    };

    // ESC 키로 모달 닫기
    useEffect(() => {
        const handleEscKey = (event: KeyboardEvent) => {
            if (event.keyCode === 27) {
                closeModal();
            }
        };

        if (modalOpen) {
            document.addEventListener('keydown', handleEscKey);
            return () => document.removeEventListener('keydown', handleEscKey);
        }
    }, [modalOpen]);

    // 분석 중 화면
    if (isAnalyzing) {
        return (
            <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
                <div className="text-center">
                    <div className="w-32 h-32 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mx-auto mb-8 animate-spin">
                        <div className="w-24 h-24 bg-[#e7f8ff] rounded-full flex items-center justify-center">
                            <i className="ri-file-chart-line text-4xl text-[#27386d]"></i>
                        </div>
                    </div>
                    <h2 className="text-4xl font-bold text-[#27386d] mb-6">
                        {userNickname}님의 면접 전체를<br/>
                        종합 분석하고 있어요!
                    </h2>
                    <p className="text-xl text-[#27386d]/70 mb-8">
                        AI가 모든 답변을 종합하여<br/>
                        최종 평가와 개인 맞춤 피드백을 준비하고 있습니다.
                    </p>
                    <div className="flex justify-center space-x-3">
                        <div className="w-4 h-4 bg-[#6ce5e8] rounded-full animate-bounce" style={{animationDelay: '0s'}}></div>
                        <div className="w-4 h-4 bg-[#6ce5e8] rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                        <div className="w-4 h-4 bg-[#6ce5e8] rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                    </div>
                </div>
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
                                "{userNickname}님은 <strong>논리적 사고력</strong>과 <strong>문제해결 능력</strong>이 뛰어나신 분이에요.
                                특히 어려운 상황에 대한 답변에서 94점이라는 높은 점수를 받으셨네요!
                                앞으로 <strong>시선 집중도 유지</strong>와 <strong>다양한 음성 톤 활용</strong>에 조금 더 신경 쓰신다면,
                                더욱 완벽한 면접관이 되실 수 있을 것 같습니다.
                                오늘 면접 정말 수고하셨고, 이미 충분히 멋진 모습이에요! 💪"
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
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">1</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">어려운 경험 답변 (94점)</h4>
                                    <p className="text-sm text-gray-600">문제해결력과 성장 의지가 뛰어나게 표현되었습니다</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">2</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">텍스트 분석 (92점)</h4>
                                    <p className="text-sm text-gray-600">논리적이고 체계적인 답변 구조가 일관되게 유지되었습니다</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">3</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">감정 분석 (91점)</h4>
                                    <p className="text-sm text-gray-600">65% 긍정적 표정으로 자신감과 진정성을 잘 전달했습니다</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 우선순위별 개선점 */}
                    <div className="bg-white rounded-2xl p-6 shadow-sm">
                        <div className="flex items-center mb-6">
                            <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mr-4">
                                <i className="ri-lightbulb-line text-2xl text-orange-500"></i>
                            </div>
                            <h3 className="text-xl font-semibold text-[#27386d]">우선순위별 개선점</h3>
                        </div>
                        <div className="space-y-4">
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-orange-400 rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">1</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">집중 지속도 향상 (78점)</h4>
                                    <p className="text-sm text-gray-600">후반부 질문에서 시선 집중도가 낮아졌습니다. 체력 관리가 필요해요</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-orange-400 rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">2</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">영상 분석 전반 (85점)</h4>
                                    <p className="text-sm text-gray-600">비언어적 표현력 향상을 위한 연습이 도움될 것 같습니다</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-3">
                                <div className="w-6 h-6 bg-orange-400 rounded-full flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">3</div>
                                <div>
                                    <h4 className="font-semibold text-gray-800 mb-1">음성 톤 다양성 (86점)</h4>
                                    <p className="text-sm text-gray-600">감정 표현에 따른 목소리 톤 변화를 더 활용해보세요</p>
                                </div>
                            </div>
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
                                            <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.similarity}%`}}></div>
                                        </div>
                                        <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.similarity}%</span>
                                    </div>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-600 w-24">지식 정확도</span>
                                    <div className="flex items-center flex-1 justify-end">
                                        <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                                            <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.accuracy}%`}}></div>
                                        </div>
                                        <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.accuracy}%</span>
                                    </div>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-600 w-24">질문의도 파악</span>
                                    <div className="flex items-center flex-1 justify-end">
                                        <div className="w-24 bg-gray-200 rounded-full h-2 mr-3">
                                            <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.text.understanding}%`}}></div>
                                        </div>
                                        <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.text.understanding}%</span>
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
                                        <span className="text-sm font-medium w-12 text-right whitespace-pre-line">{`매끄
러움`}</span>
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
                                            <div className="bg-[#6ce5e8] h-2 rounded-full" style={{width: `${evaluationData.areaScores.video.gazeRate}%`}}></div>
                                        </div>
                                        <span className="text-sm font-medium w-12 text-right">{evaluationData.areaScores.video.gazeRate}%</span>
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
                                    {index === 0 && "개념 설명이 명확하고 체계적이었습니다."}
                                    {index === 1 && "기술적 이해도가 뛰어나고 정확했습니다."}
                                    {index === 2 && "상황 대처 능력이 우수하게 나타났습니다."}
                                    {index === 3 && "행동 기반 답변이 최고 수준이었습니다."}
                                    {index === 4 && "꼬리질문 대응력이 뛰어났습니다."}
                                    {index === 5 && "종합적 사고력이 우수하게 발휘되었습니다."}
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

export default function FinalEvaluationPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-[#e7f8ff] flex items-center justify-center">
                    <div className="text-[#27386d] text-xl">로딩 중...</div>
                </div>
            }
        >
            <FinalEvaluationPageContent />
        </Suspense>
    );
}
