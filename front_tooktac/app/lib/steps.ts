/** 한 번의 연습 면접에서 답변할 수 있는 질문 수 (자기소개 포함). 백엔드 plan.py와 일치. */
export const MAX_INTERVIEW_QUESTIONS = 7;

/** 면접 진행 단계 이름 (아이스브레이킹 + 질문 N개 + 최종 평가) */
export function buildSteps(totalQuestions: number): string[] {
  return [
    '아이스브레이킹',
    ...Array.from({ length: totalQuestions }, (_, i) => `질문 ${i + 1}`),
    '최종 평가',
  ];
}
