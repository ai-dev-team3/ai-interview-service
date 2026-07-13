"""면접 구성(질문 유형·개수 제한·단계 이름)의 단일 소스.

연습 면접(practice):
  이력서 등록 시 생성된 질문 풀에서 사용자가 골라 순서대로 답변한다.
  꼬리질문 없음. 문항마다 결과를 본다.

실전 면접(real):
  서버가 풀에서 질문을 자동으로 고른다(사용자는 미리 못 본다).
  답변마다 꼬리질문이 붙을 수 있고, 그만큼 남은 기본 질문이 밀려난다.
  총 문항 수는 어느 쪽이든 MAX_INTERVIEW_QUESTIONS 를 넘지 않는다.
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

# 한 번의 면접에서 답변할 수 있는 질문 수 (기본 질문·꼬리질문 포함)
MAX_INTERVIEW_QUESTIONS = 7

# 면접 모드
MODE_PRACTICE = "practice"
MODE_REAL = "real"

# --- 실전 면접 ---
#
# 문항 수가 아니라 시간이 기준이다. 짧게 답하면 문항이 늘고, 길게 답하면 준다.
# 어느 쪽이든 12분 안팎에서 끝난다.
REAL_PREPARE_SECONDS = 10
REAL_ANSWER_SECONDS = 90

# 답변이 끝난 시점의 경과가 이 시간을 넘으면 마무리 질문으로 간다.
REAL_TIME_BUDGET_SECONDS = 10 * 60

# 안전장치. 답변이 계속 무음으로 끝나면 시간이 안 흐르는 것처럼 보일 수 있다.
REAL_MAX_QUESTIONS = 15

# 마지막 질문. 채점하지 않으므로 질문 행으로 만들지 않는다 —
# 전사만 interview_session.closing_remark 에 남긴다.
CLOSING_QUESTION_TEXT = "마지막으로 하고 싶은 말씀 있으신가요?"
