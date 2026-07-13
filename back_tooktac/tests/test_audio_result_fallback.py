"""audio.py — 분석이 끝나지 못했을 때 최소 결과를 남기는지 검증.

결과 행이 없으면 /result/full이 영원히 status="processing"을 반환하고
프론트 폴러가 멈추지 않는다(무한 로딩). 이 회귀를 막는 테스트다.
"""
import asyncio

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import sessionmaker

import app.api.audio as audio
from app.services.interview.result_store import save_result_if_missing as _save_result_if_missing
from app.repository.analysis import EvaluationResult
from app.repository.interview import InterviewQuestion, InterviewSession


def _seed(db, user_id):
    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.flush()
    question = InterviewQuestion(
        session_id=session.id, question_order=1,
        question_text="자기소개 해주세요", question_type="행동형",
    )
    db.add(question)
    db.commit()
    return session, question


def _full_result(user_id, session, question):
    return EvaluationResult(
        user_id=user_id, session_id=session.id, question_id=question.id,
        question_order=1, similarity=0.8, intent_score=8.0, knowledge_score=7.0,
        final_text_score=80, model_answer="모범답안", strengths="강점",
        improvements="개선점", final_feedback="총평",
        speed_score=80, filler_score=90, pitch_score=70, final_speech_score=80,
        speed_label="적절", fluency_label="유창", tone_label="안정",
    )


def test_writes_minimal_result_when_none_exists(db_session, test_user):
    session, question = _seed(db_session, test_user.id)

    _save_result_if_missing(db_session, test_user.id, session.id, question, reason="연결이 끊김")

    row = db_session.query(EvaluationResult).filter_by(question_id=question.id).one()
    # model_answer가 비어 있어야 /result/full이 status="failed"를 준다
    assert row.model_answer == ""
    assert "연결이 끊김" in row.final_feedback
    assert row.final_text_score == 0


def test_does_not_overwrite_existing_result(db_session, test_user):
    """정상 저장 후 응답 단계에서 터진 경우, 결과를 최소 행으로 덮어쓰면 안 된다."""
    session, question = _seed(db_session, test_user.id)
    db_session.add(_full_result(test_user.id, session, question))
    db_session.commit()

    _save_result_if_missing(db_session, test_user.id, session.id, question, reason="처리 오류")

    rows = db_session.query(EvaluationResult).filter_by(question_id=question.id).all()
    assert len(rows) == 1
    assert rows[0].model_answer == "모범답안"


def test_no_row_written_when_question_unknown(db_session, test_user):
    """질문을 특정하기 전에 실패했으면 남길 곳이 없다 — 조용히 넘어간다."""
    session, _ = _seed(db_session, test_user.id)

    _save_result_if_missing(db_session, test_user.id, session.id, None, reason="세션 없음")
    _save_result_if_missing(db_session, test_user.id, None, None, reason="세션 없음")
    _save_result_if_missing(None, None, None, None, reason="DB 없음")

    assert db_session.query(EvaluationResult).count() == 0


def test_minimal_result_makes_full_result_report_failed(auth_client, db_session, test_user):
    """저장된 최소 행이 실제로 status=failed 로 읽히는지 — 폴러가 멈추는 조건."""
    session, question = _seed(db_session, test_user.id)
    _save_result_if_missing(db_session, test_user.id, session.id, question, reason="연결이 끊김")

    body = auth_client.get("/result/full", params={"question_order": 1}).json()
    assert body["status"] == "failed"


# ---------- 핸들러 배선 (연결 끊김 재현) ----------

class _DisconnectingWebSocket:
    """오디오를 보내기 전에 끊어지는 WebSocket. 실제 프론트 버그를 흉내낸다."""

    def __init__(self, params):
        self.query_params = params
        self.sent = []

    async def accept(self):
        pass

    async def receive_bytes(self):
        raise WebSocketDisconnect(code=1005)

    async def send_json(self, payload):
        self.sent.append(payload)


def test_disconnect_before_audio_writes_failed_row(db_session, test_user, engine, monkeypatch):
    """오디오 도착 전에 끊겨도 결과 행이 남아야 한다 — 무한 로딩 회귀 테스트."""
    session, question = _seed(db_session, test_user.id)

    # audio.py는 get_db가 아니라 SessionLocal을 직접 쓴다 → 테스트 엔진으로 바꿔친다
    monkeypatch.setattr(audio, "SessionLocal", sessionmaker(bind=engine, autoflush=False))

    async def fake_auth(_ws):
        return test_user.id

    monkeypatch.setattr(audio, "get_user_id_from_websocket", fake_auth)

    ws = _DisconnectingWebSocket({"question_id": "1", "session_id": str(session.id)})
    asyncio.run(audio.websocket_endpoint(ws))

    # 핸들러는 별도 세션에서 커밋한다. db_session의 스냅샷을 끝내야 그 커밋이 보인다.
    db_session.commit()

    row = db_session.query(EvaluationResult).filter_by(question_id=question.id).one()
    assert row.model_answer == ""
    assert "연결이 끊김" in row.final_feedback
