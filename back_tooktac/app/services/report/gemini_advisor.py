import logging
"""Gemini 기반 AI 조언 생성 (병렬 호출)"""
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from .models import QuestionAnalysis



logger = logging.getLogger(__name__)

class GeminiAdvisor:
    """Gemini AI를 활용한 AI 조언 생성 클래스 - 병렬 처리 최적화"""

    def __init__(self, client, model_name, generation_config):
        self.client = client
        self.model_name = model_name
        self.generation_config = generation_config

    def generate_all_advice(
            self,
            question_analyses: List["QuestionAnalysis"],
            aggregated_scores: Dict,
            user_nickname: str
    ) -> Dict:
        # 공통 데이터 전처리 (한 번만 계산)
        analysis_summary = self._prepare_analysis_summary(question_analyses)
        question_summary = self._prepare_question_summary(question_analyses)

        # 병렬 처리로 4개 API 호출 동시 실행
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 4개 작업을 동시에 제출
            future_personalized = executor.submit(
                self._generate_personalized_message_with_summary,
                question_summary, aggregated_scores['total_evaluation'], user_nickname
            )
            future_strengths = executor.submit(
                self._generate_top_strengths_with_summary,
                analysis_summary, user_nickname
            )
            future_improvements = executor.submit(
                self._generate_improvements_with_summary,
                analysis_summary, user_nickname
            )
            future_summaries = executor.submit(
                self._generate_question_summaries,
                question_analyses
            )

            # 모든 결과를 기다림 (가장 오래 걸리는 작업 시간만큼만 소요)
            personalized_message = future_personalized.result()
            top_strengths = future_strengths.result()
            improvements = future_improvements.result()
            question_summaries = future_summaries.result()

        return {
            'personalized_message': personalized_message,
            'top_strengths': top_strengths,
            'improvements': improvements,
            'question_summaries': question_summaries
        }

    def _prepare_analysis_summary(self, question_analyses: List["QuestionAnalysis"]) -> str:
        """강점/개선점 분석용 공통 요약 생성 (한 번만 계산)"""
        return "\n".join([
            f"{qa.name} ({qa.type}, {qa.final_score}점):\n"
            f"- 텍스트: {qa.detail_analysis['text']['score']}점\n"
            f"- 음성: {qa.detail_analysis['voice']['score']}점\n"
            f"- 영상: {qa.detail_analysis['video']['score']}점\n"
            f"- 감정: {qa.detail_analysis['emotion']['score']}점\n"
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

    def _generate_personalized_message_with_summary(
            self,
            question_summary: str,
            total_evaluation: Dict,
            user_nickname: str
    ) -> str:
        prompt = f"""
{user_nickname}님의 면접 전체를 분석해서 개인 맞춤 조언을 생성해주세요.

전체 점수: {total_evaluation['total_score']}점 ({total_evaluation['rank']})

각 질문별 분석:
{question_summary}

조언 생성 요구사항:
- 정확히 200자 내외
- {user_nickname}님의 데이터에서만 발견되는 구체적 특징 기반
- 가장 시급한 개선점 1개 + 활용할 최고 강점 1개 명시
- 실행 가능한 구체적 액션 아이템 포함
- 따뜻하되 예리한 분석이 느껴지는 전문적 톤
"""
        return self._call_gemini(prompt).strip()

    def _generate_top_strengths_with_summary(self, analysis_summary: str, user_nickname: str) -> List[Dict]:
        prompt = f"""
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
        response = self._call_gemini(prompt).strip()
        return self._parse_json_response(response, "강점")

    def _generate_improvements_with_summary(self, analysis_summary: str, user_nickname: str) -> List[Dict]:
        prompt = f"""
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
        response = self._call_gemini(prompt).strip()
        return self._parse_json_response(response, "개선점")

    def _generate_question_summaries(self, question_analyses: List["QuestionAnalysis"]) -> List[str]:
        # 질문 요약은 각각 독립적이므로 병렬 처리
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for qa in question_analyses:
                prompt = f"""
    면접 답변을 한 줄로 요약해주세요.

    질문: {qa.question}
    답변: {qa.my_answer}
    점수: {qa.final_score}점
    강점: {', '.join(qa.strengths)}

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
                futures.append(executor.submit(self._call_gemini, prompt))

            # 순서대로 결과 수집
            return [future.result().strip() for future in futures]

    def _parse_json_response(self, response: str, error_type: str) -> List[Dict]:
        """JSON 파싱 통합 처리"""
        response = self._clean_json_block(response)
        try:
            parsed = json.loads(response)
            logger.debug("JSON 파싱 성공 (%s)", error_type)
            return parsed
        except json.JSONDecodeError as e:
            logger.error("JSON 파싱 실패 (%s): %s / Gemini 원본 응답: %s", error_type, e, response)
            raise Exception(f"Gemini 응답이 JSON 형식이 아닙니다. ({error_type})")

    def _call_gemini(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )

            if not response.candidates:
                raise Exception("Gemini 응답이 비어있습니다.")

            candidate = response.candidates[0]
            if candidate.finish_reason.name != "STOP":
                raise Exception(f"Gemini 응답이 정상 종료되지 않았습니다. finish_reason: {candidate.finish_reason.name}")

            if not candidate.content.parts:
                raise Exception("Gemini 응답이 Part를 포함하지 않습니다.")

            return candidate.content.parts[0].text.strip()

        except Exception as e:
            raise Exception(f"Gemini API 호출 실패: {str(e)}")

    def _clean_json_block(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text.removeprefix("```json").removesuffix("```")
        return text.strip().strip("`").strip()


# %%
