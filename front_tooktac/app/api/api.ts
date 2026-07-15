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

export type ResumeDocument = {
  id: number;
  user_id: number;
  filename: string | null;
  content: string | null;
  structured: unknown;
  questions_generated: boolean;
};

export const getResume = async (): Promise<ResumeDocument> => {
  const response = await api.get('/resume');
  return response.data;
};

export const updateResume = async (
  resumeText: string,
  filename?: string,
): Promise<ResumeDocument> => {
  const form = new FormData();
  form.append('resume_text', resumeText);
  if (filename) form.append('filename', filename);
  const response = await api.patch('/resume', form);
  return response.data.resume;
};

export const deleteResume = async (): Promise<void> => {
  await api.delete('/resume');
};

export type ResumeStatus = {
  has_resume: boolean;
  has_cover_letter: boolean;
  ready_for_career_diagnosis: boolean;
};

// 이력서/자소서 등록 여부 조회
export const getResumeStatus = async (): Promise<ResumeStatus> => {
  const response = await api.get('/resume/status');
  return response.data;
};

export type JobGroup = {
  id: number;
  name: string;
  description: string | null;
};

export const getJobGroups = async (): Promise<JobGroup[]> => {
  const response = await api.get('/career/job-groups');
  return response.data;
};

export type CoverLetter = {
  id: number;
  user_id: number;
  company_name: string | null;
  job_group_id: number;
  title: string;
  items: Array<{
    question_text: string;
    answer_text: string;
  }>;
  created_at: string | null;
};

export const getCoverLetters = async (): Promise<CoverLetter[]> => {
  const response = await api.get('/cover-letters');
  return response.data;
};

export const getCoverLetter = async (id: number): Promise<CoverLetter> => {
  const response = await api.get(`/cover-letters/${id}`);
  return response.data;
};

type CoverLetterPayload = {
  job_group_id: number;
  title?: string;
  company_name?: string;
  items: Array<{
    question_text: string;
    answer_text: string;
  }>;
};

const buildCoverLetterForm = (payload: CoverLetterPayload) => {
  const form = new FormData();
  form.append('job_group_id', String(payload.job_group_id));
  if (payload.title) form.append('title', payload.title);
  if (payload.company_name) form.append('company_name', payload.company_name);
  payload.items.forEach((item) => {
    form.append('question_text', item.question_text);
    form.append('answer_text', item.answer_text);
  });
  return form;
};

export const uploadCoverLetter = async (
  payload: CoverLetterPayload,
): Promise<CoverLetter> => {
  const form = buildCoverLetterForm(payload);
  const response = await api.post('/cover-letters', form);
  return response.data;
};

export const updateCoverLetter = async (
  id: number,
  payload: CoverLetterPayload,
): Promise<CoverLetter> => {
  const form = buildCoverLetterForm(payload);
  const response = await api.patch(`/cover-letters/${id}`, form);
  return response.data;
};

export const deleteCoverLetter = async (id: number): Promise<void> => {
  await api.delete(`/cover-letters/${id}`);
};

export type CareerCriteriaResult = {
  criterion_name: string;
  description: string;
  score: number;
  raw_score?: number;
  rule_score?: number;
  weight: number;
  feedback: string;
  matched_keywords: string[];
  evidence_keywords?: string[];
  keyword_score?: number;
  specificity_score?: number;
  material_score?: number;
  qa_score?: number;
  keyword_stuffing_penalty?: number;
  criterion_cap?: number;
  job_fit_cap?: number;
  job_fit_capped?: boolean;
  llm_score?: number;
  llm_raw_score?: number;
  llm_score_cap?: number;
  llm_feedback?: string;
  llm_evidence_summary?: string;
  llm_keyword_stuffed?: boolean;
  llm_reviewed?: boolean;
};

export type CareerActionPlan = {
  title: string;
  detail: string;
};

