"""최종 보고서 조립 (프론트엔드 응답 형식)"""
from typing import Dict, List

from .models import UserInfo, QuestionAnalysis


class ReportBuilder:
    """최종 보고서 구성 클래스"""

    def get_grade_message(self, score: int) -> str:
        """점수별 메시지 생성 - 프론트엔드와 동일한 로직"""
        if score >= 95:
            return "S등급 - 면접관도 감탄할만큼 완벽한 응답이네요!"
        elif score >= 90:
            return "A+등급 - 완벽에 가까운 훌륭한 답변입니다!"
        elif score >= 85:
            return "A등급 - 우수한 답변이에요! 약간만 다듬으면 더 좋아질 수 있어요."
        elif score >= 80:
            return "B+등급 - 매일 연습하면 더좋은 답변을 할 수 있어요!"
        elif score >= 75:
            return "B등급 - 기본기는 탄탄해요! 조금 더 연습해보세요."
        elif score >= 70:
            return "C+등급 - 시작이 반이에요. 한걸음씩 함께 노력해요!"
        else:
            return "C등급 - 꾸준한 연습으로 실력을 키워나가세요!"

    def build_final_report(
            self,
            user_info: UserInfo,
            # question_analyses: List[QuestionAnalysis],
            aggregated_scores: Dict,
            ai_advice: Dict,
            # step_names: List[str]

    ) -> Dict:
        """
        최종 보고서 데이터를 프론트엔드 형식에 맞게 구성

        Args:
            user_info: 사용자 정보
            question_analyses: 질문별 분석 결과
            aggregated_scores: 집계된 점수
            ai_advice: LLM 생성 조언
            step_names: 단계명 리스트

        Returns:
            최종 보고서 딕셔너리
        """
        grade_message = self.get_grade_message(aggregated_scores['total_evaluation']['total_score'])

        # 질문별 데이터에 LLM 생성 요약 추가
        enhanced_question_scores = []
        for i, qa_dict in enumerate(aggregated_scores['question_scores']):
            enhanced_qa = qa_dict.copy()
            enhanced_qa['summary'] = ai_advice['question_summaries'][i]  # 15자 내외 요약 추가
            enhanced_question_scores.append(enhanced_qa)

        # 최종 보고서 구성
        final_report = {
            # 사용자 기본 정보
            'user_info': {
                'user_id': user_info.user_id,
                'user_nickname': user_info.user_nickname,
                'interview_id': user_info.interview_id,
                'interview_date': user_info.interview_date,
                'interview_duration': user_info.interview_duration
            },

            # 종합 평가 점수
            # 'total_evaluation': aggregated_scores['total_evaluation'],  # 밑줄이랑 중복

            # 등급 메시지
            'total_evaluation': {
                **aggregated_scores['total_evaluation'],
                'grade_message': grade_message
            },

            # 4영역 평균 점수들
            'area_scores': aggregated_scores['area_scores'],

            # 6개 질문별 상세 점수들 (요약 포함)
            'question_scores': enhanced_question_scores,

            # LLM이 생성한 AI 조언들
            'ai_advice': {
                'personalized_message': ai_advice['personalized_message'],
                'top_strengths': ai_advice['top_strengths'],
                'improvements': ai_advice['improvements']
            }
        }

        return final_report
