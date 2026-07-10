"""면접 구성(질문 유형·개수 제한·단계 이름)의 단일 소스.

질문은 이력서 등록 시 한 번에 생성되어 이력서 질문 풀에 저장되고,
사용자가 그중 일부를 골라 순서대로 답변한다. 꼬리물기 질문은 없다.
"""

# 채점 가중치(score/scoring.py)와 LLM 평가 프롬프트(text/calculator.py)가
# 이 목록의 값에 직접 의존한다. 값을 바꾸면 두 곳을 함께 고쳐야 한다.
QUESTION_TYPES = ("개념설명형", "기술형", "상황형", "행동형")

# 유형 판별에 실패했을 때의 폴백
FALLBACK_QUESTION_TYPE = "개념설명형"

# 이력서 등록 시 항상 미리 저장되는 기본 질문. LLM 생성 개수에 포함하지 않는다.
DEFAULT_QUESTION_TEXT = "1분 자기소개 부탁드립니다."
DEFAULT_QUESTION_TYPE = "행동형"

# LLM이 이력서를 보고 스스로 정하는 질문 개수의 범위
MIN_GENERATED_QUESTIONS = 1
MAX_GENERATED_QUESTIONS = 10

# 한 번의 연습 면접에서 답변할 수 있는 질문 수 (기본 질문 포함)
MAX_INTERVIEW_QUESTIONS = 7
