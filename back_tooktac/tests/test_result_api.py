"""결과 조회 API 통합 테스트 — DB CRUD 검증 포함"""
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.repository.interview import (
    InterviewAnswer,
    InterviewQuestion,
    InterviewSession,
)


def _seed_full_result(db, user_id):
    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.flush()

    question = InterviewQuestion(
        session_id=session.id, question_order=1,
        question_text="자기소개 해주세요", question_type="개념설명형",
    )
    db.add(question)
    db.flush()

    db.add(InterviewAnswer(
        session_id=session.id, question_id=question.id,
        user_id=user_id, question_order=1, answer_text="안녕하세요",
    ))
    db.add(EvaluationResult(
        user_id=user_id, session_id=session.id, question_id=question.id,
        question_order=1, similarity=0.8, intent_score=8.0, knowledge_score=7.0,
        final_text_score=80, model_answer="모범답안", strengths="강점1",
        improvements="개선점1", final_feedback="총평", speed_score=80,
        filler_score=90, pitch_score=70, final_speech_score=80,
        speed_label="적절", fluency_label="유창", tone_label="안정",
    ))
    db.add(VideoEvaluationResult(
        user_id=user_id, session_id=session.id, question_id=question.id,
        question_order=1, gaze_score=90, shoulder_warning=1, hand_warning=0,
        posture_score=85, final_video_score=88, positive_rate=60,
        neutral_rate=30, negative_rate=5, tense_rate=5,
        emotion_best="긍정", emotion_score=75,
    ))
    db.commit()
    return session, question


def test_full_latest_result(auth_client, db_session, test_user):
    session, _ = _seed_full_result(db_session, test_user.id)

    res = auth_client.get("/result/full/latest")
    assert res.status_code == 200
    body = res.json()
    assert body["session_id"] == session.id
    assert body["question"] == "자기소개 해주세요"
    assert body["user_answer"] == "안녕하세요"
    assert body["model_answer"] == "모범답안"
    assert body["strengths"] == ["강점1"]
    assert body["labels"]["speed"] == "적절"
    assert body["video"]["gaze_score"] == 90
    assert body["best_emotion"] == "긍정"
    assert isinstance(body["weighted_score"], (int, float))


def test_full_latest_result_no_session_404(auth_client):
    res = auth_client.get("/result/full/latest")
    assert res.status_code == 404


def test_full_latest_result_requires_auth(client):
    res = client.get("/result/full/latest")
    assert res.status_code == 401
