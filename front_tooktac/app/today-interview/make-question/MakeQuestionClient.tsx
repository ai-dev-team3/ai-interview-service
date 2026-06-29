"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { startInterview, generateNextQuestion } from "@/api/api";

export default function MakeQuestionClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams?.get("next"); // 예: /today-interview/2
  const runningRef = useRef(false);

  useEffect(() => {
    // next 파라미터가 없으면 실행하지 않음
    if (!next) return;

    // StrictMode 중복 호출 방지(개발 모드에서 2회 실행되는 것을 1회로 고정)
    if (runningRef.current) return;
    runningRef.current = true;

    // open redirect 방지: 외부 URL이 들어오지 않도록 가볍게 검증
    if (!next.startsWith("/")) {
      console.error("유효하지 않은 next 파라미터");
      return;
    }

    const generateQuestionAndRedirect = async () => {
      try {
        const pathname = next.split("?")[0];
        const questionNumber = Number(pathname.split("/").pop());

        if (!Number.isFinite(questionNumber)) {
          throw new Error("질문 번호 파싱 실패");
        }

        let result;
        if (questionNumber === 1) {
          result = await startInterview();
        } else if (questionNumber >= 2 && questionNumber <= 6) {
          result = await generateNextQuestion(questionNumber);
        } else {
          throw new Error("지원하지 않는 질문 번호입니다.");
        }

        const { session_id, question } = result;
        const target = `${pathname}?session=${session_id}&question=${encodeURIComponent(
          question || ""
        )}`;

        // history를 쌓지 않으려면 replace를 사용(선호)
        router.replace(target);
      } catch (e) {
        console.error("질문 생성 오류:", e);
        // router.replace("/error"); // 필요 시 에러 페이지로 이동
      }
    };

    generateQuestionAndRedirect();
  }, [router, next]);

  return (
    <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center">
      <div className="w-24 h-24 bg-gradient-to-r from-[#6ce5e8] to-[#27386d] rounded-full flex items-center justify-center mb-8 animate-spin">
        <div className="w-16 h-16 bg-[#e7f8ff] rounded-full flex items-center justify-center">
          <i className="ri-mic-line text-2xl text-[#27386d]"></i>
        </div>
      </div>
      <h2 className="text-2xl font-bold text-[#27386d] mb-2">다음 질문을 생성 중입니다...</h2>
      <p className="text-[#27386d]/70">곧 새로운 면접 질문으로 넘어갑니다.</p>
    </div>
  );
}
