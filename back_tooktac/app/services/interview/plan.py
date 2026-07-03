"""면접 구성(질문 수·유형·꼬리물기 위치)의 단일 소스.

기존에는 질문 6개 구성이 interview.py의 if-elif 분기, 리포트의 step_names,
꼬리질문 판정 [3, 6] 등 여러 곳에 하드코딩되어 있었다.
질문 수나 흐름을 바꿀 때는 이 파일만 수정하면 된다.
"""

TOTAL_QUESTIONS = 6

# 꼬리물기(팔로업) 질문 위치
FOLLOWUP_ORDERS = (3, 6)

# 최종 리포트의 단계 이름 (아이스브레이킹 + 질문 N개 + 최종 평가)
STEP_NAMES = [
    "아이스브레이킹",
    *[f"질문 {i}" for i in range(1, TOTAL_QUESTIONS + 1)],
    "최종 평가",
]

# order → (InterviewQuestionGenerator 메서드 이름, 참조할 이전 질문 order들)
# refs가 있으면 해당 질문·답변을 함께 프롬프트에 넣는 꼬리물기 질문이다.
QUESTION_FLOW = {
    1: {"method": "generate_conceptual_question", "refs": None},
    2: {"method": "generate_technical_question", "refs": None},
    3: {"method": "generate_followup_resume_question", "refs": (1, 2)},
    4: {"method": "generate_situational_question", "refs": None},
    5: {"method": "generate_behavioral_question", "refs": None},
    6: {"method": "generate_followup_coverletter_question", "refs": (4, 5)},
}
