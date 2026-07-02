'use client';

import Link from 'next/link';
import api from '@/api/api';
import { useUser } from '@/contexts/UserContext'
import { useState, useEffect, useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
  ScriptableContext,
  ChartData,
  ChartOptions
} from 'chart.js';
import annotationPlugin from 'chartjs-plugin-annotation';
import { Line, Radar } from 'react-chartjs-2';

// Chart.js 컴포넌트 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
  annotationPlugin
);

// 키 타입 정의
type AreaKey = 'text' | 'voice' | 'video' | 'emotion';
type QuestionKey = 'concept' | 'technical' | 'situation' | 'behavior' | 'followUp';

type DayCounters = {
  programDayToday: number;
  trainedDays: number;
  consecutiveStreak: number;
  firstSessionDate: string | null;
  dayIndexByDate: Record<string, number>;
};

type RankApiResponse = {
  basis: 'current' | 'best';
  my_score: number;
  rank_percent: number;  // 상위 X%
  population: number;
  higher_or_equal: number;
};

// TypeScript 인터페이스
interface WeeklyDataItem {
  date: string;
  fullDate: string;
  score: number;
  day: string;
  areas: Record<AreaKey, number>;
  questionTypes: Record<QuestionKey, number>;
  routineAchieved?: boolean;
}

