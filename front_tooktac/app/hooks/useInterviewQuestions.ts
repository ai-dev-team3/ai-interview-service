import { useEffect, useState } from 'react';
import { InterviewQuestion, getSessionQuestions, getStoredQuestions } from '@/api/api';

type State = {
  questions: InterviewQuestion[] | null;
  loading: boolean;
  error: boolean;
};

/**
 * 현재 세션의 질문 목록.
 *
 * 면접 시작 시 sessionStorage에 저장해 두지만, 하드 리로드로 잃을 수 있으므로
 * 그때는 서버(GET /interview/questions)에서 되찾는다.
 */
export function useInterviewQuestions(): State {
  const [questions, setQuestions] = useState<InterviewQuestion[] | null>(() => getStoredQuestions());
  const [loading, setLoading] = useState(questions === null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (questions !== null) return;

    let cancelled = false;
    getSessionQuestions()
      .then((data) => {
        if (!cancelled) setQuestions(data.questions);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [questions]);

  return { questions, loading, error };
}
