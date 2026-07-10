"""LangChain 전환(LCEL 체인/LangGraph) 단위 테스트.

실제 API를 호출하지 않도록 FakeListChatModel 또는 페이크 컴포넌트를 주입한다.
"""
import pytest
from langchain_core.language_models import FakeListChatModel

from app.services.resume.structurer import ResumeStructurer, ResumeStructuringError
from app.services.text.answer_generator import ModelAnswerGenerator
from app.services.text.evaluator import AnswerEvaluator

STRUCTURED = {
    "skills": ["Python", "FastAPI"],
    "education": {"major": "컴퓨터공학"},
    "career": {"status": "신입", "years": "0년"},
    "projects": [{"name": "면접 서비스"}],
    "self_introduction": {"motivation": "동기", "strengths": "강점",
                          "key_experiences": "경험", "career_goals": "목표"},
    "desired_position": {"job_type": "백엔드"},
}


# ---------- ResumeStructurer ----------

def test_structurer_parses_json_and_fills_defaults():
    # 마크다운 코드블록으로 감싸도 JsonOutputParser가 파싱해야 한다
    fake = FakeListChatModel(
        responses=['```json\n{"skills": ["Python"], "career": {"status": "신입"}}\n```']
    )
    structurer = ResumeStructurer(llm=fake)

    result = structurer.structure("이력서 원문")

    assert result["skills"] == ["Python"]
    assert result["career"] == {"status": "신입"}
    # 누락 키는 기본값으로 채워짐
    assert result["education"] == {}
    assert result["projects"] == []


def test_structurer_invalid_json_raises():
    fake = FakeListChatModel(responses=["JSON이 아닌 그냥 텍스트"])
    structurer = ResumeStructurer(llm=fake)

    with pytest.raises(ResumeStructuringError):
        structurer.structure("이력서 원문")


# ---------- ModelAnswerGenerator ----------

def test_model_answer_generator_technical():
    fake = FakeListChatModel(responses=["정의입니다. 특징입니다. 실무 예시입니다."])
    generator = ModelAnswerGenerator(llm=fake)

    answer = generator.generate("프로세스와 스레드 차이는?", "", "technical")

    assert answer == "정의입니다. 특징입니다. 실무 예시입니다."


def test_model_answer_generator_situational():
    fake = FakeListChatModel(responses=["상황입니다. 행동입니다. 결과입니다."])
    generator = ModelAnswerGenerator(llm=fake)

    answer = generator.generate("갈등 상황 대처는?", "대화로 해결했습니다.", "situational")

    assert answer == "상황입니다. 행동입니다. 결과입니다."


# ---------- AnswerEvaluator ----------

def test_evaluator_parses_and_clamps_scores():
    fake = FakeListChatModel(responses=[
        '{"intent_score": 15, "knowledge_score": 0,'
        ' "strengths": ["명확한 설명"], "improvements": ["깊이 부족"],'
        ' "final_feedback": "총평"}'
    ])
    evaluator = AnswerEvaluator(llm=fake)

    result = evaluator.evaluate("질문", "답변", "technical")

    # 점수는 1~10으로 클램프
    assert result["intent_score"] == 10.0
    assert result["knowledge_score"] == 1.0
    assert result["strengths"] == ["명확한 설명"]
    assert result["final_feedback"] == "총평"
