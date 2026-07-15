'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api, {
  getCoverLetters,
  getResumeStatus,
  getInterviewSchedules,
  createInterviewSchedule,
  updateInterviewSchedule,
  deleteInterviewSchedule,
  type CoverLetter,
  type InterviewSchedule,
} from '@/api/api';
import { useState, useEffect, useMemo, useRef } from 'react';

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

const formatScheduleDate = (value: string) => {
  const d = new Date(value);
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
};

const sortSchedules = (schedules: InterviewSchedule[]) =>
  [...schedules].sort(
    (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
  );

export default function MyPage() {
  const router = useRouter();

  // 현재 보이는 기준 월 (초기값: 오늘)
  const [currentDate, setCurrentDate] = useState(new Date());

  // API에서 가져오는 카운터들
  const [, setProgramDay] = useState<number>(0);
  const [streak, setStreak] = useState<number>(0);
  const [trainedDays, setTrainDays] = useState<number>(0);
  const [dayIndexByDate, setDayIndexByDate] = useState<Record<string, number>>({});

  // 면접 일정 상태
  const [interviewSchedules, setInterviewSchedules] = useState<InterviewSchedule[]>([]);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [scheduleDate, setScheduleDate] = useState(fmtYMD(new Date()));
  const [scheduleDescription, setScheduleDescription] = useState('');
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<InterviewSchedule | null>(null);
  const [deletingScheduleId, setDeletingScheduleId] = useState<number | null>(null);
  const schedulesWithinMonth = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const monthLater = new Date(today);
    monthLater.setMonth(monthLater.getMonth() + 1);

    return sortSchedules(interviewSchedules).filter((schedule) => {
      const scheduledAt = new Date(schedule.scheduled_at);
      return scheduledAt >= today && scheduledAt <= monthLater;
    });
  }, [interviewSchedules]);
  const interviewDateSet = useMemo(
    () => new Set(interviewSchedules.map((schedule) => fmtYMD(new Date(schedule.scheduled_at)))),
    [interviewSchedules]
  );

  // 이력서 등록 상태
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [hasCoverLetter, setHasCoverLetter] = useState<boolean | null>(null);
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
  const [selectedCoverLetterId, setSelectedCoverLetterId] = useState('');
  const [careerChecking, setCareerChecking] = useState(false);
  const [toast, setToast] = useState('');
  const careerSectionRef = useRef<HTMLDivElement>(null);
  const selectedCoverLetter = useMemo(
    () => coverLetters.find(letter => String(letter.id) === selectedCoverLetterId) ?? null,
    [coverLetters, selectedCoverLetterId]
  );

  // 이력서/자소서 등록 여부 로드
  useEffect(() => {
    const loadReadinessData = async () => {
      try {
        const [d, letters] = await Promise.all([
          getResumeStatus(),
          getCoverLetters(),
        ]);
        setHasResume(d.has_resume);
        setHasCoverLetter(letters.length > 0);
        setCoverLetters(letters);
        setSelectedCoverLetterId(prev => {
          if (prev && letters.some(letter => String(letter.id) === prev)) {
            return prev;
          }
          return letters[0] ? String(letters[0].id) : '';
        });
      } catch {
        setHasResume(null);
        setHasCoverLetter(null);
        setCoverLetters([]);
        setSelectedCoverLetterId('');
      }
    };
    loadReadinessData();
  }, []);

  // 가드 리다이렉트(?resume=required)로 진입한 경우 안내 + 준비 자료 상태로 스크롤
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('resume') === 'required') {
      setToast('이력서와 자소서를 계정 관리에서 등록한 뒤 이용할 수 있습니다.');
      setTimeout(() => careerSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, []);

  // 토스트 자동 닫힘
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  const handleCareerReadinessClick = async () => {
    setCareerChecking(true);
    try {
      const status = await getResumeStatus();
      setHasResume(status.has_resume);
      setHasCoverLetter(status.has_cover_letter);

      if (!status.ready_for_career_diagnosis) {
        alert('자소서와 이력서를 등록 후 이용하시기 바랍니다.');
        setTimeout(() => careerSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        return;
      }

      const coverLetterId = Number(selectedCoverLetterId);
      if (!coverLetterId || !Number.isFinite(coverLetterId)) {
        alert('진단에 사용할 자소서를 선택해주세요.');
        setTimeout(() => careerSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        return;
      }

      window.sessionStorage.setItem('careerDiagnosisCoverLetterId', String(coverLetterId));
      router.push('/career-diagnosis');
    } catch (err: any) {
      if (err?.response?.status === 401) {
        router.push('/login');
        return;
      }
      alert('취업 준비도 확인 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setCareerChecking(false);
    }
  };

  const openScheduleModal = () => {
    setEditingSchedule(null);
    setScheduleDate(fmtYMD(new Date()));
    setScheduleDescription('');
    setIsScheduleModalOpen(true);
  };

  const openEditScheduleModal = (schedule: InterviewSchedule) => {
    setEditingSchedule(schedule);
    setScheduleDate(fmtYMD(new Date(schedule.scheduled_at)));
    setScheduleDescription(schedule.description ?? '');
    setIsScheduleModalOpen(true);
  };

  const closeScheduleModal = () => {
    if (scheduleSaving) return;
    setEditingSchedule(null);
    setIsScheduleModalOpen(false);
  };

  const handleScheduleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!scheduleDate) {
      setToast('면접 날짜를 선택해주세요.');
      return;
    }

    setScheduleSaving(true);
    try {
      const payload = {
        scheduled_at: scheduleDate,
        description: scheduleDescription.trim(),
      };
      const saved = editingSchedule
        ? await updateInterviewSchedule(editingSchedule.id, payload)
        : await createInterviewSchedule(payload);

      setInterviewSchedules(prev =>
        editingSchedule
          ? sortSchedules(prev.map(schedule => schedule.id === saved.id ? saved : schedule))
          : sortSchedules([...prev, saved])
      );
      setCurrentDate(new Date(saved.scheduled_at));
      setEditingSchedule(null);
      setIsScheduleModalOpen(false);
      setToast(editingSchedule ? '면접 일정이 수정되었습니다.' : '면접 일정이 추가되었습니다.');
    } catch {
      setToast(
        editingSchedule
          ? '면접 일정 수정에 실패했습니다. 다시 시도해주세요.'
          : '면접 일정 추가에 실패했습니다. 다시 시도해주세요.'
      );
    } finally {
      setScheduleSaving(false);
    }
  };

  const handleScheduleDelete = async (schedule: InterviewSchedule) => {
    if (deletingScheduleId !== null) return;

    const confirmed = window.confirm(`${formatScheduleDate(schedule.scheduled_at)} 면접 일정을 삭제할까요?`);
    if (!confirmed) return;

    setDeletingScheduleId(schedule.id);
    try {
      await deleteInterviewSchedule(schedule.id);
      setInterviewSchedules(prev => prev.filter(item => item.id !== schedule.id));
      if (editingSchedule?.id === schedule.id) {
        setEditingSchedule(null);
        setIsScheduleModalOpen(false);
      }
      setToast('면접 일정이 삭제되었습니다.');
    } catch {
      setToast('면접 일정 삭제에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setDeletingScheduleId(null);
    }
  };

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

  // 면접 일정 로드
  useEffect(() => {
    const loadInterviewSchedules = async () => {
      try {
        const schedules = await getInterviewSchedules();
        setInterviewSchedules(sortSchedules(schedules));
      } catch {
        setInterviewSchedules([]);
      }
    };
    loadInterviewSchedules();
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

    const cursor = new Date(start);
    while (cursor <= end) {
      const week = [];
      for (let i = 0; i < 7; i++) {
        const cellDate = new Date(cursor);
        const ymd = fmtYMD(cellDate);
        const isCurrentMonth = cellDate.getMonth() === month;
        const isStudyDay = Boolean(dayIndexByDate[ymd]); // 실제 학습한 날짜만 표시
        const isInterviewDay = interviewDateSet.has(ymd);

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
  }, [currentDate, dayIndexByDate, interviewDateSet]);

  return (
    <div className="min-h-screen bg-[#e7f8ff]">
      {/* 안내 토스트 */}
      {toast && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 bg-[#27386d] text-white px-6 py-3 rounded-full shadow-lg text-sm font-medium">
          {toast}
        </div>
      )}

      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
          <form
            onSubmit={handleScheduleSubmit}
            className="w-full max-w-md bg-white rounded-2xl p-6 shadow-xl"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-[#27386d]">
                {editingSchedule ? '면접 일정 수정' : '면접 일정 추가'}
              </h2>
              <button
                type="button"
                onClick={closeScheduleModal}
                className="w-9 h-9 rounded-full flex items-center justify-center text-gray-500 hover:bg-gray-100"
                aria-label="닫기"
              >
                <i className="ri-close-line text-xl" />
              </button>
            </div>

            <div className="space-y-4">
              <label className="block">
                <span className="block text-sm font-medium text-[#27386d] mb-2">날짜</span>
                <input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => setScheduleDate(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm"
                  required
                />
              </label>

              <label className="block">
                <span className="block text-sm font-medium text-[#27386d] mb-2">설명</span>
                <textarea
                  value={scheduleDescription}
                  onChange={(e) => setScheduleDescription(e.target.value)}
                  maxLength={255}
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6ce5e8] text-sm resize-none"
                  placeholder="예: 우수성과 공유 컨퍼런스"
                />
              </label>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                type="button"
                onClick={closeScheduleModal}
                className="px-4 py-2 rounded-full border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={scheduleSaving}
                className="px-4 py-2 rounded-full bg-[#6ce5e8] text-[#27386d] text-sm font-medium hover:bg-opacity-90 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {scheduleSaving
                  ? editingSchedule ? '수정 중...' : '추가 중...'
                  : editingSchedule ? '수정하기' : '추가하기'}
              </button>
            </div>
          </form>
        </div>
      )}

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
          {/* 이력서 / 자소서 관리 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div className="flex min-w-0 items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#e7f8ff] text-[#27386d]">
                  <i className="ri-file-user-line text-2xl" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-[#27386d]">이력서/자소서 관리</h2>
                  <p className="mt-1 text-sm leading-6 text-gray-600">
                    면접과 취업 준비도 진단에 사용할 이력서와 자기소개서를 등록하고 수정합니다.
                  </p>
                </div>
              </div>
              <Link
                href="/mypage/account"
                className="inline-flex h-11 shrink-0 items-center justify-center rounded-full bg-[#27386d] px-5 text-sm font-semibold text-white transition-colors hover:bg-opacity-90 whitespace-nowrap"
              >
                <i className="ri-file-edit-line mr-2 text-base leading-none" />
                이력서/자소서 관리
              </Link>
            </div>
          </div>

          {/* 취업 준비도 진단 */}
          <div ref={careerSectionRef} className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#27386d] text-white">
                <i className="ri-bar-chart-box-line text-2xl" />
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-[#27386d]">AI 취업 준비도 진단</h2>
                <p className="mt-1 text-sm leading-6 text-gray-600">
                  등록된 이력서와 선택한 자기소개서를 바탕으로 취업 준비도와 보완 액션을 확인합니다.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3 border-t border-gray-100 pt-5 md:grid-cols-[minmax(0,1fr)_160px] md:items-end">
              <label className="min-w-0">
                <span className="mb-2 block text-sm font-semibold text-[#27386d]">
                  진단에 사용할 자소서
                </span>
                <div className="relative">
                  <i className="ri-file-list-3-line pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-base text-gray-400" />
                  <select
                    value={selectedCoverLetterId}
                    onChange={(e) => setSelectedCoverLetterId(e.target.value)}
                    disabled={careerChecking || coverLetters.length === 0}
                    className="h-11 w-full min-w-0 rounded-full border border-gray-200 bg-white pl-11 pr-4 text-sm font-semibold text-[#27386d] outline-none transition-colors focus:border-[#27386d] focus:ring-2 focus:ring-[#e7f8ff] disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
                  >
                    {coverLetters.length === 0 ? (
                      <option value="">등록된 자소서가 없습니다</option>
                    ) : (
                      coverLetters.map((letter) => (
                        <option key={letter.id} value={letter.id}>
                          {letter.title}
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </label>
              <button
                type="button"
                onClick={handleCareerReadinessClick}
                disabled={careerChecking}
                className="inline-flex h-11 min-w-0 items-center justify-center rounded-full bg-[#27386d] px-5 text-sm font-semibold text-white transition-colors hover:bg-opacity-90 disabled:cursor-not-allowed disabled:opacity-60 whitespace-nowrap"
              >
                <i className="ri-arrow-right-circle-line mr-2 text-base leading-none" />
                <span>{careerChecking ? '확인 중...' : '준비도 확인'}</span>
              </button>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  hasResume ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}
              >
                이력서 {hasResume ? '준비 완료' : '필요'}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  hasCoverLetter ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}
              >
                자소서 {hasCoverLetter ? '선택 가능' : '필요'}
              </span>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              {selectedCoverLetter
                ? `선택된 자소서: ${selectedCoverLetter.title}`
                : '자소서를 등록하면 이곳에서 진단에 사용할 항목을 선택할 수 있습니다.'}
            </p>
          </div>

          {/* 다음 면접 예정일 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#27386d]">한 달 내 면접 일정</h2>
              <button
                onClick={openScheduleModal}
                className="bg-[#6ce5e8] text-[#27386d] px-4 py-2 rounded-full text-sm font-medium hover:bg-opacity-90 transition-colors cursor-pointer whitespace-nowrap"
              >
                면접일정 추가하기
              </button>
            </div>
            {schedulesWithinMonth.length > 0 ? (
              <div className="space-y-3 py-2">
                {schedulesWithinMonth.map((schedule) => (
                  <div
                    key={schedule.id}
                    className="flex items-start gap-3 rounded-lg border border-gray-100 px-4 py-3"
                  >
                    <div className="mt-2 w-3 h-3 bg-[#6ce5e8] rounded-full shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-lg font-bold text-[#27386d]">
                        {formatScheduleDate(schedule.scheduled_at)}
                      </div>
                      <div className="text-sm text-gray-700 break-words">
                        {schedule.description || '등록된 설명이 없습니다.'}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => openEditScheduleModal(schedule)}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-[#27386d] hover:bg-[#e7f8ff] disabled:opacity-60"
                        aria-label="면접 일정 수정"
                        title="수정"
                        disabled={deletingScheduleId === schedule.id}
                      >
                        <i className="ri-pencil-line text-lg" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleScheduleDelete(schedule)}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-red-500 hover:bg-red-50 disabled:opacity-60 disabled:cursor-not-allowed"
                        aria-label="면접 일정 삭제"
                        title="삭제"
                        disabled={deletingScheduleId === schedule.id}
                      >
                        <i className={deletingScheduleId === schedule.id ? 'ri-loader-4-line text-lg' : 'ri-delete-bin-line text-lg'} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-gray-500">
                한 달 내 등록된 면접 일정이 없습니다.
              </div>
            )}
          </div>

          {/* 계정 관리 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-[#27386d]">계정 관리</h2>
                <p className="mt-1 text-sm text-gray-600">
                  아이디 확인, 비밀번호 변경, 회원 탈퇴를 관리합니다.
                </p>
              </div>
              <Link
                href="/mypage/account"
                className="inline-flex items-center px-4 py-2 rounded-full bg-[#27386d] text-white text-sm font-medium hover:bg-opacity-90 transition-colors whitespace-nowrap"
              >
                <i className="ri-settings-3-line mr-2" />
                계정 관리
              </Link>
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
              {schedulesWithinMonth.length > 0 && (
                <p className="text-sm text-[#27386d] font-medium">
                  한 달 내 면접예정: {schedulesWithinMonth.length}건
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