interface DailyReport {
  totalScore: number;
  rank: string;
  areas: Record<AreaKey, number>;
  topStrengths: string[];
  improvements: string[];
  aiAdvice: string;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

type JobStatsResponse = {
  success: boolean;
  job: string;
  applicants: number;
  cap_to_my_days: boolean;
  min_peer_points: number;
  my_days: number;
  my_growth_per_day: number | null;
  peer_avg_growth_per_day: number | null;
  multiplier: number | null;
  note_growth: string;
  job_rank: {
    basis: 'latest_score_within_my_days' | 'latest_score_all_days';
    my_score: number;
    rank_percent: number;      // 상위 X%
    population: number;        // 동일 직무 표본 수
    higher_or_equal: number;   // 내 점수 이상 인원(동점 포함)
  };
};

// 색상 시스템
const CHART_COLORS = {
  primary: '#27386d',
  secondary: '#6ce5e8',
  growthStart: '#94a3b8',
  growthEnd: '#27386d',
  benchmark50: '#e2e8f0',
  benchmark12: '#3b82f6',
  success: '#10b981',
  background: '#e7f8ff',
  white: '#ffffff'
};

// 개선된 더미데이터 (현실적인 성장 스토리)
// const getImprovedWeeklyData = (): WeeklyDataItem[] => [
//   {
//     date: '07/28', fullDate: '2025-07-28', day: '월', score: 64,
//     areas: { text: 62, voice: 58, video: 60, emotion: 76 },
//     questionTypes: { concept: 65, technical: 60, situation: 58, behavior: 72, followUp: 60 },
//     routineAchieved: true
//   },
//   {
//     date: '07/29', fullDate: '2025-07-29', day: '화', score: 67,
//     areas: { text: 65, voice: 61, video: 63, emotion: 78 },
//     questionTypes: { concept: 68, technical: 63, situation: 61, behavior: 74, followUp: 63 },
//     routineAchieved: true
//   },
//   {
//     date: '07/30', fullDate: '2025-07-30', day: '수', score: 73,
//     areas: { text: 71, voice: 68, video: 70, emotion: 82 },
//     questionTypes: { concept: 74, technical: 70, situation: 67, behavior: 79, followUp: 68 },
//     routineAchieved: true
//   },
//   {
//     date: '07/31', fullDate: '2025-07-31', day: '목', score: 76,
//     areas: { text: 74, voice: 72, video: 73, emotion: 84 },
//     questionTypes: { concept: 77, technical: 74, situation: 70, behavior: 82, followUp: 72 },
//     routineAchieved: true
//   },
//   {
//     date: '08/01', fullDate: '2025-08-01', day: '금', score: 78,
//     areas: { text: 76, voice: 74, video: 75, emotion: 86 },
//     questionTypes: { concept: 79, technical: 76, situation: 72, behavior: 84, followUp: 74 },
//     routineAchieved: true
//   },
//   {
//     date: '08/02', fullDate: '2025-08-02', day: '토', score: 82,
//     areas: { text: 80, voice: 78, video: 79, emotion: 89 },
//     questionTypes: { concept: 83, technical: 80, situation: 76, behavior: 87, followUp: 78 },
//     routineAchieved: true
//   },
//   {
//     date: '08/03', fullDate: '2025-08-03', day: '일', score: 85,
//     areas: { text: 83, voice: 82, video: 82, emotion: 92 },
//     questionTypes: { concept: 86, technical: 84, situation: 80, behavior: 90, followUp: 82 },
//     routineAchieved: true
//   }
// ];

// 상위 50% 평균 점수 더미 데이터 (들쑥날쑥한 변동)
const getAverageScoresData = (n: number): number[] => [68, 71, 69, 74, 70, 73, 72].slice(0, n);
const getPeerAverages = async (): Promise<(number|null)[]> => {
  const res = await api.get('/training/peer-averages', { params: { min_population: 5 } });
  return res.data.data as (number|null)[];
};


// 실제 API 호출로 교체
const getWeeklyTrainingData = async (): Promise<ApiResponse<WeeklyDataItem[]>> => {
  const res = await api.get('/training/weekly');
  // 백엔드가 { success, data } 형태로 반환
  return { success: true, data: res.data.data };
};

const getReportByDate = async (date: string): Promise<ApiResponse<DailyReport>> => {
  const res = await api.get(`/report/date/${date}`);
  // 백엔드가 { success, data: { totalScore, rank, areas, ... } } 형태로 반환
  return { success: true, data: res.data.data };
};

const getTrainingDayCounters = async (): Promise<DayCounters> => {
  const res = await api.get('/training/day-counters');
  return res.data.data as DayCounters;
};

// 2) 최신 세션 기준 상위 % 가져오기
const getCurrentRank = async (): Promise<RankApiResponse> => {
  const res = await api.get('/rank/current');
  return res.data as RankApiResponse;
};

// 3) 개인 최고점 기준 상위 % 가져오기
const getBestRank = async (): Promise<RankApiResponse> => {
  const res = await api.get('/rank/best');
  return res.data as RankApiResponse;
};

const getTop12Cutoff = async (): Promise<number> => {
  const res = await api.get('/rank/cutoff', { params: { percent: 12 } });
  return res.data.cutoff_score as number;
};

const getJobStats = async (
  cap_to_my_days: boolean = true,
  min_peer_points: number = 2
): Promise<JobStatsResponse> => {
  const res = await api.get('/rank/job-stats', { params: { cap_to_my_days, min_peer_points } });
  return res.data as JobStatsResponse;
};

export default function TrainingHistory() {
  // 상태 관리
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [weeklyLoading, setWeeklyLoading] = useState<boolean>(true);
  const [weeklyData, setWeeklyData] = useState<WeeklyDataItem[]>([]);
  const {user} = useUser()
  const userNickname = user?.nickname ?? '사용자';
  const userDesiredJob = user?.desired_job ?? '데이터 분석가';

  // 2) 상태 추가
  const [programDay, setProgramDay] = useState<number>(0);
  const [streak, setStreak] = useState<number>(0);
  const [trainedDays, setTrainDays] = useState<number>(0);
  const [dayIndexByDate, setDayIndexByDate] = useState<Record<string, number>>({});

  // 랭크 상태
  const [currentRank, setCurrentRank] = useState<number | null>(null);
  const [bestRank, setBestRank] = useState<number | null>(null);
  const [rankLoading, setRankLoading] = useState<boolean>(false);
  const [rankError, setRankError] = useState<string | null>(null);

  const [targetScore, setTargetScore] = useState<number>(88); // 초기값
  const [peerAverages, setPeerAverages] = useState<(number|null)[]>([]);

  const [jobStatsLoading, setJobStatsLoading] = useState<boolean>(false);
  const [jobStatsError, setJobStatsError] = useState<string | null>(null);

  const [jobApplicants, setJobApplicants] = useState<number | null>(null);        // 지원자 수
  const [jobRankPercent, setJobRankPercent] = useState<number | null>(null);      // 상위 %
  const [growthMultiplier, setGrowthMultiplier] = useState<number | null>(null);  // 성장 배수
  const [myGrowthPerDay, setMyGrowthPerDay] = useState<number | null>(null);
  const [peerAvgGrowthPerDay, setPeerAvgGrowthPerDay] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const cutoff = await getTop12Cutoff();
        setTargetScore(cutoff);
      } catch {
        // 실패 시 기본값 유지
      }
    })();
  }, []);

  // 3) 마운트 시 불러오기
  useEffect(() => {
    const loadCounters = async () => {
      try {
        const d = await getTrainingDayCounters();
        setProgramDay(d.programDayToday);
        setStreak(d.consecutiveStreak);
        // ✔ 핵심: 누락된 trainedDays 세팅
        setTrainDays(
          typeof d.trainedDays === 'number'
            ? d.trainedDays
            : Object.keys(d.dayIndexByDate ?? {}).length // 백업 계산
        );
        setDayIndexByDate(d.dayIndexByDate);
      } catch (e) {
        setProgramDay(0);
        setStreak(0);
        setTrainDays(0); // 실패 시 0으로 명시 세팅
        setDayIndexByDate({});
      }
    };
    loadCounters();
  }, []);

  useEffect(() => {
    if (trainedDays <= 0) return;          // 아직 내 일수 모르면 패스
    (async () => {
      try {
        const arr = await getPeerAverages();    // (number|null)[] 반환
        setPeerAverages(arr);
      } catch (e) {
        setPeerAverages([]); // 실패 시 빈 배열
      }
    })();
  }, [trainedDays]);


  useEffect(() => {
    let mounted = true;

    (async () => {
      setRankLoading(true);
      try {
        // 두 랭크를 병렬로 호출해 최초 페인트 지연을 최소화
        const [cur, best] = await Promise.all([getCurrentRank(), getBestRank()]);
        if (!mounted) return;

        setCurrentRank(Number(cur.rank_percent.toFixed(1)));
        setBestRank(Number(best.rank_percent.toFixed(1)));
      } catch (e: any) {
        if (!mounted) return;
        const detail = e?.response?.data?.detail || e?.message || '랭크 정보를 불러오지 못했습니다.';
        setRankError(detail);
      } finally {
        if (mounted) setRankLoading(false);
      }
    })();

    return () => {
      mounted = false; // 언마운트 시 상태 업데이트 방지
    };
  }, []);
  
  useEffect(() => {
    let mounted = true;
    (async () => {
      setJobStatsLoading(true);
      try {
        const stats = await getJobStats(true, 2); // 내 일수 이내로 캡 + 성장률 최소 2포인트
        if (!mounted) return;

        setJobApplicants(stats.applicants);
        setJobRankPercent(Number(stats.job_rank.rank_percent.toFixed(1)));
        setGrowthMultiplier(
          stats.multiplier !== null ? Number(stats.multiplier.toFixed(1)) : null
        );
        setMyGrowthPerDay(
          stats.my_growth_per_day !== null ? Number(stats.my_growth_per_day.toFixed(2)) : null
        );
        setPeerAvgGrowthPerDay(
          stats.peer_avg_growth_per_day !== null ? Number(stats.peer_avg_growth_per_day.toFixed(2)) : null
        );
      } catch (e: any) {
        const detail = e?.response?.data?.detail || e?.message || '동일 직무 통계를 불러오지 못했습니다.';
        setJobStatsError(detail);
      } finally {
        setJobStatsLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  // 상수
  const CURRENT_RANK = 23;
  const TARGET_SCORE = targetScore; // 상위 12% 기준
  const AVERAGE_SCORE = 72; // 상위 50% 기준
  const TARGET_JOB = userDesiredJob;
  const JOB_APPLICANTS = jobApplicants ?? 0;
  const JOB_CURRENT_RANK = jobRankPercent ?? 0; // 상위 10%

  // 데이터 로딩
  useEffect(() => {
    const loadWeeklyData = async () => {
      setWeeklyLoading(true);
      try {
        const result = await getWeeklyTrainingData();
        setWeeklyData(result.data);
      } catch (error) {
        console.error('데이터 로딩 실패:', error);
      } finally {
        setWeeklyLoading(false);
      }
    };
    loadWeeklyData();
  }, []);

  useEffect(() => {
    if (selectedDate) {
      fetchDailyReport(selectedDate);
    } else {
      setSelectedReport(null);
      setError(null);
    }
  }, [selectedDate]);

  const fetchDailyReport = async (date: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await getReportByDate(date);
      if (result.success && result.data) {
        setSelectedReport(result.data);
      }
    } catch {
      setError('해당 날짜의 면접 기록을 불러올 수 없습니다.');
      setSelectedReport(null);
    } finally {
      setLoading(false);
    }
  };

  // 그라데이션 생성 함수
  const createGradient = (ctx: CanvasRenderingContext2D, chartArea: any) => {
    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
    gradient.addColorStop(0, CHART_COLORS.growthStart);
    gradient.addColorStop(0.5, CHART_COLORS.secondary);
    gradient.addColorStop(1, CHART_COLORS.primary);
    return gradient;
  };

  // 빈 차트 데이터/옵션 (타입 안전)
  const emptyLineData: ChartData<'line'> = useMemo(() => ({ labels: [], datasets: [] }), []);
  const emptyLineOptions: ChartOptions<'line'> = useMemo(() => ({ responsive: true }), []);
  const emptyRadarData: ChartData<'radar'> = useMemo(() => ({ labels: [], datasets: [] }), []);
  const emptyRadarOptions: ChartOptions<'radar'> = useMemo(
    () => ({ responsive: true, maintainAspectRatio: false }),
    []
  );

  // 메인 시계열 차트 데이터/옵션
  const { lineData, lineOptions }: { lineData: ChartData<'line'>; lineOptions: ChartOptions<'line'> } = useMemo(() => {
    if (weeklyData.length === 0) {
      return { lineData: emptyLineData, lineOptions: emptyLineOptions };
    }

    // const averageScores = getAverageScoresData(weeklyData.length);

    const avgSeries: (number|null)[] = (() => {
      const need = weeklyData.length;
      const arr = peerAverages.slice(0, need);
      if (arr.length < need) {
        return [...arr, ...Array(need - arr.length).fill(null)];
      }
      return arr;
    })();

    const data: ChartData<'line'> = {
      labels: weeklyData.map(d => `${d.date}\n(${d.day})`),
      datasets: [
        {
          label: '내 점수',
          data: weeklyData.map(d => d.score),
          borderColor: (context: ScriptableContext<'line'>) => {
            const chart = context.chart as any;
            const { ctx, chartArea } = chart;
            if (!chartArea) return CHART_COLORS.secondary;
            return createGradient(ctx as CanvasRenderingContext2D, chartArea);
          },
          backgroundColor: 'transparent',
          borderWidth: 4,
          pointRadius: weeklyData.map((_, index) =>
            index === 0 ? 4 : index === weeklyData.length - 1 ? 8 : 5
          ),
          pointBackgroundColor: weeklyData.map((_, index) =>
            index === 0 ? CHART_COLORS.growthStart :
            index === weeklyData.length - 1 ? CHART_COLORS.primary :
            CHART_COLORS.secondary
          ),
          pointBorderColor: CHART_COLORS.white,
          pointBorderWidth: 2,
          tension: 0.4,
          fill: false
        },
        {
          label: '사용자 평균',
          data: avgSeries as number[],     // Chart.js는 null도 수용, 다만 TS 캐스팅 필요
          spanGaps: true,                  // null 구간을 자연스럽게 잇기
          borderColor: '#9ca3af',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#9ca3af',
          pointBorderColor: CHART_COLORS.white,
          pointBorderWidth: 1,
          tension: 0.3,
          fill: false,
          borderDash: [5, 5]
        }
      ]
    };

    const options: ChartOptions<'line'> = {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 10, bottom: 0, left: 10, right: 10 } },
      interaction: { intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (context) => {
              const dataIndex = context[0].dataIndex;
              const data = weeklyData[dataIndex];
              return `${data.date} (${data.day})`;
            },
            label: (context) => {
              const score = context.parsed.y as number;
              const datasetLabel = context.dataset.label;
              const dataIndex = context.dataIndex;
              if (datasetLabel === '내 점수') {
                const isFirst = dataIndex === 0;
                const isLast = dataIndex === weeklyData.length - 1;
                if (isFirst) return [`${score}점`, '시작점'];
                if (isLast) {
                  const growth = score - weeklyData[0].score;
                  return [`${score}점`, `+${growth}점 성장`];
                }
                return `${score}점`;
              }
              return `사용자 평균: ${score}점`;
            }
          }
        },
        annotation: {
          annotations: {
            targetLine: {
              type: 'line',
              yMin: TARGET_SCORE,
              yMax: TARGET_SCORE,
              borderColor: '#3b82f6',
              borderWidth: 3,
              borderDash: [8, 4],
              label: {
                display: true,
                content: '상위 12% 목표선',
                position: 'end',
                backgroundColor: '#3b82f6',
                color: '#ffffff',
                font: { size: 11 },
                xAdjust: -10,
                yAdjust: -5
              }
            }
          }
        } as any
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#6b7280', font: { size: 12 }, padding: 5 }
        },
        y: {
          min: Math.min(...weeklyData.map(d => d.score)) - 5,
          max: Math.max(TARGET_SCORE, Math.max(...weeklyData.map(d => d.score))) + 5,
          grid: { color: '#f1f5f9' },
          ticks: {
            color: '#6b7280',
            font: { size: 12 },
            callback: (value) => `${value}점`,
            padding: 10
          }
        }
      },
      elements: { point: { hoverRadius: 8 } }
    };

    return { lineData: data, lineOptions: options };
  }, [weeklyData, TARGET_SCORE, emptyLineData, emptyLineOptions, peerAverages]);

  // 레이더 차트 (영역별)
  // const { areasData, areasOptions }: { areasData: ChartData<'radar'>; areasOptions: ChartOptions<'radar'> } = useMemo(() => {
  //   if (weeklyData.length === 0) {
  //     return { areasData: emptyRadarData, areasOptions: emptyRadarOptions };
  //   }
  //   const day1 = weeklyData[0];
  //   const day7 = weeklyData[weeklyData.length - 1];

  //   const data: ChartData<'radar'> = {
  //     labels: ['답변내용', '음성', '영상', '감정'],
  //     datasets: [
  //       {
  //         label: '1일차',
  //         data: [day1.areas.text, day1.areas.voice, day1.areas.video, day1.areas.emotion],
  //         borderColor: '#1e3a8a',
  //         backgroundColor: '#1e3a8a25',
  //         borderWidth: 3,
  //         pointBackgroundColor: '#1e3a8a',
  //         pointBorderColor: CHART_COLORS.white,
  //         pointBorderWidth: 3
  //       },
  //       {
  //         label: '7일차',
  //         data: [day7.areas.text, day7.areas.voice, day7.areas.video, day7.areas.emotion],
  //         borderColor: '#6ce5e8',
  //         backgroundColor: '#6ce5e830',
  //         borderWidth: 3,
  //         pointBackgroundColor: '#6ce5e8',
  //         pointBorderColor: CHART_COLORS.white,
  //         pointBorderWidth: 3
  //       }
  //     ]
  //   };

  //   const options: ChartOptions<'radar'> = {
  //     responsive: true,
  //     maintainAspectRatio: false,
  //     plugins: {
  //       legend: {
  //         position: 'bottom',
  //         labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
  //       }
  //     },
  //     scales: {
  //       r: {
  //         angleLines: { color: '#e2e8f0' },
  //         grid: { color: '#e2e8f0' },
  //         pointLabels: { color: '#374151', font: { size: 11 } },
  //         ticks: { display: false },
  //         min: 50,
  //         max: 100
  //       }
  //     }
  //   };

  //   return { areasData: data, areasOptions: options };
  // }, [weeklyData, emptyRadarData, emptyRadarOptions]);

  // // 레이더 차트 (질문유형별)
  // const { questionData, questionOptions }: { questionData: ChartData<'radar'>; questionOptions: ChartOptions<'radar'> } =
  //   useMemo(() => {
  //     if (weeklyData.length === 0) {
  //       return { questionData: emptyRadarData, questionOptions: emptyRadarOptions };
  //     }

  //     const day1 = weeklyData[0];
  //     const day7 = weeklyData[weeklyData.length - 1];

  //     const data: ChartData<'radar'> = {
  //       labels: ['개념설명', '기술형', '상황형', '행동형', '꼬리질문'],
  //       datasets: [
  //         {
  //           label: '1일차',
  //           data: [
  //             day1.questionTypes.concept,
  //             day1.questionTypes.technical,
  //             day1.questionTypes.situation,
  //             day1.questionTypes.behavior,
  //             day1.questionTypes.followUp
  //           ],
  //           borderColor: '#1e3a8a',
  //           backgroundColor: '#1e3a8a25',
  //           borderWidth: 3,
  //           pointBackgroundColor: '#1e3a8a',
  //           pointBorderColor: CHART_COLORS.white,
  //           pointBorderWidth: 3
  //         },
  //         {
  //           label: '7일차',
  //           data: [
  //             day7.questionTypes.concept,
  //             day7.questionTypes.technical,
  //             day7.questionTypes.situation,
  //             day7.questionTypes.behavior,
  //             day7.questionTypes.followUp
  //           ],
  //           borderColor: '#6ce5e8',
  //           backgroundColor: '#6ce5e830',
  //           borderWidth: 3,
  //           pointBackgroundColor: '#6ce5e8',
  //           pointBorderColor: CHART_COLORS.white,
  //           pointBorderWidth: 3
  //         }
  //       ]
  //     };

  //     const options: ChartOptions<'radar'> = {
  //       responsive: true,
  //       maintainAspectRatio: false,
  //       plugins: {
  //         legend: {
  //           position: 'bottom',
  //           labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
  //         }
  //       },
  //       scales: {
  //         r: {
  //           angleLines: { color: '#e2e8f0' },
  //           grid: { color: '#e2e8f0' },
  //           pointLabels: { color: '#374151', font: { size: 11 } },
  //           ticks: { display: false },
  //           min: 50,
  //           max: 100
  //         }
  //       }
  //     };

  //     return { questionData: data, questionOptions: options };
  //   }, [weeklyData, emptyRadarData, emptyRadarOptions]);
  // 레이더 차트 (영역별)
  const { areasData, areasOptions }: { areasData: ChartData<'radar'>; areasOptions: ChartOptions<'radar'> } = useMemo(() => {
    if (weeklyData.length === 0) {
      return { areasData: emptyRadarData, areasOptions: emptyRadarOptions };
    }

    const first = weeklyData[0];                                // 1) 첫 기록
    const last = weeklyData[weeklyData.length - 1];             // 2) 마지막 기록

    // 3) 일차 라벨 계산: dayIndexByDate가 있으면 그대로, 없으면 fallback으로 배열 인덱스 기반
    const firstLabel = dayIndexByDate[first.fullDate]
      ? `${dayIndexByDate[first.fullDate]}일차`
      : '1일차';

    const lastLabel = dayIndexByDate[last.fullDate]
      ? `${dayIndexByDate[last.fullDate]}일차`
      : `${weeklyData.length}일차`;

    // 4) 데이터셋 구성: 최소 1개, 2일 이상이면 마지막 기록용 데이터셋을 추가
    const datasets: ChartData<'radar'>['datasets'] = [
      {
        label: firstLabel,
        data: [first.areas.text, first.areas.voice, first.areas.video, first.areas.emotion],
        borderColor: '#1e3a8a',
        backgroundColor: '#1e3a8a25',
        borderWidth: 3,
        pointBackgroundColor: '#1e3a8a',
        pointBorderColor: CHART_COLORS.white,
        pointBorderWidth: 3
      }
    ];

    if (weeklyData.length > 1) {
      datasets.push({
        label: lastLabel,
        data: [last.areas.text, last.areas.voice, last.areas.video, last.areas.emotion],
        borderColor: '#6ce5e8',
        backgroundColor: '#6ce5e830',
        borderWidth: 3,
        pointBackgroundColor: '#6ce5e8',
        pointBorderColor: CHART_COLORS.white,
        pointBorderWidth: 3
      });
    }
    const data: ChartData<'radar'> = {
      labels: ['답변내용', '음성', '영상', '감정'],
      datasets
    };

    const options: ChartOptions<'radar'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
        }
      },
      scales: {
        r: {
          angleLines: { color: '#e2e8f0' },
          grid: { color: '#e2e8f0' },
          pointLabels: { color: '#374151', font: { size: 11 } },
          ticks: { display: false },
          min: 0,
          max: 100
        }
      }
    };

    return { areasData: data, areasOptions: options };
  }, [weeklyData, dayIndexByDate, emptyRadarData, emptyRadarOptions]);

  // 레이더 차트 (질문유형별)
  const { questionData, questionOptions }: { questionData: ChartData<'radar'>; questionOptions: ChartOptions<'radar'> } =
    useMemo(() => {
      if (weeklyData.length === 0) {
        return { questionData: emptyRadarData, questionOptions: emptyRadarOptions };
      }

      const first = weeklyData[0];                                // 1) 첫 기록
      const last = weeklyData[weeklyData.length - 1];             // 2) 마지막 기록

      // 3) 일차 라벨 계산
      const firstLabel = dayIndexByDate[first.fullDate]
        ? `${dayIndexByDate[first.fullDate]}일차`
        : '1일차';

      const lastLabel = dayIndexByDate[last.fullDate]
        ? `${dayIndexByDate[last.fullDate]}일차`
        : `${weeklyData.length}일차`;

      // 4) 데이터셋 구성
      const datasets: ChartData<'radar'>['datasets'] = [
        {
          label: firstLabel,
          data: [
            first.questionTypes.concept,
            first.questionTypes.technical,
            first.questionTypes.situation,
            first.questionTypes.behavior,
            first.questionTypes.followUp
          ],
          borderColor: '#1e3a8a',
          backgroundColor: '#1e3a8a25',
          borderWidth: 3,
          pointBackgroundColor: '#1e3a8a',
          pointBorderColor: CHART_COLORS.white,
          pointBorderWidth: 3
        }
      ];

      if (weeklyData.length > 1) {
        datasets.push({
          label: lastLabel,
          data: [
            last.questionTypes.concept,
            last.questionTypes.technical,
            last.questionTypes.situation,
            last.questionTypes.behavior,
            last.questionTypes.followUp
          ],
          borderColor: '#6ce5e8',
          backgroundColor: '#6ce5e830',
          borderWidth: 3,
          pointBackgroundColor: '#6ce5e8',
          pointBorderColor: CHART_COLORS.white,
          pointBorderWidth: 3
        });
      }

    const data: ChartData<'radar'> = {
      labels: ['개념설명', '기술형', '상황형', '행동형', '꼬리질문'],
      datasets
    };

    const options: ChartOptions<'radar'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 12, padding: 15, font: { size: 11 } }
        }
      },
      scales: {
        r: {
          angleLines: { color: '#e2e8f0' },
          grid: { color: '#e2e8f0' },
          pointLabels: { color: '#374151', font: { size: 11 } },
          ticks: { display: false },
          min: 0,
          max: 100
        }
      }
    };

    return { questionData: data, questionOptions: options };
  }, [weeklyData, dayIndexByDate, emptyRadarData, emptyRadarOptions]);


  // 계산된 값들
  const growthAmount = weeklyData.length > 0 ? weeklyData[weeklyData.length - 1].score - weeklyData[0].score : 0;
  const currentScore = weeklyData.length > 0 ? weeklyData[weeklyData.length - 1].score : 0;
  const startScore = weeklyData.length > 0 ? weeklyData[0].score : 0;
  const pointsToTarget = Math.max(0, TARGET_SCORE - currentScore);
  const consecutiveDays = 7;

  // 새로운 분석 함수들
  const getDailyGrowthRate = () => {
    if (weeklyData.length === 0) return 0;
    return Math.round(growthAmount / consecutiveDays);
  };

  const getGrowthPercentage = () => {
    if (weeklyData.length === 0) return 0;
    const s = weeklyData[0].score;
    const c = weeklyData[weeklyData.length - 1].score;
    if (s === 0) return 0; // 분모 0 방지
    return Math.round(((c - s) / s) * 100);
  };


  const getGrowthMultiplier = () => {
    if (growthMultiplier !== null) return growthMultiplier;
    // 서버 값이 없을 때만 기존 더미 로직으로 fallback
    const userGrowthRate = weeklyData.length > 0
      ? Math.round((weeklyData[weeklyData.length - 1].score - weeklyData[0].score) / 7)
      : 0;
    const averageGrowthRate = 1;
    return Math.round(userGrowthRate / averageGrowthRate);
  };

  const getTopStrength = () => {
    if (weeklyData.length === 0) return '데이터 로딩 중';
    const latestData = weeklyData[weeklyData.length - 1];
    const areas: AreaKey[] = ['text', 'voice', 'video', 'emotion'];
    const areaNames = ['답변 구성', '음성 전달', '시선 처리', '감정 표현'];

    const maxArea = areas.reduce<AreaKey>(
      (max, area) => (latestData.areas[area] > latestData.areas[max] ? area : max),
      areas[0]
    );

    return areaNames[areas.indexOf(maxArea)] + ' 최고 수준';
  };

  const getWeakestArea = () => {
    if (weeklyData.length === 0) return '데이터 로딩 중';
    const latestData = weeklyData[weeklyData.length - 1];
    const areas: AreaKey[] = ['text', 'voice', 'video', 'emotion'];
    const areaNames = ['답변 구성', '음성 전달', '시선 처리', '감정 표현'];

    const minArea = areas.reduce<AreaKey>(
      (min, area) => (latestData.areas[area] < latestData.areas[min] ? area : min),
      areas[0]
    );

    return areaNames[areas.indexOf(minArea)] + ' 집중 훈련 필요';
  };

  const getWeakestQuestionType = () => {
    if (weeklyData.length === 0) return '데이터 로딩 중';
    const latestData = weeklyData[weeklyData.length - 1];
    const types: QuestionKey[] = ['concept', 'technical', 'situation', 'behavior', 'followUp'];
    const typeNames = ['개념설명형', '기술형', '상황형', '행동형', '꼬리질문'];

    const minType = types.reduce<QuestionKey>(
      (min, type) => (latestData.questionTypes[type] < latestData.questionTypes[min] ? type : min),
      types[0]
    );

    return typeNames[types.indexOf(minType)] + ' 질문에 더 집중하기';
  };

  const getGradeMessage = (score: number): string => {
    if (score >= 90) return 'S등급 - 완벽한 면접 실력!';
    if (score >= 85) return 'A+등급 - 상급자 수준!';
    if (score >= 80) return 'A등급 - 우수한 실력!';
    if (score >= 75) return 'B+등급 - 중급자 수준!';
    if (score >= 70) return 'B등급 - 기본기 완성!';
    return 'C등급 - 꾸준히 발전 중!';
  };

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* 헤더 영역 */}
        <div className="flex items-center mb-8">
          <Link
            href="/mypage"
            className="w-10 h-10 flex items-center justify-center rounded-full bg-white shadow-sm mr-4 cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <i className="ri-arrow-left-line text-xl text-[#27386d]"></i>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-[#27386d] mb-1">나의 훈련기록</h1>
            <p className="text-gray-600">면접 실력 향상 과정을 확인해보세요</p>
          </div>
        </div>

        {/* 프로필 배너 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-[#6ce5e8] rounded-full flex items-center justify-center">
                <i className="ri-user-3-line text-2xl text-[#27386d]"></i>
              </div>
              <div>
                <h2 className="text-xl font-bold text-[#27386d] mb-1">{userNickname}</h2>
                <p className="text-gray-600 mb-1">희망직무: {userDesiredJob}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center justify-end mb-3">
                <i className="ri-fire-line text-orange-500 mr-2"></i>
                <span className="text-xl font-bold text-[#27386d]">{streak}일 연속</span>
              </div>
              <div className="text-base text-gray-600 mb-2">D-DAY 우수성과 공유 컨퍼런스</div>
            </div>
          </div>
        </div>

        {/* Hero Impact Section */}
        <div className="bg-white rounded-2xl p-8 shadow-sm mb-8">
          <div className="text-center">
            <div className="mb-8">
              <div
                className="text-5xl font-bold mb-6 text-[#27386d]"
                style={{ textShadow: '0 4px 8px rgba(39, 56, 109, 0.3)' }}
              >
                매일의 노력이 <span className="text-7xl font-extrabold">{getGrowthPercentage()}%</span> 성장을 만들었어요!
              </div>
            </div>

            {/* 통합된 1일차 → 7일차 카드 */}
            <div className="mb-8">
              <div
                style={{
                  background: 'rgba(108, 229, 232, 0.15)',
                  border: '2px solid rgba(108, 229, 232, 0.2)',
                  borderRadius: '16px',
                  padding: '32px',
                  boxShadow: '0 8px 32px rgba(108, 229, 232, 0.1)'
                }}
                className="flex items-center justify-between"
              >
                {/* 1일차 섹션 */}
                <div className="text-center flex-1">
                  <div className="text-xl font-semibold text-gray-600 mb-3">9일차</div>
                  <div className="text-4xl font-bold text-gray-700 mb-2">{startScore}점</div>
                  <div className="text-base text-gray-500">상위 63.6%</div>
                </div>

                {/* 화살표 섹션 */}
                <div className="flex items-center justify-center px-8">
                  <div className="w-24 h-24 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center shadow-lg">
                    <i className="ri-arrow-right-line text-4xl text-white"></i>
                  </div>
                </div>

                {/* 7일차 섹션 */}
                <div className="text-center flex-1">
                  <div className="text-xl font-semibold text-[#27386d] mb-3">{trainedDays}일차</div>
                  <div className="text-4xl font-bold text-[#27386d] mb-2">{currentScore}점</div>
                  <div className="text-base text-[#27386d] font-bold bg-[#6ce5e8]/20 px-3 py-1 rounded-lg inline-block">
                    상위 {currentRank}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 컨텐츠 영역 */}
        <div className="grid grid-cols-1 lg:grid-cols-[7fr_3fr] gap-8 mb-8">
          {/* 메인 시계열 차트 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-[#27386d] mb-1 flex items-center">
                <i className="ri-line-chart-line mr-2"></i>
                7일간 성장 스토리
              </h2>
              <p className="text-sm text-gray-600">최근 7일간의 면접 점수 변화와 목표 달성 현황</p>
            </div>

            {weeklyLoading ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-[#6ce5e8] bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-3 animate-spin">
                  <i className="ri-loader-4-line text-xl text-[#27386d]"></i>
                </div>
                <p className="text-gray-600">차트를 불러오는 중...</p>
              </div>
            ) : weeklyData.length > 0 ? (
              <div className="h-[32rem]">
                <Line data={lineData} options={lineOptions} />
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <i className="ri-line-chart-line text-xl text-gray-400"></i>
                </div>
                <p className="text-gray-600">데이터를 불러올 수 없습니다</p>
              </div>
            )}
          </div>

          {/* 1일차 vs 7일차 비교 */}
          <div className="hidden lg:block">
            <div className="bg-white rounded-2xl p-6 shadow-sm mb-6" style={{ height: '320px' }}>
              <h3 className="text-lg font-semibold text-[#27386d] mb-4 flex items-center">
                <i className="ri-bar-chart-line mr-2"></i>
                영역별 성장
              </h3>
              <div className="h-56">
                {weeklyData.length > 0 ? (
                  <Radar data={areasData} options={areasOptions} />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <i className="ri-radar-line text-2xl mr-2"></i>
                    <span>데이터 로딩 중...</span>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm" style={{ height: '320px' }}>
              <h3 className="text-lg font-semibold text-[#27386d] mb-4 flex items-center">
                <i className="ri-pie-chart-line mr-2"></i>
                질문유형별 성장
              </h3>
              <div className="h-56">
                {weeklyData.length > 0 ? (
                  <Radar data={questionData} options={questionOptions} />
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <i className="ri-pie-chart-line text-2xl mr-2"></i>
                    <span>데이터 로딩 중...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 모바일용 레이더 차트 */}
        <div className="lg:hidden space-y-6 mb-8">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#27386d] mb-4 flex items-center">
              <i className="ri-bar-chart-line mr-2"></i>
              영역별 성장 비교
            </h3>
            <div className="h-64">
              {weeklyData.length > 0 ? (
                <Radar data={areasData} options={areasOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <i className="ri-radar-line text-2xl mr-2"></i>
                  <span>데이터 로딩 중...</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#27386d] mb-4 flex items-center">
              <i className="ri-pie-chart-line mr-2"></i>
              질문유형별 성장 비교
            </h3>
            <div className="h-64">
              {weeklyData.length > 0 ? (
                <Radar data={questionData} options={questionOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <i className="ri-pie-chart-line text-2xl mr-2"></i>
                  <span>데이터 로딩 중...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 성과 배너 */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(108, 229, 232, 0.2), rgba(39, 56, 109, 0.15))',
            borderWidth: '2px',
            borderStyle: 'solid',
            borderColor: 'rgba(108, 229, 232, 0.3)',
            boxShadow: '0 8px 32px rgba(108, 229, 232, 0.15)'
          }}
          className="rounded-2xl p-6 mb-8"
        >
          <div className="text-center">
            <div className="text-2xl font-bold text-[#27386d] mb-4 flex items-center justify-center">
              <i className="ri-trophy-line mr-2"></i>
              이번주 최고 성과! 상위 {currentRank}% 진입 성공
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
                  minHeight: '100px'
                }}
                className="rounded-lg p-4 border border-white/20 flex flex-col justify-center"
              >
                <div className="text-sm text-gray-600 mb-1">성장 속도</div>
                <div className="font-bold text-[#27386d] text-base">일평균 {getDailyGrowthRate()}점씩 성장 중!</div>
              </div>

              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
                  minHeight: '100px'
                }}
                className="rounded-lg p-4 border border-white/20 flex flex-col justify-center"
              >
                <div className="text-sm text-gray-600 mb-1">강점 분야</div>
                <div className="font-bold text-[#27386d] text-base">{getTopStrength()}</div>
              </div>

              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
                  minHeight: '100px'
                }}
                className="rounded-lg p-4 border border-white/20 flex flex-col justify-center"
              >
                <div className="text-sm text-gray-600 mb-1">개선 우선순위</div>
                <div className="font-bold text-[#27386d] text-base">{getWeakestArea()}</div>
              </div>

              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
                  minHeight: '100px'
                }}
                className="rounded-lg p-4 border border-white/20 flex flex-col justify-center"
              >
                <div className="text-sm text-gray-600 mb-1">목표 달성 전략</div>
                <div className="font-bold text-[#27386d] text-base">{getWeakestQuestionType()}</div>
              </div>
            </div>
          </div>
        </div>

        {/* 사회적 증명 배너 */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(108, 229, 232, 0.2), rgba(39, 56, 109, 0.15))',
            borderWidth: '2px',
            borderStyle: 'solid',
            borderColor: 'rgba(108, 229, 232, 0.3)',
            boxShadow: '0 8px 32px rgba(108, 229, 232, 0.15)',
            backdropFilter: 'blur(10px)'
          }}
          className="rounded-2xl p-8 mb-8"
        >
          <div className="text-center">
            <div className="text-2xl font-bold text-[#27386d] mb-3 flex items-center justify-center">
              <i className="ri-award-line mr-3 text-3xl"></i>
              동일 직무 지원자 [{TARGET_JOB}] {JOB_APPLICANTS}명 중 상위 {JOB_CURRENT_RANK}%
            </div>
            <div className="text-xl text-[#3b82f6] font-semibold">
              동일 직무 지원자 대비 {getGrowthMultiplier()}배 빠른 성장 속도!
            </div>
          </div>
        </div>

        {/* 지난 학습기록 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#27386d] mb-1 flex items-center">
            <i className="ri-calendar-line mr-2"></i>
            지난 학습기록
          </h2>
          <p className="text-sm text-gray-600 mb-4">날짜를 선택하면 해당 날짜의 면접 결과를 확인할 수 있습니다</p>

          <div className="mb-6 text-center">
            <label htmlFor="user-date" className="block text-sm font-medium text-[#27386d] mb-2">
              날짜 선택
            </label>
            <input
              type="date"
              id="user-date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] focus:border-transparent text-[#27386d] cursor-pointer"
              max={new Date().toISOString().split('T')[0]}
            />
          </div>

          {loading && (
            <div className="border-t pt-6">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-4 animate-spin">
                  <i className="ri-loader-4-line text-2xl text-[#27386d]"></i>
                </div>
                <h3 className="text-lg font-medium text-[#27386d] mb-2">보고서를 불러오는 중...</h3>
                <p className="text-gray-600">잠시만 기다려주세요</p>
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="border-t pt-6">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className="ri-error-warning-line text-2xl text-red-500"></i>
                </div>
                <h3 className="text-lg font-medium text-red-600 mb-2">데이터를 불러올 수 없습니다</h3>
                <p className="text-gray-600 mb-4">{error}</p>
                <button
                  onClick={() => selectedDate && fetchDailyReport(selectedDate)}
                  className="px-4 py-2 bg-[#27386d] text-white rounded-lg hover:bg-[#27386d]/90 transition-colors"
                >
                  다시 시도
                </button>
              </div>
            </div>
          )}

          {selectedReport && !loading && !error && (
            <div className="border-t pt-6">
              <div className="bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-2xl p-6 mb-6 text-white">
                <div className="text-center">
                  <h3 className="text-xl font-bold mb-2">{selectedDate} 면접 결과</h3>
                  <div className="text-5xl font-bold mb-2">{selectedReport.totalScore}</div>
                  <div className="text-lg font-medium mb-2">/ 100점</div>
                  <div className="bg-white/20 rounded-lg px-4 py-2 inline-block">
                    <span className="text-sm font-semibold">{selectedReport.rank}</span>
                  </div>
                  <div className="mt-2 text-sm">{getGradeMessage(selectedReport.totalScore)}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#27386d] mb-1">{selectedReport.areas.text}</div>
                  <div className="text-sm text-gray-600">답변 내용</div>
                </div>
                <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#27386d] mb-1">{selectedReport.areas.voice}</div>
                  <div className="text-sm text-gray-600">음성</div>
                </div>
                <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#27386d] mb-1">{selectedReport.areas.video}</div>
                  <div className="text-sm text-gray-600">영상</div>
                </div>
                <div className="bg-[#f8fafc] rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#27386d] mb-1">{selectedReport.areas.emotion}</div>
                  <div className="text-sm text-gray-600">감정</div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-[#e7f8ff] to-[#f0f9ff] rounded-xl p-6 mb-6">
                <div className="flex items-center mb-3">
                  <div className="w-8 h-8 bg-[#27386d] rounded-full flex items-center justify-center mr-3">
                    <i className="ri-robot-line text-white"></i>
                  </div>
                  <h4 className="text-lg font-semibold text-[#27386d]">AI 개인 맞춤 조언</h4>
                </div>
                <p className="text-gray-800 leading-relaxed">{selectedReport.aiAdvice}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-green-50 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-thumb-up-line text-white text-sm"></i>
                    </div>
                    <h4 className="text-lg font-semibold text-green-800">주요 강점</h4>
                  </div>
                  <ul className="space-y-2">
                    {selectedReport.topStrengths.map((strength, index) => (
                      <li key={`strength-${index}`} className="flex items-start">
                        <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <span className="text-sm text-green-800">{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-orange-50 rounded-xl p-5">
                  <div className="flex items-center mb-4">
                    <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-lightbulb-line text-white text-sm"></i>
                    </div>
                    <h4 className="text-lg font-semibold text-orange-800">개선 포인트</h4>
                  </div>
                  <ul className="space-y-2">
                    {selectedReport.improvements.map((improvement, index) => (
                      <li key={`improvement-${index}`} className="flex items-start">
                        <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <span className="text-sm text-orange-800">{improvement}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {!selectedDate && !loading && (
            <div className="border-t pt-6 text-center py-8">
              <div className="w-12 h-12 bg-[#6ce5e8] bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-3">
                <i className="ri-calendar-check-line text-xl text-[#27386d]"></i>
              </div>
              <p className="text-gray-600">날짜를 선택해주세요</p>
              <p className="text-sm text-gray-400 mt-1">면접을 진행한 날짜의 상세 보고서를 확인할 수 있습니다</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
