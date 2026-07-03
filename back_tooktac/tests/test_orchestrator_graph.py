"""EvaluationOrchestrator LangGraph 워크플로우 테스트.

scorer 모듈이 torch를 로드하므로 이 파일은 임포트가 다소 느릴 수 있다.
LLM/임베딩 컴포넌트는 모두 페이크를 주입해 그래프 배선만 검증한다.
"""
from app.services.text.orchestrator import EvaluationOrchestrator, preprocess_input


class FakeModelAnswerGenerator:
    def generate(self, question, user_answer, evaluation_type):
        return "모범답변입니다."


class FakeAnswerEvaluator:
    def evaluate(self, question, user_answer, evaluation_type):
        return {
            "intent_score": 8.0,
            "knowledge_score": 7.0,
            "strengths": ["논리적"],
            "improvements": ["구체성 부족"],
            "final_feedback": "전반적으로 양호합니다.",
        }


class FakeSimilarityScorer:
    def calculate_similarity(self, user_answer, model_answer):
        return 0.5


def test_preprocess_input_maps_question_type():
    result = preprocess_input(" 질문 ", " 답변 ", "행동형")
    assert result == {
        "question": "질문",
        "user_answer": "답변",
        "question_type": "행동형",
        "evaluation_type": "situational",
    }


def test_orchestrator_graph_end_to_end():
    orchestrator = EvaluationOrchestrator(
        model_answer_generator=FakeModelAnswerGenerator(),
        answer_evaluator=FakeAnswerEvaluator(),
        similarity_scorer=FakeSimilarityScorer(),
    )

    result = orchestrator.evaluate_answer("질문", "답변", "기술형")

    assert result["model_answer"] == "모범답변입니다."
    assert result["similarity"] == 0.5
    assert result["intent_score"] == 8.0
    assert result["knowledge_score"] == 7.0
    # technical 가중치: 0.5*0.2 + (7/9)*0.3 + (6/9)*0.5 = 0.6667 → 67점
    assert result["final_score"] == 67
    assert result["feedback"]["strengths"] == ["논리적"]
    assert result["feedback"]["final_feedback"] == "전반적으로 양호합니다."
