import logging
"""최종 보고서 생성 진입점 - 파싱/집계/조언/조립을 오케스트레이션"""
from typing import Dict, List

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from .models import UserInfo, QuestionAnalysis
from .data_parser import DataParser
from .score_aggregator import ScoreAggregator
from .gemini_advisor import GeminiAdvisor
from .report_builder import ReportBuilder



logger = logging.getLogger(__name__)

class FinalEvaluationGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = GEMINI_MODEL_NAME
        self.generation_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=10000,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        self.step_names = [
            '아이스브레이킹', '질문 1', '질문 2', '질문 3',
            '질문 4', '질문 5', '질문 6', '최종 평가'
        ]

    def generate_final_report(self, user_info: UserInfo, question_analyses: List[QuestionAnalysis]) -> Dict:
        try:
            # 1. 점수 집계
            score_aggregator = ScoreAggregator()
            aggregated_scores = score_aggregator.aggregate_all_scores(question_analyses)

            # 2. AI 조언 생성
            gemini_advisor = GeminiAdvisor(self.client, self.model_name, self.generation_config)
            ai_advice = gemini_advisor.generate_all_advice(
                question_analyses,
                aggregated_scores,
                user_info.user_nickname
            )

            # 3. 보고서 구성
            report_builder = ReportBuilder()
            final_report = report_builder.build_final_report(
                user_info,
                question_analyses,
                aggregated_scores,
                ai_advice,
                self.step_names
            )

            return final_report

        except Exception as e:
            logger.exception("최종 보고서 생성 실패")
            raise

    def generate_final_report_from_json(self, interview_data) -> Dict:
        try:
            # 1. 데이터 파싱
            data_parser = DataParser()
            parsed_data = data_parser.parse_interview_data(interview_data)
            user_info = parsed_data['user_info']
            question_analyses = parsed_data['question_analyses']

            # 2. 보고서 생성
            return self.generate_final_report(user_info, question_analyses)

        except Exception as e:
            logger.exception("JSON 데이터 처리 실패")
            raise
