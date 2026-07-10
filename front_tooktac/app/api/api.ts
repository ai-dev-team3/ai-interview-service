// app/api/api.ts

import axios from 'axios';
import { getBackendHttpBaseUrl } from '@/lib/env';

// ✅ 기본 axios 인스턴스 생성
const api = axios.create({
  baseURL: getBackendHttpBaseUrl(),
  withCredentials: true, // 필요에 따라 (예: 쿠키 인증 시)
  headers: {
    'Accept': 'application/json',
  }
});

export default api;

//  회원가입 요청 (multipart/form-data)
export const signup = async (formData: FormData) => {
  const response = await api.post('/signup', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    }
  });
  return response.data;
};

//  로그인 요청
export const login = async (formData: FormData) => {
  const response = await api.post('/login', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    }
  });
  return response.data;
};

// 아이디 중복 확인 (예시: GET /check-username?username=test)
export const checkUsername = async (username: string) => {
  const response = await api.get(`/check-username`, {
    params: { username },
  });
  return response.data;
};

export const checkAuth = async () => {
  const response = await api.get('/me');
  return response.data;
};

export type AccountInfo = {
  user_id: number;
  username: string;
  nickname: string;
  email: string | null;
  desired_job: string;
};

export const getAccount = async (): Promise<AccountInfo> => {
  const response = await api.get('/account');
  return response.data;
};

export const changePassword = async (payload: {
  current_password: string;
  new_password: string;
}) => {
  const response = await api.patch('/account/password', payload);
  return response.data;
};

export const deleteAccount = async () => {
  const response = await api.delete('/account');
  return response.data;
};

// 이력서 등록/갱신 (클라이언트에서 추출한 텍스트 전송)
export const uploadResume = async (resumeText: string, filename?: string) => {
  const form = new FormData();
  form.append('resume_text', resumeText);
  if (filename) form.append('filename', filename);
  const response = await api.post('/resume', form);
  return response.data; // { message, resume_id }
};

// 이력서 등록 여부 조회
export const getResumeStatus = async (): Promise<{ has_resume: boolean }> => {
  const response = await api.get('/resume/status');
  return response.data;
};

// ---------- 이력서 질문 풀 ----------

export type ResumeQuestion = {
  id: number;
  question_text: string;
  question_type: string;
  is_default: boolean;
  sort_order: number;
};

export const getResumeQuestions = async (): Promise<{ resume_id: number; questions: ResumeQuestion[] }> => {
  const response = await api.get('/resume/questions');
  return response.data;
};

export const addResumeQuestion = async (questionText: string): Promise<ResumeQuestion> => {
  const response = await api.post('/resume/questions', { question_text: questionText });
  return response.data;
};

export const updateResumeQuestion = async (id: number, questionText: string): Promise<ResumeQuestion> => {
  const response = await api.patch(`/resume/questions/${id}`, { question_text: questionText });
  return response.data;
};

export const deleteResumeQuestion = async (id: number): Promise<void> => {
  await api.delete(`/resume/questions/${id}`);
};

// ---------- 면접 일정 ----------

export type InterviewSchedule = {
  id: number;
  scheduled_at: string;
  description: string | null;
};

export const getInterviewSchedules = async (): Promise<InterviewSchedule[]> => {
  const response = await api.get('/interview-schedules');
  return response.data.data;
};

export const createInterviewSchedule = async (payload: {
  scheduled_at: string;
  description?: string;
}): Promise<InterviewSchedule> => {
  const response = await api.post('/interview-schedules', payload);
  return response.data.data;
};

// ---------- 면접 세션 ----------

// 진행 중인 면접 세션 ID 저장/조회 (탭·재시작 간 혼선 방지용으로 백엔드에 명시 전달)
const SESSION_KEY = 'interview_session_id';
const QUESTIONS_KEY = 'interview_questions';

export type InterviewQuestion = {
  question_order: number;
  question_text: string;
  question_type: string;
};

export const getInterviewSessionId = (): number | null => {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(SESSION_KEY);
  return raw ? Number(raw) : null;
};

const sessionParams = () => {
  const sid = getInterviewSessionId();
  return sid ? { session_id: sid } : {};
};

/** 새로고침으로 잃지 않도록 세션 질문 목록을 sessionStorage에 둔다. */
export const getStoredQuestions = (): InterviewQuestion[] | null => {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(QUESTIONS_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as InterviewQuestion[];
  } catch {
    return null;
  }
};

const storeSession = (data: { session_id: number; questions: InterviewQuestion[] }) => {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(SESSION_KEY, String(data.session_id));
  sessionStorage.setItem(QUESTIONS_KEY, JSON.stringify(data.questions));
};

/** 선택한 질문 id를 순서대로 보낸다. 자기소개는 서버가 1번에 넣는다. */
export const startInterview = async (questionIds: number[]) => {
  const response = await api.post('/start-interview', { question_ids: questionIds });
  storeSession(response.data);
  return response.data; // { session_id, total_questions, questions }
};

/** sessionStorage를 잃었을 때(하드 리로드 등) 서버에서 되찾는다. */
export const getSessionQuestions = async () => {
  const response = await api.get('/interview/questions', { params: sessionParams() });
  storeSession(response.data);
  return response.data;
};

// export const fetchEvaluationResult = async (questionId: string) => {
//   const response = await api.get(`/result/${questionId}`);
//   return response.data; // { question, user_answer, final_score, ... }
// };

export const fetchEvaluationResult = async () => {
  const response = await api.get("/result/latest");
  return response.data; // { question, user_answer, final_score, ... }
};

// 질문별 분석결과 api — 어떤 질문의 결과인지 반드시 지정한다.
// 세션의 질문이 모두 미리 만들어지므로 "가장 마지막 질문"을 보면 안 된다.
export const fetchFullResult = async (questionOrder: number) => {
  const response = await api.get("/result/full", {
    params: { ...sessionParams(), question_order: questionOrder },
  });
  return response.data;
};

export const fetchFinalReport = async () => {
  const response = await api.post("/report/final", null, { params: sessionParams() });
  return response.data;
};

// 주간 훈련 데이터 조회
export const getWeeklyTrainingData = async () => {
  const response = await api.get('/training/weekly');
  return response.data;
};

// 날짜별 보고서 조회
export const getReportByDate = async (date: string) => {
  const response = await api.get(`/report/date/${date}`);
  return response.data;
};

// 세션 ID로 보고서 조회
export const getReportBySession = async (sessionId: number) => {
  const response = await api.get(`/report/${sessionId}`);
  return response.data;
};
