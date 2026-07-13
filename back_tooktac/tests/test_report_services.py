"""리포트 서비스 비즈니스 로직 유닛 테스트 (LLM 호출 없음)"""
import pytest

from app.services.report.data_parser import DataParser
from app.services.report.models import QuestionAnalysis
from app.services.report.report_builder import ReportBuilder
from app.services.report.score_aggregator import ScoreAggregator
from app.services.text.orchestrator import preprocess_input


def _detail(text=80, voice=70, video=90):
    return {
        "text": {"score": text, "similarity": 75, "accuracy": 80, "understanding": 85},
        "voice": {"score": voice, "speed": {"score": 70}, "fluency": {"score": 75}, "tone": {"score": 65}},
        "video": {"score": video, "gaze_rate": {"percentage": 88}, "shoulder_posture": {"score": 90}, "hand_posture": {"score": 92}},
    }


def _qa(n, score=80):
    return QuestionAnalysis(
        question_id=f"q{n}", name=f"질문 {n}", type="개념설명형",
        final_score=score, question="질문?", my_answer="답변",
        model_answer="모범답안", detail_analysis=_detail(),
        feedback="피드백", strengths=["강점"], improvements=["개선점"],
    )


class TestScoreAggregator:
    @pytest.mark.parametrize("total", [1, 3, 6, 7])
    def test_aggregate_all_scores(self, total):
        result = ScoreAggregator().aggregate_all_scores([_qa(i) for i in range(1, total + 1)])

        assert result["area_scores"]["text"]["total"] == 80
        assert result["area_scores"]["voice"]["total"] == 70
        assert result["area_scores"]["video"]["total"] == 90
        # (80+70+90)/3 = 80 — 질문 수와 무관하다
        assert result["total_evaluation"]["total_score"] == 80
        assert result["total_evaluation"]["grade"] == "B+"
        assert result["total_evaluation"]["rank"] == "상위 25%"
        assert len(result["question_scores"]) == total

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

    def _list_payload(self, n):
        rows = [self._question_dict(i) for i in range(1, n + 1)]
        rows[0]["user_info"] = {"user_id": "u1", "user_nickname": "닉", "interview_id": "i1",
                                "interview_date": "2026-07-02", "interview_duration": 20}
        return rows

    @pytest.mark.parametrize("total", [1, 3, 7])
    def test_parse_list_format_accepts_variable_count(self, total):
        parsed = DataParser().parse_interview_data(self._list_payload(total))
        assert len(parsed["question_analyses"]) == total

    def test_parse_list_format_rejects_empty(self):
        with pytest.raises(ValueError):
            DataParser().parse_interview_data([])

    def test_parse_list_format_rejects_over_max(self):
        with pytest.raises(ValueError, match="1~7개"):
            DataParser().parse_interview_data(self._list_payload(8))

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


def test_분석이_유실된_문항이_있어도_리포트가_만들어진다(db_session, test_user):
    """실전 면접은 분석이 백그라운드에서 돈다.

    서버가 재시작하거나 분석이 유실되면 그 문항의 EvaluationResult 가 영영 안 생긴다.
    그 한 문항 때문에 면접 전체의 리포트를 못 보게 되면 안 된다.
    """
    from app.repository.analysis import EvaluationResult, VideoEvaluationResult
    from app.repository.interview import InterviewAnswer, InterviewQuestion, InterviewSession
    from app.services.report.interview_data_formatter import generate_interview_json_from_session

    session = InterviewSession(user_id=test_user.id, mode="real")
    db_session.add(session)
    db_session.flush()

    # 1번: 정상 분석
    q1 = InterviewQuestion(session_id=session.id, question_order=1,
                           question_text="질문 1", question_type="기술형")
    # 2번: 분석이 유실됨 (EvaluationResult / VideoEvaluationResult 없음)
    q2 = InterviewQuestion(session_id=session.id, question_order=2,
                           question_text="질문 2", question_type="기술형")
    db_session.add_all([q1, q2])
    db_session.flush()

    db_session.add(InterviewAnswer(session_id=session.id, question_id=q1.id,
                                   user_id=test_user.id, question_order=1, answer_text="답변 1"))
    db_session.add(EvaluationResult(
        user_id=test_user.id, session_id=session.id, question_id=q1.id, question_order=1,
        similarity=0.8, intent_score=80, knowledge_score=80, final_text_score=80,
        model_answer="모범", strengths="강점", improvements="개선", final_feedback="피드백",
        speed_score=30, filler_score=30, pitch_score=15, final_speech_score=75,
        speed_label="적절", fluency_label="양호", tone_label="적절",
    ))
    db_session.add(VideoEvaluationResult(
        user_id=test_user.id, session_id=session.id, question_id=q1.id, question_order=1,
        gaze_score=80, shoulder_warning=1, hand_warning=0,
        posture_score=90, final_video_score=85,
    ))
    db_session.commit()

    data = generate_interview_json_from_session(db_session, session.id)

    analyses = data["question_analyses"]
    assert len(analyses) == 2, "분석 안 된 문항이 통째로 빠지면 안 된다"

    assert analyses[0]["analysis_failed"] is False
    assert analyses[0]["user_answer"] == "답변 1"

    assert analyses[1]["analysis_failed"] is True
    assert analyses[1]["final_score"] == 0
    assert analyses[1]["user_answer"] == ""
    assert "완료되지 않았습니다" in analyses[1]["feedback"]