export type CareerDiagnosis = {
  job_group: {
    id: number;
    name: string;
    description: string;
  };
  source_cover_letter?: {
    id: number;
    title: string;
    company_name: string | null;
    job_group_id: number;
  };
  desired_job: string;
  total_score: number;
  score_label: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  criteria_results: CareerCriteriaResult[];
  action_plan: CareerActionPlan[];
  job_fit?: {
    score: number;
    cap: number;
    matched_keywords: string[];
    evidence_keywords: string[];
    competing_keywords: string[];
    feedback: string;
  };
  evaluation_available?: boolean;
  unavailable_reasons?: string[];
  llm_reviewed?: boolean;
  caution: string;
};

export const createCareerDiagnosis = async (payload?: {
  cover_letter_id?: number;
}): Promise<CareerDiagnosis> => {
  const response = await api.post('/career/diagnosis', payload ?? {});
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

export const updateInterviewSchedule = async (
  id: number,
  payload: {
    scheduled_at: string;
    description?: string;
  }
): Promise<InterviewSchedule> => {
  const response = await api.patch(`/interview-schedules/${id}`, payload);
  return response.data.data;
};

export const deleteInterviewSchedule = async (id: number): Promise<void> => {
  await api.delete(`/interview-schedules/${id}`);
};

// ---------- 면접 세션 ----------

// 진행 중인 면접 세션 ID 저장/조회 (탭·재시작 간 혼선 방지용으로 백엔드에 명시 전달)
const SESSION_KEY = 'interview_session_id';
const QUESTIONS_KEY = 'interview_questions';

export type InterviewQuestion = {
  question_order: number;
  question_text: string;
  question_type: string;
  /** 직전 답변을 파고든 질문인가 (실전 면접). 표시용이며 채점과 무관하다. */
  is_follow_up?: boolean;
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

// ---------- 실전 면접 ----------
//
// 연습과 달리 질문 목록을 미리 받지 않는다. 사용자가 다음 질문을 알면 실전이 아니고,
// 꼬리질문 때문에 애초에 다음 질문이 정해져 있지도 않다. 한 번에 하나씩만 온다.
// 그래서 sessionStorage에 질문 목록을 저장하지 않는다.

export type RealInterviewStart = {
  session_id: number;
  prepare_seconds: number;
  answer_seconds: number;
  question: InterviewQuestion;
};

/**
 * 문항 수가 아니라 시간이 기준이다. 시간이 다 되면 closing=true 로 마무리 질문이 온다.
 * 마무리 답변은 채점하지 않으므로 submitClosingRemark 로 따로 올린다.
 */
export type RealAnswerResult = {
  transcript: string;
  closing: boolean;
  closing_question: string | null;
  is_follow_up: boolean;
  question: InterviewQuestion | null;
};

export type AnalysisStatus = {
  session_id: number;
  total: number;
  done: number;
  finished: boolean;
};

export const startRealInterview = async (): Promise<RealInterviewStart> => {
  const response = await api.post('/real-interview/start');
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(SESSION_KEY, String(response.data.session_id));
  }
  return response.data;
};

/**
 * 답변 오디오를 올리고 다음 질문을 받는다.
 * 서버는 STT와 꼬리질문 판단까지만 하고 응답한다(약 1~5초).
 * 무거운 분석(LLM 평가)은 뒤에서 계속 돈다.
 */
export const submitRealAnswer = async (
  sessionId: number,
  questionOrder: number,
  audio: Blob,
): Promise<RealAnswerResult> => {
  const form = new FormData();
  form.append('audio', audio, 'answer.webm');

  const response = await api.post('/real-interview/answer', form, {
    params: { session_id: sessionId, question_order: questionOrder },
  });
  return response.data;
};

/** 마지막 한마디. 채점하지 않고 전사만 남긴다. */
export const submitClosingRemark = async (sessionId: number, audio: Blob): Promise<void> => {
  const form = new FormData();
  form.append('audio', audio, 'closing.webm');
  await api.post('/real-interview/closing', form, { params: { session_id: sessionId } });
};

export const getRealAnalysisStatus = async (sessionId: number): Promise<AnalysisStatus> => {
  const response = await api.get('/real-interview/analysis-status', {
    params: { session_id: sessionId },
  });
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
