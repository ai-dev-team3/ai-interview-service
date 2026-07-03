import logging
"""최종 보고서 생성 진입점 - 파싱/집계/조언/조립을 오케스트레이션"""
from typing import Dict, List

from .models import UserInfo, QuestionAnalysis
from .data_parser import DataParser
from .score_aggregator import ScoreAggregator
from .gemini_advisor import GeminiAdvisor
from .report_builder import ReportBuilder



logger = logging.getLogger(__name__)

class FinalEvaluationGenerator:
    def __init__(self):
        # 단계 이름은 면접 구성 단일 소스(plan.STEP_NAMES)를 따른다
        from app.services.interview.plan import STEP_NAMES

        self.step_names = list(STEP_NAMES)

    def generate_final_report(self, user_info: UserInfo, question_analyses: List[QuestionAnalysis]) -> Dict:
        try:
            # 1. 점수 집계
            score_aggregator = ScoreAggregator()
            aggregated_scores = score_aggregator.aggregate_all_scores(question_analyses)

            # 2. AI 조언 생성
            gemini_advisor = GeminiAdvisor()
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
