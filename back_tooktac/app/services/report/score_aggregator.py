"""4영역 점수 집계 (단순 평균)"""
import statistics
from typing import Dict, List

from .models import QuestionAnalysis


class ScoreAggregator:
    """점수 집계 전용 클래스 - 가중치 적용 없이 단순 평균만 계산"""

    def aggregate_all_scores(self, question_analyses: List[QuestionAnalysis]) -> Dict:
        """
        모든 점수를 집계해서 최종 평가 점수 계산

        Args:
            question_analyses: 6개 질문의 분석 결과 (이미 가중치 적용된 점수 포함)

        Returns:
            집계된 점수 딕셔너리
        """
        # 4영역 평균 점수 계산
        area_scores = self._calculate_area_averages(question_analyses)

        # 최종 종합 점수 계산
        total_score = self._calculate_total_score(area_scores)

        # 상위 퍼센트 및 등급 계산
        rank = self._calculate_rank(total_score)
        grade = self._calculate_grade(total_score)

        return {
            'question_scores': [self._format_question_score(qa) for qa in question_analyses],
            'area_scores': area_scores,
            'total_evaluation': {
                'total_score': total_score,
                'rank': rank,
                'grade': grade
            }
        }

    def _calculate_area_averages(self, question_analyses: List[QuestionAnalysis]) -> Dict:
        """4영역(텍스트, 음성, 영상, 감정)의 평균 점수 계산"""

        # 각 영역별 점수들을 수집
        text_scores = []
        voice_scores = []
        video_scores = []
        emotion_scores = []

        # 세부 지표별 점수들도 수집
        text_similarity = []
        text_accuracy = []
        text_understanding = []

        voice_speed = []
        voice_fluency = []
        voice_tone = []

        video_gaze_rate = []
        video_shoulder_scores = []
        video_hand_scores = []

        emotion_positive = []
        emotion_neutral = []
        emotion_nervous = []
        emotion_negative = []

        # 각 질문에서 점수 추출
        for qa in question_analyses:
            detail = qa.detail_analysis

            # 텍스트 영역
            text_scores.append(detail['text']['score'])
            text_similarity.append(detail['text']['similarity'])
            text_accuracy.append(detail['text']['accuracy'])
            text_understanding.append(detail['text']['understanding'])

            # 음성 영역
            voice_scores.append(detail['voice']['score'])
            voice_speed.append(detail['voice']['speed']['score'])
            voice_fluency.append(detail['voice']['fluency']['score'])
            voice_tone.append(detail['voice']['tone']['score'])

            # 영상 영역
            video_scores.append(detail['video']['score'])
            video_gaze_rate.append(detail['video']['gaze_rate']['percentage'])
            video_shoulder_scores.append(detail['video']['shoulder_posture']['score'])
            video_hand_scores.append(detail['video']['hand_posture']['score'])

            # 감정 영역
            emotion_scores.append(detail['emotion']['score'])
            emotion_positive.append(detail['emotion']['positive'])
            emotion_neutral.append(detail['emotion']['neutral'])
            emotion_nervous.append(detail['emotion']['nervous'])
            emotion_negative.append(detail['emotion']['negative'])

        # 평균 계산 후 반환
        return {
            'text': {
                'total': round(statistics.mean(text_scores)),
                'similarity': round(statistics.mean(text_similarity)),
                'accuracy': round(statistics.mean(text_accuracy)),
                'understanding': round(statistics.mean(text_understanding))
            },
            'voice': {
                'total': round(statistics.mean(voice_scores)),
                'speed': round(statistics.mean(voice_speed)),
                'fluency': round(statistics.mean(voice_fluency)),
                'tone': round(statistics.mean(voice_tone))
            },
            'video': {
                'total': round(statistics.mean(video_scores)),
                'gaze_rate': round(statistics.mean(video_gaze_rate)),
                # 자세는 어깨 + 손 점수의 평균
                'posture': round(statistics.mean([
                    (shoulder + hand) / 2
                    for shoulder, hand in zip(video_shoulder_scores, video_hand_scores)
                ]))
            },
            'emotion': {
                'total': round(statistics.mean(emotion_scores)),
                # 감정 비율은 전체 질문의 평균
                'positive': round(statistics.mean(emotion_positive)),
                'neutral': round(statistics.mean(emotion_neutral)),
                'nervous': round(statistics.mean(emotion_nervous)),
                'negative': round(statistics.mean(emotion_negative))
            }
        }

    def _calculate_total_score(self, area_scores: Dict) -> int:
        """4영역 점수의 단순 평균으로 최종 점수 계산"""
        total = (
                        area_scores['text']['total'] +
                        area_scores['voice']['total'] +
                        area_scores['video']['total'] +
                        area_scores['emotion']['total']
                ) / 4
        return round(total)

    def _calculate_rank(self, total_score: int) -> str:
        """점수를 기반으로 상위 몇 % 계산"""
        if total_score >= 95:
            return "상위 5%"
        elif total_score >= 90:
            return "상위 10%"
        elif total_score >= 85:
            return "상위 15%"
        elif total_score >= 80:
            return "상위 25%"
        elif total_score >= 75:
            return "상위 35%"
        elif total_score >= 70:
            return "상위 50%"
        else:
            return "하위 50%"

    def _calculate_grade(self, total_score: int) -> str:
        """점수를 기반으로 등급 계산"""
        if total_score >= 95:
            return "S"
        elif total_score >= 90:
            return "A+"
        elif total_score >= 85:
            return "A"
        elif total_score >= 80:
            return "B+"
        elif total_score >= 75:
            return "B"
        elif total_score >= 70:
            return "C+"
        else:
            return "C"

    def _format_question_score(self, qa: QuestionAnalysis) -> Dict:
        """질문별 점수를 최종 형식으로 변환"""
        return {
            'question_id': qa.question_id,
            'name': qa.name,
            'type': qa.type,
            'score': qa.final_score,  # 이미 가중치가 적용된 최종 점수
            'question': qa.question,
            'my_answer': qa.my_answer,
            'model_answer': qa.model_answer,
            'detail_analysis': qa.detail_analysis,
            'feedback': qa.feedback,
            'strengths': qa.strengths,
            'improvements': qa.improvements
        }
