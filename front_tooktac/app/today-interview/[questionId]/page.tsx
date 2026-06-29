// app/today-interview/[questionId]/page.tsx

import QuestionClientWrapper from './QuestionClientWrapper';

// 서버 컴포넌트 - 클라이언트에서만 작동하는 컴포넌트를 감쌉니다.
export default function QuestionPageWrapper() {
    return <QuestionClientWrapper />;
}
