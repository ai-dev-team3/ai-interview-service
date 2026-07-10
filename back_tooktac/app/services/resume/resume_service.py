"""이력서 저장/조회/구조화 서비스.

마이페이지 업로드, 면접 질문 생성 등 어느 진입점에서든
재사용할 수 있도록 라우터와 분리된 독립 모듈로 유지한다.
"""
import json
import logging

from sqlalchemy.orm import Session

from app.repository.resume import Resume, ResumeQuestion
from app.services.interview.plan import DEFAULT_QUESTION_TEXT, DEFAULT_QUESTION_TYPE
from app.services.interview.question_generator import (
    ResumeQuestionGenerationError,
    ResumeQuestionGenerator,
)
from app.services.resume.structurer import ResumeStructurer, ResumeStructuringError

logger = logging.getLogger(__name__)


class ResumeNotFoundError(Exception):
    """등록된 이력서(원문)가 없음"""


def get_resume(db: Session, user_id: int) -> Resume | None:
    return db.query(Resume).filter(Resume.user_id == user_id).first()


def has_resume(db: Session, user_id: int) -> bool:
    """이력서 원문(content)이 등록되어 있는지 여부"""
    resume = get_resume(db, user_id)
    return bool(resume and resume.content)


def upsert_resume(db: Session, user_id: int, content: str, filename: str | None = None) -> Resume:
    """이력서 원문 텍스트를 저장한다. 이미 있으면 갱신(업서트).

    원문이 바뀌면 기존 구조화 데이터(structured)와 질문 풀은 더 이상 유효하지 않으므로
    모두 버리고, 기본 자기소개 질문 1행만 다시 심는다.
    """
    resume = get_resume(db, user_id)
    if resume:
        resume.content = content
        resume.filename = filename
        resume.structured = None
        resume.questions_generated = False
        resume.questions.clear()  # delete-orphan 캐스케이드로 실제 삭제
    else:
        resume = Resume(user_id=user_id, filename=filename, content=content, structured=None)
        db.add(resume)
    db.flush()
    _seed_default_question(resume)
    db.commit()
    db.refresh(resume)
    return resume


def _seed_default_question(resume: Resume) -> None:
    """기본 자기소개 질문을 풀 맨 앞에 넣는다. LLM 생성 개수에 포함하지 않는다."""
    resume.questions.append(ResumeQuestion(
        question_text=DEFAULT_QUESTION_TEXT,
        question_type=DEFAULT_QUESTION_TYPE,
        is_default=True,
        sort_order=0,
    ))


def try_structure(db: Session, resume: Resume) -> bool:
    """이력서 원문을 구조화해 저장한다. 실패해도 예외를 전파하지 않는다.

    업로드 시점의 베스트에포트 처리용 — 실패 시 면접 시작 시점에
    ensure_structured()가 재시도한다.
    """
    try:
        resume.structured = ResumeStructurer().structure(resume.content)
    except ResumeStructuringError:
        logger.warning("이력서 구조화 실패 — 면접 시작 시 재시도 (resume_id=%s)", resume.id)
        return False
    db.commit()
    return True


def ensure_structured(db: Session, user_id: int) -> dict:
    """구조화된 이력서를 반환한다. 없으면 원문으로부터 생성·저장 후 반환.

    Raises:
        ResumeNotFoundError: 이력서 원문 자체가 없음
        ResumeStructuringError: 구조화(Gemini) 실패
    """
    resume = get_resume(db, user_id)
    if not resume or not resume.content:
        raise ResumeNotFoundError("등록된 이력서가 없습니다.")

    if not resume.structured:
        resume.structured = ResumeStructurer().structure(resume.content)
        db.commit()
        db.refresh(resume)

    structured = resume.structured
    if isinstance(structured, str):
        structured = json.loads(structured)
    return structured


def _generate_questions(db: Session, resume: Resume, structured: dict) -> None:
    """LLM으로 질문을 생성해 풀에 덧붙인다. 실패 시 예외를 전파한다."""
    existing = [q.question_text for q in resume.questions]
    generated = ResumeQuestionGenerator().generate(structured, existing=existing)

    next_order = max((q.sort_order for q in resume.questions), default=0) + 1
    for offset, item in enumerate(generated):
        resume.questions.append(ResumeQuestion(
            question_text=item["question_text"],
            question_type=item["question_type"],
            is_default=False,
            sort_order=next_order + offset,
        ))
    resume.questions_generated = True
    db.commit()
    logger.info("면접 질문 %d개 생성 (resume_id=%s)", len(generated), resume.id)


def try_generate_questions(db: Session, resume: Resume) -> bool:
    """업로드 시점의 베스트에포트 질문 생성. 실패해도 예외를 전파하지 않는다.

    실패하면 ensure_questions()가 나중에 재시도한다.
    """
    structured = resume.structured
    if not structured:
        return False
    if isinstance(structured, str):
        structured = json.loads(structured)

    try:
        _generate_questions(db, resume, structured)
    except ResumeQuestionGenerationError:
        db.rollback()
        logger.warning("면접 질문 생성 실패 — 나중에 재시도 (resume_id=%s)", resume.id)
        return False
    return True


def ensure_questions(db: Session, user_id: int) -> list[ResumeQuestion]:
    """이력서의 질문 풀을 반환한다. 아직 생성 전이면 지금 생성한다.

    LLM 생성에 실패해도 예외를 던지지 않는다. 최소한 기본 자기소개 질문은
    항상 들어 있으므로 그것만으로도 면접을 진행할 수 있다.

    Raises:
        ResumeNotFoundError: 이력서 원문 자체가 없음
    """
    resume = get_resume(db, user_id)
    if not resume or not resume.content:
        raise ResumeNotFoundError("등록된 이력서가 없습니다.")

    # 마이그레이션 백필 이전에 만들어진 이력서 등, 기본 질문이 없는 경우 방어
    if not resume.questions:
        _seed_default_question(resume)
        db.commit()

    if not resume.questions_generated:
        try:
            structured = ensure_structured(db, user_id)
            _generate_questions(db, resume, structured)
        except (ResumeStructuringError, ResumeQuestionGenerationError):
            db.rollback()
            logger.warning(
                "질문 생성 실패 — 기본 질문만으로 진행 (resume_id=%s)", resume.id, exc_info=True
            )

    db.refresh(resume)
    return list(resume.questions)
