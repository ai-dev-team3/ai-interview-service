"""답변 평가 워크플로우 (LangGraph).

그래프 구조:

    START ─┬─ generate_model_answer ─┬─ finalize ─ END
           └─ evaluate_answer ───────┘

모범답변 생성과 LLM 평가는 서로 독립이므로 병렬 노드로 실행하고,
finalize에서 유사도 계산과 최종 점수 산출을 수행한다.
"""
from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.text.answer_generator import ModelAnswerGenerator
from app.services.text.calculator import FinalScoreCalculator
from app.services.text.evaluator import AnswerEvaluator
from app.services.text.scorer import SimilarityScorer


def preprocess_input(question_text: str, user_answer_text: str, question_type: str) -> dict:
    TYPE_MAPPING = {
        "개념설명형": "technical",
        "기술형": "technical",
        "상황형": "situational",
        "행동형": "situational"
    }

    return {
        "question": question_text.strip(),
        "user_answer": user_answer_text.strip(),
        "question_type": question_type,
        "evaluation_type": TYPE_MAPPING.get(question_type, "technical")
    }


class EvaluationState(TypedDict, total=False):
    # 입력
    question: str
    user_answer: str
    question_type: str
    evaluation_type: str
    # 병렬 노드 산출물
    model_answer: str
    evaluation: dict
    # finalize 산출물
    similarity: float
    final_score: float


class EvaluationOrchestrator:
    def __init__(
        self,
        model_answer_generator: Optional[ModelAnswerGenerator] = None,
        answer_evaluator: Optional[AnswerEvaluator] = None,
        similarity_scorer: Optional[SimilarityScorer] = None,
        score_calculator: Optional[FinalScoreCalculator] = None,
    ):
        self.model_answer_generator = model_answer_generator or ModelAnswerGenerator()
        self.similarity_scorer = similarity_scorer or SimilarityScorer()
        self.answer_evaluator = answer_evaluator or AnswerEvaluator()
        self.score_calculator = score_calculator or FinalScoreCalculator()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(EvaluationState)
        builder.add_node("generate_model_answer", self._generate_model_answer)
        builder.add_node("evaluate_answer", self._evaluate_answer)
        builder.add_node("finalize", self._finalize)

        # 모범답변 생성과 LLM 평가는 독립 → 병렬 실행
        builder.add_edge(START, "generate_model_answer")
        builder.add_edge(START, "evaluate_answer")
        builder.add_edge(["generate_model_answer", "evaluate_answer"], "finalize")
        builder.add_edge("finalize", END)
        return builder.compile()

    def _generate_model_answer(self, state: EvaluationState) -> dict:
        model_answer = self.model_answer_generator.generate(
            state["question"],
            state["user_answer"],
            state["evaluation_type"],
        )
        return {"model_answer": model_answer}

    def _evaluate_answer(self, state: EvaluationState) -> dict:
        evaluation = self.answer_evaluator.evaluate(
            state["question"],
            state["user_answer"],
            state["evaluation_type"],
        )
        return {"evaluation": evaluation}

    def _finalize(self, state: EvaluationState) -> dict:
        similarity = self.similarity_scorer.calculate_similarity(
            state["user_answer"],
            state["model_answer"],
        )
        scores = {
            "similarity_score": similarity,
            "intent_score": state["evaluation"]["intent_score"],
            "knowledge_score": state["evaluation"]["knowledge_score"],
        }
        final_score = self.score_calculator.calculate_final_score(
            scores, state["evaluation_type"]
        )
        return {"similarity": similarity, "final_score": final_score}

    def evaluate_answer(self, question: str, user_answer: str, question_type: str) -> dict:
        processed_input = preprocess_input(question, user_answer, question_type)
        state = self.graph.invoke(processed_input)

        evaluation_result = state["evaluation"]
        return {
            "question": processed_input["question"],
            "user_answer": processed_input["user_answer"],
            "question_type": processed_input["question_type"],
            "evaluation_type": processed_input["evaluation_type"],
            "model_answer": state["model_answer"],
            "similarity": state["similarity"],
            "intent_score": evaluation_result["intent_score"],
            "knowledge_score": evaluation_result["knowledge_score"],
            "final_score": state["final_score"],
            "feedback": {
                "strengths": evaluation_result["strengths"],
                "improvements": evaluation_result["improvements"],
                "final_feedback": evaluation_result["final_feedback"]
            }
        }
