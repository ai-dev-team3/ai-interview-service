"""services/interview/plan.py — 면접 구성 단일 소스 일관성 테스트"""
from app.services.interview.plan import (
    FOLLOWUP_ORDERS,
    QUESTION_FLOW,
    STEP_NAMES,
    TOTAL_QUESTIONS,
)
from app.services.text.make_question import InterviewQuestionGenerator


def test_flow_covers_all_orders():
    assert sorted(QUESTION_FLOW.keys()) == list(range(1, TOTAL_QUESTIONS + 1))


def test_followup_orders_have_refs():
    for order in FOLLOWUP_ORDERS:
        refs = QUESTION_FLOW[order]["refs"]
        assert refs, f"{order}번은 꼬리물기인데 refs가 없음"
        # 참조는 항상 자신보다 앞선 질문이어야 함
        assert all(r < order for r in refs)


def test_non_followup_orders_have_no_refs():
    for order, flow in QUESTION_FLOW.items():
        if order not in FOLLOWUP_ORDERS:
            assert flow["refs"] is None


def test_step_names_length():
    # 아이스브레이킹 + 질문 N개 + 최종 평가
    assert len(STEP_NAMES) == TOTAL_QUESTIONS + 2
    assert STEP_NAMES[0] == "아이스브레이킹"
    assert STEP_NAMES[-1] == "최종 평가"


def test_flow_methods_exist_on_generator():
    for flow in QUESTION_FLOW.values():
        assert hasattr(InterviewQuestionGenerator, flow["method"])
