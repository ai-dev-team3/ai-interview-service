"""ResumeQuestionGenerator / QuestionTypeClassifier 단위 테스트 (실제 LLM 호출 없음)."""
import json

import pytest
from langchain_core.language_models import FakeListChatModel

from app.services.interview.plan import (
    FALLBACK_QUESTION_TYPE,
    MAX_GENERATED_QUESTIONS,
)
from app.services.interview.question_generator import (
    QuestionTypeClassifier,
    ResumeQuestionGenerationError,
    ResumeQuestionGenerator,
    _normalize_questions,
)

STRUCTURED = {
    "skills": ["Python", "FastAPI"],
    "career": {"status": "신입", "years": "0년"},
    "projects": [{"name": "면접 서비스"}],
    "self_introduction": {"strengths": "강점"},
    "desired_position": {"job_type": "백엔드"},
}


def _fake(payload) -> FakeListChatModel:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return FakeListChatModel(responses=[body])


# ---------- _normalize_questions ----------

def test_normalize_accepts_object_and_bare_list():
    item = {"question_text": "질문1", "question_type": "기술형"}
    assert _normalize_questions({"questions": [item]}) == [item]
    assert _normalize_questions([item]) == [item]


def test_normalize_coerces_unknown_type_to_fallback():
    out = _normalize_questions({"questions": [
        {"question_text": "질문", "question_type": "꼬리질문"},
    ]})
    assert out[0]["question_type"] == FALLBACK_QUESTION_TYPE


def test_normalize_drops_blank_text_and_non_dict():
    out = _normalize_questions({"questions": [
        {"question_text": "   ", "question_type": "기술형"},
        "그냥 문자열",
        {"question_type": "기술형"},
        {"question_text": "살아남는 질문", "question_type": "기술형"},
    ]})
    assert [q["question_text"] for q in out] == ["살아남는 질문"]


def test_normalize_drops_exact_duplicates_ignoring_punctuation():
    out = _normalize_questions({"questions": [
        {"question_text": "오버피팅을 설명해주세요", "question_type": "개념설명형"},
        {"question_text": "  오버피팅을 설명해주세요!  ", "question_type": "기술형"},
    ]})
    assert len(out) == 1


def test_normalize_truncates_to_max():
    items = [{"question_text": f"질문 {i}", "question_type": "기술형"} for i in range(20)]
    assert len(_normalize_questions({"questions": items})) == MAX_GENERATED_QUESTIONS


def test_normalize_returns_empty_when_not_a_list():
    assert _normalize_questions({"questions": "리스트가 아님"}) == []
    assert _normalize_questions(42) == []


# ---------- ResumeQuestionGenerator ----------

def test_generate_parses_questions():
    fake = _fake({"questions": [
        {"question_text": "GIL을 설명해주세요.", "question_type": "개념설명형"},
        {"question_text": "FastAPI 의존성 주입을 어떻게 썼나요?", "question_type": "기술형"},
    ]})
    result = ResumeQuestionGenerator(llm=fake).generate(STRUCTURED, existing=["1분 자기소개 부탁드립니다."])

    assert len(result) == 2
    assert result[0]["question_type"] == "개념설명형"
    assert result[1]["question_text"].startswith("FastAPI")


class _RecordingLLM(FakeListChatModel):
    """체인이 실제로 넘긴 프롬프트를 기록하는 페이크 LLM"""

    prompts: list = []

    def _call(self, messages, *args, **kwargs):
        type(self).prompts.append("".join(m.content for m in messages))
        return super()._call(messages, *args, **kwargs)


def test_generate_injects_existing_questions_into_prompt():
    _RecordingLLM.prompts = []
    body = json.dumps({"questions": [{"question_text": "새 질문", "question_type": "기술형"}]},
                      ensure_ascii=False)
    generator = ResumeQuestionGenerator(llm=_RecordingLLM(responses=[body]))

    generator.generate(STRUCTURED, existing=["오버피팅을 설명해주세요", "1분 자기소개 부탁드립니다."])

    assert _RecordingLLM.prompts, "LLM이 호출되지 않았다"
    sent = _RecordingLLM.prompts[0]
    # 기존 질문이 실제로 프롬프트에 실려 나갔는지
    assert "- 오버피팅을 설명해주세요" in sent
    assert "- 1분 자기소개 부탁드립니다." in sent
    assert "의미가 겹치는 질문은 절대 만들지 마세요" in sent
    # 이력서 내용과 개수 상한도 함께 전달된다
    assert "FastAPI" in sent
    assert str(MAX_GENERATED_QUESTIONS) in sent


def test_generate_without_existing_sends_placeholder():
    _RecordingLLM.prompts = []
    body = json.dumps({"questions": [{"question_text": "질문", "question_type": "기술형"}]},
                      ensure_ascii=False)
    ResumeQuestionGenerator(llm=_RecordingLLM(responses=[body])).generate(STRUCTURED)

    assert "(없음)" in _RecordingLLM.prompts[0]


def test_generate_raises_when_llm_returns_no_usable_question():
    fake = _fake({"questions": []})
    with pytest.raises(ResumeQuestionGenerationError):
        ResumeQuestionGenerator(llm=fake).generate(STRUCTURED)


def test_generate_raises_on_malformed_json():
    fake = _fake("JSON이 아닌 그냥 텍스트")
    with pytest.raises(ResumeQuestionGenerationError):
        ResumeQuestionGenerator(llm=fake).generate(STRUCTURED)


# ---------- QuestionTypeClassifier ----------

def test_classify_returns_known_type():
    fake = FakeListChatModel(responses=["상황형"])
    assert QuestionTypeClassifier(llm=fake).classify("출시 직전 오류가 나면?") == "상황형"


def test_classify_strips_quotes_and_whitespace():
    fake = FakeListChatModel(responses=['  "행동형" \n'])
    assert QuestionTypeClassifier(llm=fake).classify("경험을 말해주세요") == "행동형"


def test_classify_unknown_output_falls_back_with_warning(caplog):
    fake = FakeListChatModel(responses=["아무말"])
    with caplog.at_level("WARNING"):
        result = QuestionTypeClassifier(llm=fake).classify("질문")
    assert result == FALLBACK_QUESTION_TYPE
    assert "알 수 없는 질문 유형" in caplog.text


def test_classify_llm_failure_falls_back_with_warning(caplog):
    class BoomLLM(FakeListChatModel):
        def _call(self, *args, **kwargs):
            raise RuntimeError("LLM 장애")

    with caplog.at_level("WARNING"):
        result = QuestionTypeClassifier(llm=BoomLLM(responses=["x"])).classify("질문")
    assert result == FALLBACK_QUESTION_TYPE
    assert "질문 유형 분류 실패" in caplog.text
