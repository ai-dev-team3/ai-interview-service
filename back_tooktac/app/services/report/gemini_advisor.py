"""LLM 기반 AI 조언 생성 (LCEL 병렬 체인)"""
import logging
from typing import Dict, List, Optional

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from app.services.llm import get_chat_model

from .models import QuestionAnalysis

logger = logging.getLogger(__name__)

_PERSONALIZED_TEMPLATE = """
{user_nickname}님의 면접 전체를 분석해서 개인 맞춤 조언을 생성해주세요.

전체 점수: {total_score}점 ({rank})

각 질문별 분석:
{question_summary}

조언 생성 요구사항:
- 정확히 200자 내외
- {user_nickname}님의 데이터에서만 발견되는 구체적 특징 기반
- 가장 시급한 개선점 1개 + 활용할 최고 강점 1개 명시
- 실행 가능한 구체적 액션 아이템 포함
- 따뜻하되 예리한 분석이 느껴지는 전문적 톤
"""

_STRENGTHS_TEMPLATE = """
{user_nickname}님의 6개 질문 면접 분석 결과를 종합해서 TOP 3 강점을 선정해주세요.

강점top3:
{analysis_summary}

요구사항:
1. 전체적으로 가장 뛰어난 TOP 3 강점 선정
2. 중복 제거 및 개인 특성 반영
3. 각각 제목(간결) + 설명(구체적) + 점수
4. 반드시 20자 내외로 간결하고 직관적이게 작성

⚠️ 반드시 다음 JSON 형태로만 출력하세요. 설명 문구 없이 JSON 객체만 출력해주세요.

[
  {{"title": "강점 제목", "description": "상세 설명", "score": 94}},
  {{"title": "강점 제목", "description": "상세 설명", "score": 91}},
  {{"title": "강점 제목", "description": "상세 설명", "score": 89}}
]
"""

_IMPROVEMENTS_TEMPLATE = """
{user_nickname}님의 6개 질문 면접 분석 결과를 종합해서 우선순위별 TOP 3 개선점을 선정해주세요.

개선점top3:
{analysis_summary}

요구사항:
1. 우선순위별 TOP 3 개선점 (1순위가 가장 중요)
2. 중복 제거 및 개인화
3. 각각 제목(간결) + 설명(구체적) + 점수
4. 반드시 15자 내외의 한문장으로 작성
5. 간결하고 직관적인 표현의 한문장

⚠️ 반드시 다음 JSON 형태로만 출력하세요. 설명 문구 없이 JSON 객체만 출력해주세요.

[
  {{"priority": 1, "title": "개선점 제목", "description": "상세 설명", "score": 78}},
  {{"priority": 2, "title": "개선점 제목", "description": "상세 설명", "score": 82}},
  {{"priority": 3, "title": "개선점 제목", "description": "상세 설명", "score": 85}}
]
"""

_QUESTION_SUMMARY_TEMPLATE = """
    면접 답변을 한 줄로 요약해주세요.

    질문: {question}
    답변: {my_answer}
    점수: {final_score}점
    강점: {strengths}

    요구사항:
    - 정확히 15자 내외
    - 답변의 핵심 강점을 표현
    - 완성된 문장으로 작성
    - "~했습니다" 또는 "~되었습니다" 형태

    예시:
    - "개념 설명이 명확하고 체계적이었습니다"
    - "기술적 이해도가 뛰어나고 정확했습니다"
    - "문제해결 과정이 논리적이었습니다"
    - "실무 경험이 잘 반영된 답변이었습니다"
    - "창의적 사고가 돋보이는 답변이었습니다"

    위 형태로 한 문장만 출력하세요:
    """


