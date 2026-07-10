"""리포트 조회 API 통합 테스트 + 순수 헬퍼 유닛 테스트"""
from datetime import datetime

from app.repository.interview import InterviewSession
from app.repository.report import (
    FinalReportSummary,
    ReportAreaScore,
    ReportImprovement,
    ReportStrength,
)
from app.services.report.score_utils import avg_or_zero, normalize_question_type, to_number_score


# ---------- 순수 헬퍼 유닛 테스트 ----------

def test_to_number_score_variants():
    assert to_number_score(87) == 87
    assert to_number_score(87.6) == 88
    assert to_number_score({"score": 90}) == 90
    assert to_number_score({"value": 75.2}) == 75
    assert to_number_score({"unknown": 1}) == 0
    assert to_number_score("bad") == 0


def test_normalize_qtype():
    assert normalize_question_type("개념설명형") == "concept"
    assert normalize_question_type("기술형") == "technical"
    assert normalize_question_type("상황형") == "situation"
    assert normalize_question_type("행동형") == "behavior"
    assert normalize_question_type("") == "concept"  # 기본값
    assert normalize_question_type("알 수 없는 유형") == "concept"  # 폴백


def test_avg_or_zero():
    assert avg_or_zero([80, 90]) == 85
    assert avg_or_zero([]) == 0


# ---------- 리포트 조회 API ----------

def _seed_report(db, user_id):
    # started_at은 모델 기본값(naive UTC) 사용 — 저장 규약과 일치시킴
    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.flush()

    summary = FinalReportSummary(
        user_id=user_id, session_id=session.id, total_score=85,
        rank="상위 15%", grade="A", grade_message="우수한 답변이에요!",
        personalized_advice="구체적 사례를 더 들어보세요.",
    )
    db.add(summary)
    db.flush()

    db.add(ReportStrength(report_id=summary.id, title="논리력", description="논리적입니다", score=90))
    db.add(ReportImprovement(report_id=summary.id, priority=1, title="속도", description="말이 빠릅니다", score=60))
    for name, score in (("text", 88), ("voice", 80), ("video", 84)):
        db.add(ReportAreaScore(report_id=summary.id, area_name=name, score=score))
    db.commit()
    return session, summary


def test_report_by_date(auth_client, db_session, test_user):
    _seed_report(db_session, test_user.id)
    # 조회 날짜 기준은 KST (UTC 저장 → KST 날짜 변환 규약)
    from app.utils.time_utils import kst_today

    today = kst_today().strftime("%Y-%m-%d")

    res = auth_client.get(f"/report/date/{today}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["totalScore"] == 85
    assert data["rank"] == "상위 15%"
    assert data["areas"] == {"text": 88, "voice": 80, "video": 84}
    assert data["topStrengths"] == ["논리적입니다"]
    assert data["improvements"] == ["말이 빠릅니다"]


def test_report_by_date_bad_format_400(auth_client):
    res = auth_client.get("/report/date/2026-13-99")
    assert res.status_code == 400


def test_report_by_date_not_found_404(auth_client):
    res = auth_client.get("/report/date/2000-01-01")
    assert res.status_code == 404
