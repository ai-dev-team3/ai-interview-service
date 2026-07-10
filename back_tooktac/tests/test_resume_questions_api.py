"""이력서 질문 풀 CRUD API 테스트 — LLM 호출은 모킹"""
import pytest

from app.repository.resume import Resume, ResumeQuestion
from app.services.interview.plan import DEFAULT_QUESTION_TEXT, DEFAULT_QUESTION_TYPE
from app.services.interview.question_generator import ResumeQuestionGenerationError

FAKE_STRUCTURED = {"skills": ["Python"], "career": {}, "projects": [],
                   "self_introduction": {}, "desired_position": {}, "education": {}}

FAKE_GENERATED = [
    {"question_text": "GIL을 설명해주세요.", "question_type": "개념설명형"},
    {"question_text": "FastAPI를 어떻게 썼나요?", "question_type": "기술형"},
]


class FakeStructurer:
    def structure(self, content):
        return dict(FAKE_STRUCTURED)


class FakeQuestionGenerator:
    calls: list = []

    def generate(self, structured, existing=None):
        type(self).calls.append(list(existing or []))
        return [dict(q) for q in FAKE_GENERATED]


class FailingQuestionGenerator:
    def generate(self, structured, existing=None):
        raise ResumeQuestionGenerationError("mock failure")


class FakeClassifier:
    """항상 상황형으로 분류하는 페이크"""
    def classify(self, question_text):
        return "상황형"


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    FakeQuestionGenerator.calls = []
    monkeypatch.setattr("app.services.resume.resume_service.ResumeStructurer", FakeStructurer)
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeQuestionGenerator", FakeQuestionGenerator
    )
    monkeypatch.setattr("app.api.resume.QuestionTypeClassifier", FakeClassifier)


@pytest.fixture
def resume(db_session, test_user):
    """구조화까지 끝났지만 질문은 아직 생성 전인 이력서"""
    r = Resume(user_id=test_user.id, filename="r.pdf", content="이력서 원문",
               structured=dict(FAKE_STRUCTURED), questions_generated=False)
    r.questions.append(ResumeQuestion(
        question_text=DEFAULT_QUESTION_TEXT, question_type=DEFAULT_QUESTION_TYPE,
        is_default=True, sort_order=0,
    ))
    db_session.add(r)
    db_session.commit()
    return r


# ---------- GET ----------

def test_get_lazily_generates_questions(auth_client, resume, db_session):
    body = auth_client.get("/resume/questions").json()

    assert body["resume_id"] == resume.id
    texts = [q["question_text"] for q in body["questions"]]
    assert texts[0] == DEFAULT_QUESTION_TEXT
    assert body["questions"][0]["is_default"] is True
    assert texts[1:] == [q["question_text"] for q in FAKE_GENERATED]

    db_session.refresh(resume)
    assert resume.questions_generated is True


def test_get_passes_existing_questions_to_generator(auth_client, resume):
    auth_client.get("/resume/questions")
    # 생성기는 기본 자기소개 질문을 "기존 질문"으로 넘겨받아야 한다
    assert FakeQuestionGenerator.calls == [[DEFAULT_QUESTION_TEXT]]


def test_get_does_not_regenerate_on_second_call(auth_client, resume):
    auth_client.get("/resume/questions")
    auth_client.get("/resume/questions")
    assert len(FakeQuestionGenerator.calls) == 1


def test_deleted_questions_do_not_come_back(auth_client, resume):
    body = auth_client.get("/resume/questions").json()
    generated_ids = [q["id"] for q in body["questions"] if not q["is_default"]]
    for qid in generated_ids:
        assert auth_client.delete(f"/resume/questions/{qid}").status_code == 204

    again = auth_client.get("/resume/questions").json()
    assert [q["question_text"] for q in again["questions"]] == [DEFAULT_QUESTION_TEXT]
    assert len(FakeQuestionGenerator.calls) == 1  # 재생성하지 않는다


def test_get_survives_generation_failure(auth_client, resume, monkeypatch):
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeQuestionGenerator", FailingQuestionGenerator
    )
    body = auth_client.get("/resume/questions").json()
    # 생성이 실패해도 자기소개 질문만으로 면접을 시작할 수 있어야 한다
    assert [q["question_text"] for q in body["questions"]] == [DEFAULT_QUESTION_TEXT]


# ---------- POST ----------

def test_post_adds_question_with_classified_type(auth_client, resume):
    res = auth_client.post("/resume/questions", json={"question_text": "  장애가 나면 어떻게 하시겠습니까?  "})
    assert res.status_code == 201
    body = res.json()
    assert body["question_text"] == "장애가 나면 어떻게 하시겠습니까?"
    assert body["question_type"] == "상황형"  # FakeClassifier
    assert body["is_default"] is False
    assert body["sort_order"] > 0


def test_post_does_not_check_for_duplicates(auth_client, resume):
    """중복 판정은 LLM 생성 경로에서만 한다 — 직접 추가는 검사하지 않는다."""
    first = auth_client.post("/resume/questions", json={"question_text": "오버피팅을 설명해주세요"})
    second = auth_client.post("/resume/questions", json={"question_text": "오버피팅을 설명해주세요"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_post_rejects_empty_text(auth_client, resume):
    assert auth_client.post("/resume/questions", json={"question_text": ""}).status_code == 422


def test_post_without_resume_returns_400(auth_client):
    res = auth_client.post("/resume/questions", json={"question_text": "질문"})
    assert res.status_code == 400


# ---------- PATCH ----------

def test_patch_updates_text_and_reclassifies(auth_client, resume, db_session):
    created = auth_client.post("/resume/questions", json={"question_text": "원래 질문"}).json()

    res = auth_client.patch(f"/resume/questions/{created['id']}", json={"question_text": "바뀐 질문"})
    assert res.status_code == 200
    assert res.json()["question_text"] == "바뀐 질문"
    assert res.json()["question_type"] == "상황형"  # 재분류 결과


def test_patch_default_question_rejected(auth_client, resume):
    default_id = resume.questions[0].id
    res = auth_client.patch(f"/resume/questions/{default_id}", json={"question_text": "바꿔볼까"})
    assert res.status_code == 400
    assert "기본" in res.json()["detail"]


# ---------- DELETE ----------

def test_delete_removes_question(auth_client, resume, db_session):
    created = auth_client.post("/resume/questions", json={"question_text": "지울 질문"}).json()

    assert auth_client.delete(f"/resume/questions/{created['id']}").status_code == 204
    assert db_session.get(ResumeQuestion, created["id"]) is None


def test_delete_default_question_rejected(auth_client, resume):
    default_id = resume.questions[0].id
    res = auth_client.delete(f"/resume/questions/{default_id}")
    assert res.status_code == 400


# ---------- 소유권 ----------

def test_cannot_touch_other_users_question(auth_client, resume, db_session, test_user):
    from app.repository.user import User
    import datetime

    other = User(username="other", password="p", name="n", email="o@e.com",
                 nickname="other", birthdate=datetime.date(2000, 1, 1), desired_job="백엔드")
    db_session.add(other)
    db_session.flush()
    other_resume = Resume(user_id=other.id, content="남의 이력서")
    other_resume.questions.append(ResumeQuestion(
        question_text="남의 질문", question_type="기술형", is_default=False, sort_order=1,
    ))
    db_session.add(other_resume)
    db_session.commit()
    other_qid = other_resume.questions[0].id

    assert auth_client.patch(f"/resume/questions/{other_qid}", json={"question_text": "x"}).status_code == 404
    assert auth_client.delete(f"/resume/questions/{other_qid}").status_code == 404