class GeminiAdvisor:
    """LLM을 활용한 AI 조언 생성 클래스 - LCEL 병렬 체인으로 동시 실행"""

    def __init__(self, llm: Optional[Runnable] = None):
        # 기존 GenerateContentConfig(temperature=0.7, top_p=0.8, top_k=40, max_output_tokens=10000) 유지
        self.llm = llm if llm is not None else get_chat_model(
            primary="gemini", temperature=0.7, top_p=0.8, top_k=40, max_tokens=10000,
        )
        str_parser = StrOutputParser()
        json_parser = JsonOutputParser()

        self._personalized_chain = (
            ChatPromptTemplate.from_template(_PERSONALIZED_TEMPLATE) | self.llm | str_parser
        )
        self._strengths_chain = (
            ChatPromptTemplate.from_template(_STRENGTHS_TEMPLATE) | self.llm | json_parser
        )
        self._improvements_chain = (
            ChatPromptTemplate.from_template(_IMPROVEMENTS_TEMPLATE) | self.llm | json_parser
        )
        self._summary_chain = (
            ChatPromptTemplate.from_template(_QUESTION_SUMMARY_TEMPLATE) | self.llm | str_parser
        )

        # 4개 조언을 병렬로 생성 (기존 ThreadPoolExecutor 병렬 호출 대체)
        self._advice_graph = RunnableParallel(
            personalized_message=RunnableLambda(self._run_personalized),
            top_strengths=RunnableLambda(self._run_strengths),
            improvements=RunnableLambda(self._run_improvements),
            question_summaries=RunnableLambda(self._run_summaries),
        )

    def generate_all_advice(
            self,
            question_analyses: List["QuestionAnalysis"],
            aggregated_scores: Dict,
            user_nickname: str
    ) -> Dict:
        # 공통 데이터 전처리 (한 번만 계산)
        context = {
            "question_analyses": question_analyses,
            "analysis_summary": self._prepare_analysis_summary(question_analyses),
            "question_summary": self._prepare_question_summary(question_analyses),
            "total_evaluation": aggregated_scores["total_evaluation"],
            "user_nickname": user_nickname,
        }
        return self._advice_graph.invoke(context)

    def _run_personalized(self, context: Dict) -> str:
        total_evaluation = context["total_evaluation"]
        return self._personalized_chain.invoke({
            "user_nickname": context["user_nickname"],
            "total_score": total_evaluation["total_score"],
            "rank": total_evaluation["rank"],
            "question_summary": context["question_summary"],
        }).strip()

    def _run_strengths(self, context: Dict) -> List[Dict]:
        return self._strengths_chain.invoke({
            "user_nickname": context["user_nickname"],
            "analysis_summary": context["analysis_summary"],
        })

    def _run_improvements(self, context: Dict) -> List[Dict]:
        return self._improvements_chain.invoke({
            "user_nickname": context["user_nickname"],
            "analysis_summary": context["analysis_summary"],
        })

    def _run_summaries(self, context: Dict) -> List[str]:
        # 질문 요약은 각각 독립적이므로 batch로 동시 실행
        inputs = [
            {
                "question": qa.question,
                "my_answer": qa.my_answer,
                "final_score": qa.final_score,
                "strengths": ", ".join(qa.strengths),
            }
            for qa in context["question_analyses"]
        ]
        return [summary.strip() for summary in self._summary_chain.batch(inputs)]

    def _prepare_analysis_summary(self, question_analyses: List["QuestionAnalysis"]) -> str:
        """강점/개선점 분석용 공통 요약 생성 (한 번만 계산)"""
        return "\n".join([
            f"{qa.name} ({qa.type}, {qa.final_score}점):\n"
            f"- 텍스트: {qa.detail_analysis['text']['score']}점\n"
            f"- 음성: {qa.detail_analysis['voice']['score']}점\n"
            f"- 영상: {qa.detail_analysis['video']['score']}점\n"
            f"- 강점: {', '.join(qa.strengths)}\n"
            f"- 개선점: {', '.join(qa.improvements)}"
            for qa in question_analyses
        ])

    def _prepare_question_summary(self, question_analyses: List["QuestionAnalysis"]) -> str:
        """개인 맞춤 조언용 질문 요약 생성 (한 번만 계산)"""
        return "\n".join([
            f"- {qa.name} ({qa.type}, {qa.final_score}점): {qa.feedback}\n"
            f"  강점: {', '.join(qa.strengths)}\n"
            f"  개선점: {', '.join(qa.improvements)}"
            for qa in question_analyses
        ])
