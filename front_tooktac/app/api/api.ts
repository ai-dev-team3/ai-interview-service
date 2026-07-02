// app/api/api.ts

import axios from 'axios';
import { useUser } from '@/contexts/UserContext'

// ✅ 기본 axios 인스턴스 생성
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || '/api',
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

export const startInterview = async () => {
  const response = await api.post("/start-interview");
  return response.data;
};

export const generateNextQuestion = async (questionOrder: number) => {
  const response = await api.post(`/generate-question/${questionOrder}`);
  return response.data; // { session_id, question }
};

// export const fetchEvaluationResult = async (questionId: string) => {
//   const response = await api.get(`/result/${questionId}`);
//   return response.data; // { question, user_answer, final_score, ... }
// };

export const fetchEvaluationResult = async () => {
  const response = await api.get("/result/latest");
  return response.data; // { question, user_answer, final_score, ... }
};

// 질문별 분석결과 api
export const fetchFullLatestResult = async () => {
  const response = await api.get("/result/full/latest");
  return response.data;
};

export const fetchFinalReport = async () => {
  const response = await api.post("/report/final");
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
