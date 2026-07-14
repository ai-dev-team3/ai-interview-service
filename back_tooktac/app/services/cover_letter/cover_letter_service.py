from __future__ import annotations

from sqlalchemy.orm import Session

from app.repository.career import CoverLetter, JobGroup


class CoverLetterValidationError(Exception):
    """Cover letter payload is invalid."""


class CoverLetterNotFoundError(Exception):
    """Cover letter does not exist or is not owned by the user."""


PAIR_DELIMITER = "|"
ESCAPED_DELIMITER = "｜"


def _clean_part(value: str) -> str:
    return (value or "").strip().replace(PAIR_DELIMITER, ESCAPED_DELIMITER)


def _join_parts(values: list[str]) -> str:
    return PAIR_DELIMITER.join(_clean_part(value) for value in values)


def _split_parts(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(PAIR_DELIMITER)]


def normalize_pairs(question_texts: list[str], answer_texts: list[str]) -> tuple[list[str], list[str]]:
    max_len = max(len(question_texts), len(answer_texts))
    questions: list[str] = []
    answers: list[str] = []

    for index in range(max_len):
        question = _clean_part(question_texts[index] if index < len(question_texts) else "")
        answer = _clean_part(answer_texts[index] if index < len(answer_texts) else "")
        if not question and not answer:
            continue
        if not question or not answer:
            raise CoverLetterValidationError("질문과 답변을 모두 입력해주세요.")
        questions.append(question)
        answers.append(answer)

    if not questions:
        raise CoverLetterValidationError("자소서 질문과 답변을 1개 이상 입력해주세요.")

    return questions, answers


def split_cover_letter_pairs(cover_letter: CoverLetter) -> list[dict[str, str]]:
    questions = _split_parts(cover_letter.question_text)
    answers = _split_parts(cover_letter.answer_text)
    pairs = []
    for index in range(max(len(questions), len(answers))):
        pairs.append({
            "question_text": questions[index] if index < len(questions) else "",
            "answer_text": answers[index] if index < len(answers) else "",
        })
    return pairs


def create_cover_letter(
    db: Session,
    user_id: int,
    *,
    question_texts: list[str],
    answer_texts: list[str],
    job_group_id: int,
    title: str | None = None,
    company_name: str | None = None,
) -> CoverLetter:
    job_group = db.get(JobGroup, job_group_id)
    if not job_group:
        raise CoverLetterValidationError("존재하지 않는 직무군입니다.")

    questions, answers = normalize_pairs(question_texts, answer_texts)
    normalized_title = _clean_part(title or "")[:100] or "자기소개서"
    normalized_company = _clean_part(company_name or "")[:100] or None

    cover_letter = CoverLetter(
        user_id=user_id,
        job_group_id=job_group_id,
        company_name=normalized_company,
        title=normalized_title,
        question_text=_join_parts(questions),
        answer_text=_join_parts(answers),
    )
    db.add(cover_letter)
    db.commit()
    db.refresh(cover_letter)
    return cover_letter


def update_cover_letter(
    db: Session,
    user_id: int,
    cover_letter_id: int,
    *,
    question_texts: list[str],
    answer_texts: list[str],
    job_group_id: int,
    title: str | None = None,
    company_name: str | None = None,
) -> CoverLetter:
    cover_letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.id == cover_letter_id, CoverLetter.user_id == user_id)
        .first()
    )
    if not cover_letter:
        raise CoverLetterNotFoundError("자소서를 찾을 수 없습니다.")

    job_group = db.get(JobGroup, job_group_id)
    if not job_group:
        raise CoverLetterValidationError("존재하지 않는 직무군입니다.")

    questions, answers = normalize_pairs(question_texts, answer_texts)
    cover_letter.job_group_id = job_group_id
    cover_letter.company_name = _clean_part(company_name or "")[:100] or None
    cover_letter.title = _clean_part(title or "")[:100] or "자기소개서"
    cover_letter.question_text = _join_parts(questions)
    cover_letter.answer_text = _join_parts(answers)

    db.commit()
    db.refresh(cover_letter)
    return cover_letter


def list_cover_letters(db: Session, user_id: int) -> list[CoverLetter]:
    return (
        db.query(CoverLetter)
        .filter(CoverLetter.user_id == user_id)
        .order_by(CoverLetter.created_at.desc(), CoverLetter.id.desc())
        .all()
    )


def get_latest_cover_letter(db: Session, user_id: int) -> CoverLetter | None:
    return (
        db.query(CoverLetter)
        .filter(CoverLetter.user_id == user_id)
        .order_by(CoverLetter.created_at.desc(), CoverLetter.id.desc())
        .first()
    )


def delete_cover_letter(db: Session, user_id: int, cover_letter_id: int) -> None:
    cover_letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.id == cover_letter_id, CoverLetter.user_id == user_id)
        .first()
    )
    if not cover_letter:
        raise CoverLetterNotFoundError("자소서를 찾을 수 없습니다.")
    db.delete(cover_letter)
    db.commit()


def to_analysis_text(cover_letter: CoverLetter | None) -> str:
    if not cover_letter:
        return ""

    parts = [cover_letter.company_name, cover_letter.title]
    for index, pair in enumerate(split_cover_letter_pairs(cover_letter), start=1):
        if pair["question_text"]:
            parts.append(f"질문 {index}: {pair['question_text']}")
        if pair["answer_text"]:
            parts.append(f"답변 {index}: {pair['answer_text']}")
    return "\n".join(part for part in parts if part)
