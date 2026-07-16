"""현재 처리 중인 '기능'을 LLM 추적에 실어 보내기 위한 요청 스코프 컨텍스트.

대시보드는 LLM 호출을 기능(이력서 구조화·자소서 첨삭·취업진단평가·연습면접·
실전면접·최종 리포트)별로 집계한다. 그런데 LLM을 부르는 모듈 상당수는 기능 간
공유된다 — 예를 들어 답변 평가(text/orchestrator)는 연습면접과 실전면접이 같이
쓰고, 이력서 구조화는 이력서 등록·연습면접 시작·실전면접 시작에서 모두 불린다.
그래서 '어느 모듈이냐'로는 기능을 알 수 없고, 요청이 시작될 때 정해서 들고
다녀야 한다.

서비스 함수마다 feature 인자를 뚫는 대신 contextvar를 쓴다. 라우터에서 한 번
with feature(...) 로 감싸면 그 안에서 일어나는 모든 LLM 호출을 tracer가 알아서
그 기능으로 기록한다. contextvar는 async/await은 물론 FastAPI가 동기 엔드포인트를
돌리는 스레드풀에도 복사되므로 두 방식 모두에서 동작한다.

with 는 중첩할 수 있고 안쪽이 이긴다. 이력서 구조화처럼 '누가 부르든 항상 같은
기능'인 호출은 모듈 안에서 스스로를 감싸 바깥 컨텍스트를 덮어쓴다.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

# 대시보드가 이 값으로 집계한다. 라벨은 대시보드 쪽에 있다.
RESUME_STRUCTURING = "resume-structuring"
COVER_LETTER_FEEDBACK = "cover-letter-feedback"
CAREER_DIAGNOSIS = "career-diagnosis"
PRACTICE_INTERVIEW = "practice-interview"
REAL_INTERVIEW = "real-interview"
FINAL_REPORT = "final-report"

_current: ContextVar[Optional[str]] = ContextVar("llm_feature", default=None)


@contextmanager
def feature(name: str) -> Iterator[None]:
    """이 블록 안의 LLM 호출을 name 기능으로 기록한다."""
    token = _current.set(name)
    try:
        yield
    finally:
        _current.reset(token)


def current_feature() -> Optional[str]:
    """지금 기록해야 할 기능. 표시된 적이 없으면 None."""
    return _current.get()
