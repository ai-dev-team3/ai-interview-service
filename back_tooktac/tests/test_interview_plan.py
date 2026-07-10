"""services/interview/plan.py — 면접 구성 단일 소스 일관성 테스트"""
from app.services.interview.plan import (
    DEFAULT_QUESTION_TYPE,
    FALLBACK_QUESTION_TYPE,
    MAX_GENERATED_QUESTIONS,
    MAX_INTERVIEW_QUESTIONS,
    MIN_GENERATED_QUESTIONS,
    QUESTION_TYPES,
)
from app.services.score.scoring import QuestionTypeWeights


def test_default_and_fallback_types_are_known():
    assert DEFAULT_QUESTION_TYPE in QUESTION_TYPES
    assert FALLBACK_QUESTION_TYPE in QUESTION_TYPES


def test_question_types_all_have_scoring_weights():
    # 유형을 추가하면 채점 가중치도 함께 추가해야 한다
    assert set(QUESTION_TYPES) == set(QuestionTypeWeights.WEIGHTS)


def test_generated_question_range():
    assert 1 <= MIN_GENERATED_QUESTIONS <= MAX_GENERATED_QUESTIONS


def test_interview_can_hold_default_plus_generated():
    # 기본 자기소개 질문 1개 + 최소 1개는 담을 수 있어야 한다
    assert MAX_INTERVIEW_QUESTIONS >= 1 + MIN_GENERATED_QUESTIONS
