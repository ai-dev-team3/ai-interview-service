'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';

// 클라이언트에서만 동작하도록 dynamic import 설정
const QuestionClientPage = dynamic(() => import('./QuestionClientPage'), { ssr: false });

export default function QuestionClientWrapper() {
    // URL 파라미터에서 questionId 추출
    const params = useParams();
    const questionId = params?.questionId as string;

    return <QuestionClientPage questionId={questionId} />;
}
