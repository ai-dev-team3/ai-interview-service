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
    assert body["status"] == "done"
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


def test_full_result_with_explicit_session_id(auth_client, db_session, test_user):
    """더 최신 세션이 있어도 명시한 session_id 기준으로 조회"""
    old_session, _ = _seed_full_result(db_session, test_user.id)
    db_session.add(InterviewSession(user_id=test_user.id))  # 더 최신 빈 세션
    db_session.commit()

    res = auth_client.get("/result/full/latest", params={"session_id": old_session.id})
    assert res.status_code == 200
    assert res.json()["session_id"] == old_session.id

    # 명시 없이 조회하면 최신 세션(질문 없음) → 404
    res = auth_client.get("/result/full/latest")
    assert res.status_code == 404


def test_full_latest_result_status_processing(auth_client, db_session, test_user):
    """평가 결과가 아직 없으면 status=processing"""
    session = InterviewSession(user_id=test_user.id)
    db_session.add(session)
    db_session.flush()
    db_session.add(InterviewQuestion(
        session_id=session.id, question_order=1,
        question_text="질문", question_type="개념설명형",
    ))
    db_session.commit()

    res = auth_client.get("/result/full/latest")
    assert res.status_code == 200
    assert res.json()["status"] == "processing"


def test_full_latest_result_status_failed(auth_client, db_session, test_user):
    """최소 기록(model_answer 빈 값)만 있으면 status=failed"""
    session = InterviewSession(user_id=test_user.id)
    db_session.add(session)
    db_session.flush()
    question = InterviewQuestion(
        session_id=session.id, question_order=1,
        question_text="질문", question_type="개념설명형",
    )
    db_session.add(question)
    db_session.flush()
    db_session.add(EvaluationResult(
        user_id=test_user.id, session_id=session.id, question_id=question.id,
        question_order=1, similarity=0.0, intent_score=0.0, knowledge_score=0.0,
        final_text_score=0, model_answer="", strengths="음성 인식 불가",
        improvements="", final_feedback="", speed_score=0, filler_score=0,
        pitch_score=0, final_speech_score=0,
        speed_label="없음", fluency_label="없음", tone_label="없음",
    ))
    db_session.commit()

    res = auth_client.get("/result/full/latest")
    assert res.status_code == 200
    assert res.json()["status"] == "failed"


def test_full_latest_result_requires_auth(client):
    res = client.get("/result/full/latest")
    assert res.status_code == 401
