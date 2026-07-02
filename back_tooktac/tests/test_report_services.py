"""리포트 서비스 비즈니스 로직 유닛 테스트 (LLM 호출 없음)"""
import pytest

from app.services.report.data_parser import DataParser
from app.services.report.models import QuestionAnalysis
from app.services.report.report_builder import ReportBuilder
from app.services.report.score_aggregator import ScoreAggregator
from app.services.text.orchestrator import preprocess_input


def _detail(text=80, voice=70, video=90, emotion=60):
    return {
        "text": {"score": text, "similarity": 75, "accuracy": 80, "understanding": 85},
        "voice": {"score": voice, "speed": {"score": 70}, "fluency": {"score": 75}, "tone": {"score": 65}},
        "video": {"score": video, "gaze_rate": {"percentage": 88}, "shoulder_posture": {"score": 90}, "hand_posture": {"score": 92}},
        "emotion": {"score": emotion, "positive": 50, "neutral": 30, "nervous": 15, "negative": 5},
    }


def _qa(n, score=80):
    return QuestionAnalysis(
        question_id=f"q{n}", name=f"질문 {n}", type="개념설명형",
        final_score=score, question="질문?", my_answer="답변",
        model_answer="모범답안", detail_analysis=_detail(),
        feedback="피드백", strengths=["강점"], improvements=["개선점"],
    )


class TestScoreAggregator:
    def test_aggregate_all_scores(self):
        result = ScoreAggregator().aggregate_all_scores([_qa(i) for i in range(1, 7)])

        assert result["area_scores"]["text"]["total"] == 80
        assert result["area_scores"]["voice"]["total"] == 70
        assert result["area_scores"]["video"]["total"] == 90
        assert result["area_scores"]["emotion"]["total"] == 60
        # (80+70+90+60)/4 = 75
        assert result["total_evaluation"]["total_score"] == 75
        assert result["total_evaluation"]["grade"] == "B"
        assert result["total_evaluation"]["rank"] == "상위 35%"
        assert len(result["question_scores"]) == 6

    @pytest.mark.parametrize("score,grade", [
        (95, "S"), (90, "A+"), (85, "A"), (80, "B+"), (75, "B"), (70, "C+"), (69, "C"),
    ])
    def test_grade_boundaries(self, score, grade):
        assert ScoreAggregator()._calculate_grade(score) == grade


class TestDataParser:
    def _question_dict(self, n):
        return {
            "question_id": f"q{n}", "question_number": n,
            "question_type": "기술형", "final_score": 80,
            "question_text": "질문?", "user_answer": "답변",
            "model_answer": "모범답안", "detail_analysis": _detail(),
            "feedback": "피드백", "strengths": ["s"], "improvements": ["i"],
        }

    def test_parse_dict_format(self):
        data = {
            "user_info": {"user_id": "u1", "user_nickname": "닉", "interview_id": "i1",
                          "interview_date": "2026-07-02", "interview_duration": 20},
            "questions": [self._question_dict(n) for n in range(1, 7)],
        }
        parsed = DataParser().parse_interview_data(data)
        assert parsed["user_info"].user_nickname == "닉"
        assert len(parsed["question_analyses"]) == 6
        assert parsed["question_analyses"][0].final_score == 80

    def test_parse_invalid_json_string(self):
        with pytest.raises(ValueError):
            DataParser().parse_interview_data("{broken json")

    def test_parse_dict_without_user_info(self):
        with pytest.raises(ValueError):
            DataParser().parse_interview_data({"questions": []})

    def test_validate_detail_analysis_missing_area(self):
        with pytest.raises(ValueError):
            DataParser().validate_detail_analysis({"text": {"score": 1}})


class TestReportBuilder:
    @pytest.mark.parametrize("score,keyword", [
        (95, "S등급"), (90, "A+등급"), (85, "A등급"),
        (80, "B+등급"), (75, "B등급"), (70, "C+등급"), (50, "C등급"),
    ])
    def test_grade_message(self, score, keyword):
        assert keyword in ReportBuilder().get_grade_message(score)


def test_preprocess_input_type_mapping():
    out = preprocess_input(" 질문 ", " 답변 ", "행동형")
    assert out["question"] == "질문"
    assert out["user_answer"] == "답변"
    assert out["evaluation_type"] == "situational"
    assert preprocess_input("q", "a", "기술형")["evaluation_type"] == "technical"
    assert preprocess_input("q", "a", "미지정")["evaluation_type"] == "technical"
