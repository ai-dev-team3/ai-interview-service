'use client';

import Link from 'next/link';
import api from '@/api/api';
import { useState, useEffect, useMemo } from 'react';

type DayCounters = {
  programDayToday: number;
  trainedDays: number;
  consecutiveStreak: number;
  firstSessionDate: string | null;
  dayIndexByDate: Record<string, number>;
};

const getTrainingDayCounters = async (): Promise<DayCounters> => {
  const res = await api.get('/training/day-counters');
  return res.data.data as DayCounters;
};

// 날짜 포맷터: Date -> 'YYYY-MM-DD'
const fmtYMD = (d: Date) => {
  const y = d.getFullYear();
  const m = `${d.getMonth() + 1}`.padStart(2, '0');
  const day = `${d.getDate()}`.padStart(2, '0');
  return `${y}-${m}-${day}`;
};

export default function MyPage() {
  // 현재 보이는 기준 월 (초기값: 오늘)
  const [currentDate, setCurrentDate] = useState(new Date());

  // API에서 가져오는 카운터들
  const [programDay, setProgramDay] = useState<number>(0);
  const [streak, setStreak] = useState<number>(0);
  const [trainedDays, setTrainDays] = useState<number>(0);
  const [dayIndexByDate, setDayIndexByDate] = useState<Record<string, number>>({});

  // 예시 면접 예정일(필요 시 서버 값으로 교체)
  const [interviewDate] = useState<Date | null>(new Date(2025, 9, 12)); // 2025-08-13

  // 달 이동
  const goPrevMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };
  const goNextMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };
  const goToday = () => {
    setCurrentDate(new Date());
  };

  // 학습 카운터 로드
  useEffect(() => {
    const loadCounters = async () => {
      try {
        const d = await getTrainingDayCounters();
        setProgramDay(d.programDayToday);
        setStreak(d.consecutiveStreak);
        setTrainDays(
          typeof d.trainedDays === 'number'
            ? d.trainedDays
            : Object.keys(d.dayIndexByDate ?? {}).length
        );
        setDayIndexByDate(d.dayIndexByDate || {});
      } catch {
        setProgramDay(0);
        setStreak(0);
        setTrainDays(0);
        setDayIndexByDate({});
      }
    };
    loadCounters();
  }, []);

  // 요일
  const weekDays = ['일', '월', '화', '수', '목', '금', '토'];

  // 현재 달 달력 그리드 계산
  const { weeks, year, month } = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth(); // 0 = 1월
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);

    // 시작: 첫째날의 요일 기준 이전 일요일
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());

    // 끝: 마지막날 이후 토요일
    const end = new Date(last);
    end.setDate(last.getDate() + (6 - last.getDay()));

    const weeks: {
      date: number;
      fullDate: Date;
      isCurrentMonth: boolean;
      isStudyDay: boolean;
      isInterviewDay: boolean;
    }[][] = [];

    let cursor = new Date(start);
    while (cursor <= end) {
      const week = [];
      for (let i = 0; i < 7; i++) {
        const cellDate = new Date(cursor);
        const ymd = fmtYMD(cellDate);
        const isCurrentMonth = cellDate.getMonth() === month;
        const isStudyDay = Boolean(dayIndexByDate[ymd]); // 실제 학습한 날짜만 표시
        const isInterviewDay =
          interviewDate ? cellDate.getTime() === new Date(interviewDate).setHours(0, 0, 0, 0) : false;

        week.push({
          date: cellDate.getDate(),
          fullDate: cellDate,
          isCurrentMonth,
          isStudyDay,
          isInterviewDay
        });

        cursor.setDate(cursor.getDate() + 1);
      }
      weeks.push(week);
    }

    return { weeks, year, month };
  }, [currentDate, dayIndexByDate, interviewDate]);

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      {/* 상단 네비 */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-center space-x-12 py-4">
            <Link href="/" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
              홈화면
            </Link>
            <Link href="/today-interview" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
              오늘의 면접
            </Link>
            <Link href="/practice-interview" className="text-gray-600 hover:text-[#27386d] transition-colors cursor-pointer whitespace-nowrap">
              실전면접
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* 타이틀 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#27386d] mb-2">마이페이지</h1>
          <p className="text-gray-600">나의 면접 준비 현황을 확인해보세요</p>
        </div>

        <div className="grid gap-6 mb-8">
          {/* 다음 면접 예정일 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#27386d]">다음 면접 예정일</h2>
              <button className="bg-[#6ce5e8] text-[#27386d] px-4 py-2 rounded-full text-sm font-medium hover:bg-opacity-90 transition-colors cursor-pointer whitespace-nowrap">
                면접일정 추가하기
              </button>
            </div>
            <div className="flex items-center justify-center space-x-3 py-4">
              <div className="w-3 h-3 bg-[#6ce5e8] rounded-full" />
              <span className="text-xl font-bold text-[#27386d]">
                {interviewDate
                  ? `${interviewDate.getFullYear()}/${interviewDate.getMonth()}/${interviewDate.getDate()}`
                  : '미정'}
              </span>
              <span className="text-lg text-gray-700">우수성과 공유 컨퍼런스</span>
            </div>
          </div>

          {/* 연속학습/총 학습 시간 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
              <div className="w-12 h-12 bg-[#6ce5e8] rounded-full flex items-center justify-center mx-auto mb-3">
                <i className="ri-fire-line text-xl text-[#27386d]" />
              </div>
              <h3 className="text-2xl font-bold text-[#27386d] mb-1">{streak}일</h3>
              <p className="text-gray-600">연속학습</p>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
              <div className="w-12 h-12 bg-[#27386d] rounded-full flex items-center justify-center mx-auto mb-3">
                <i className="ri-time-line text-xl text-white" />
              </div>
              <h3 className="text-2xl font-bold text-[#27386d] mb-1">{streak * 12}분</h3>
              <p className="text-gray-600">총 학습 시간</p>
            </div>
          </div>

          {/* 연속학습 캘린더 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-[#27386d]">연속학습 캘린더</h2>

              {/* 달 이동 컨트롤러 */}
              <div className="flex items-center gap-2">
                <button
                  onClick={goPrevMonth}
                  className="p-2 rounded-full border text-[#27386d] hover:bg-gray-50 flex items-center justify-center"
                  title="이전 달"
                >
                  <i className="ri-arrow-left-s-line text-lg"></i>
                </button>

                <button
                  onClick={goToday}
                  className="p-2 rounded-full border text-[#27386d] hover:bg-gray-50 flex items-center justify-center"
                  title="오늘"
                >
                  <i className="ri-calendar-line text-lg"></i>
                </button>

                <button
                  onClick={goNextMonth}
                  className="p-2 rounded-full border text-[#27386d] hover:bg-gray-50 flex items-center justify-center"
                  title="다음 달"
                >
                  <i className="ri-arrow-right-s-line text-lg"></i>
                </button>
              </div>
            </div>

            <div className="max-w-sm mx-auto">
              {/* 현재 월 타이틀 */}
              <h3 className="text-center font-semibold text-[#27386d] mb-4">
                {year}년 {month + 1}월
              </h3>

              {/* 요일 헤더 */}
              <div className="grid grid-cols-7 gap-1 mb-2">
                {weekDays.map(d => (
                  <div key={d} className="text-center text-xs font-medium text-gray-500 py-2">
                    {d}
                  </div>
                ))}
              </div>

              {/* 날짜 그리드 */}
              <div className="space-y-1">
                {weeks.map((week, weekIndex) => (
                  <div key={weekIndex} className="grid grid-cols-7 gap-1">
                    {week.map((day, dayIndex) => {
                      const hasLeftConnection =
                        day.isStudyDay && dayIndex > 0 && week[dayIndex - 1]?.isStudyDay;
                      const hasRightConnection =
                        day.isStudyDay && dayIndex < 6 && week[dayIndex + 1]?.isStudyDay;

                      return (
                        <div key={dayIndex} className="relative">
                          <div
                            className={`w-8 h-8 flex items-center justify-center text-xs font-medium relative z-10 ${
                              day.isInterviewDay
                                ? 'bg-[#27386d] text-white rounded-full border-2 border-[#6ce5e8]'
                                : day.isStudyDay
                                ? 'bg-[#6ce5e8] text-[#27386d] rounded-full'
                                : day.isCurrentMonth
                                ? 'text-gray-700 hover:bg-gray-100 rounded-full cursor-pointer'
                                : 'text-gray-400'
                            }`}
                            title={fmtYMD(day.fullDate)}
                          >
                            {day.date}
                          </div>

                          {/* 좌우 연결선 */}
                          {day.isStudyDay && (
                            <div className="absolute top-1/2 transform -translate-y-1/2 z-0">
                              {hasLeftConnection && (
                                <div className="absolute right-1/2 w-4 h-1 bg-[#6ce5e8]" />
                              )}
                              {hasRightConnection && (
                                <div className="absolute left-1/2 w-4 h-1 bg-[#6ce5e8]" />
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 text-center space-y-1">
              <p className="text-sm text-[#6ce5e8] font-medium">
                연속학습: 총 {trainedDays}일
              </p>
              {/* <p className="text-sm text-[#27386d] font-medium">
                프로그램 기준 현재 {programDay}일차
              </p> */}
              {interviewDate && (
                <p className="text-sm text-[#27386d] font-medium">
                  면접예정: {interviewDate.getMonth() + 1}월 {interviewDate.getDate()}일
                </p>
              )}
            </div>
          </div>

          {/* 훈련기록 이동 */}
          <div className="text-center">
            <Link
              href="/mypage/training-history"
              className="inline-flex items-center px-8 py-3 bg-[#27386d] text-white font-semibold rounded-full hover:bg-opacity-90 transition-colors cursor-pointer whitespace-nowrap"
            >
              <i className="ri-history-line w-5 h-5 flex items-center justify-center mr-2" />
              나의 훈련기록
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
