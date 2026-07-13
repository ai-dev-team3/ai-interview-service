import logging
# app/services/report/interview_data_formatter.py
from collections import defaultdict
from sqlalchemy.orm import Session
from app.repository.interview import InterviewSession, InterviewQuestion, InterviewAnswer
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.services.score.scale import clamp_score, from_ten_point, from_unit
from app.services.score.scoring import QuestionTypeWeights
from sqlalchemy.inspection import inspect
import json


logger = logging.getLogger(__name__)

def _score(result, attr: str) -> float:
    """결과 행이 없을 수 있다 — 실전 면접은 분석이 백그라운드에서 돌기 때문이다.

    서버가 재시작하거나 분석이 유실되면 그 문항의 행이 영영 생기지 않는다.
    그래도 나머지 문항으로 리포트는 나와야 한다. 여기서 죽으면 면접 전체가 날아간다.
    """
    if result is None:
        return 0
    return getattr(result, attr, 0) or 0


def calculate_final_score(text_result: EvaluationResult, video_result: VideoEvaluationResult, question_type: str) -> int:
    """
    질문 유형에 따라 text/voice/video 점수를 가중 평균으로 계산 (0~100)
    """
    return QuestionTypeWeights.calculate_weighted_score({
        "type": question_type,
        "detailAnalysis": {
            "text": {"score": clamp_score(_score(text_result, "final_text_score"))},
            "voice": {"score": clamp_score(_score(text_result, "final_speech_score"))},
            "video": {"score": clamp_score(_score(video_result, "final_video_score"))},
        }
    })


# 2) SQLAlchemy 객체 → 컬럼 dict로 안전 변환
def sa_to_dict(obj):
    if obj is None:
        return None
    mapper = inspect(obj).mapper
    return {c.key: getattr(obj, c.key) for c in mapper.column_attrs}

# 3) 긴 문자열 자르기(로그 가독성)
def truncate_values(d: dict, maxlen: int = 120) -> dict:
    if d is None:
        return None
    out = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > maxlen:
            out[k] = v[:maxlen] + f"...(+{len(v) - maxlen} more)"
        else:
            out[k] = v
    return out


def _pick_representative_for_order(
    db: Session, candidates: list[InterviewQuestion]
) -> InterviewQuestion:
    """
    동일 question_order에 속한 여러 질문(candidates) 중 대표 1개를 고른다.
    우선순위:
      1) EvaluationResult와 VideoEvaluationResult가 모두 존재하는 질문
         (둘 다 있으면 최신 id 우선)
      2) 그 외에는 id가 가장 큰 것(가장 최근 생성) 우선
    """
    scored = []
    for q in candidates:
        # 각 후보의 결과 존재 여부 확인
        text_res = db.query(EvaluationResult).filter_by(question_id=q.id).first()
        video_res = db.query(VideoEvaluationResult).filter_by(question_id=q.id).first()
        both = 1 if (text_res is not None and video_res is not None) else 0
        scored.append((both, q.id, q))  # both(0/1), 최신성 proxy(id), 객체

    # 우선 both가 1인 것들 중에서 id가 큰 것, 없으면 그냥 id가 큰 것
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]

def generate_interview_json_from_session(db: Session, session_id: int) -> dict:
    """
    주어진 세션 ID의 질문별 평가 결과를 FinalEvaluationGenerator에서 사용할 JSON 형식으로 반환
    """
    session = db.query(InterviewSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError("해당 session_id에 해당하는 면접 세션이 없습니다")

    user = session.user
    #questions = session.questions

    # print("=" * 20)
    # print("questions : ", questions)
    # print("=" * 20)

    qs = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.question_order.asc(), InterviewQuestion.id.asc())
        .all()
    )
    by_order: dict[int, list[InterviewQuestion]] = defaultdict(list)
    for q in qs:
        by_order[q.question_order].append(q)

    # 2) 각 order별 대표 질문 1개만 선정
    unique_questions: list[InterviewQuestion] = []
    for order in sorted(by_order.keys()):
        reps = _pick_representative_for_order(db, by_order[order])
        unique_questions.append(reps)

    question_analyses = []

    for q in sorted(unique_questions, key=lambda x: x.question_order):
        question_id = q.id
        order = q.question_order

        logger.debug("questionId=%s questionOrder=%s", question_id, order)

        answer = db.query(InterviewAnswer).filter_by(question_id=question_id).first()
        text_result = db.query(EvaluationResult).filter_by(question_id=question_id).first()
        video_result = db.query(VideoEvaluationResult).filter_by(question_id=question_id).first()

        logger.debug("Answer dict: %s", json.dumps(truncate_values(sa_to_dict(answer)), ensure_ascii=False, default=str))
        logger.debug("TextResult dict: %s", json.dumps(truncate_values(sa_to_dict(text_result)), ensure_ascii=False, default=str))
        logger.debug("VideoResult dict: %s", json.dumps(truncate_values(sa_to_dict(video_result)), ensure_ascii=False, default=str))

        # 분석 데이터가 없어도 죽지 않는다. 실전 면접은 분석이 백그라운드에서 돌기 때문에
        # 서버가 재시작하거나 분석이 유실되면 그 문항만 비어 있을 수 있다. 그 한 문항 때문에
        # 면접 전체의 리포트를 못 보게 되는 게 훨씬 나쁘다. 대신 실패했다고 표시한다.
        analysis_failed = text_result is None
        if analysis_failed:
            logger.warning("%s번 질문의 분석 결과가 없다 — 0점으로 리포트에 담는다", order)

        question_data = {
            "question_id": str(question_id),
            "question_number": order,
            "question_type": q.question_type,
            "analysis_failed": analysis_failed,
            "final_score": calculate_final_score(text_result, video_result, q.question_type),
            "question_text": q.question_text,
            "user_answer": answer.answer_text if answer else "",
            "model_answer": text_result.model_answer if text_result else "",
            # 화면에 뜨는 값은 전부 0~100 이다. 내부 스케일(유사도 0~1, LLM 척도 1~10,
            # 음성 배분 0~40/0~20)을 여기서 한 번에 맞춘다. 각자 알아서 변환하면
            # similarity * 10 처럼 조용히 틀린 값이 화면에 뜬다 — 실제로 그랬다.
            "detail_analysis": {
                "text": {
                    "score": clamp_score(_score(text_result, "final_text_score")),
                    "similarity": from_unit(_score(text_result, "similarity")),
                    "accuracy": from_ten_point(_score(text_result, "knowledge_score")),
                    "understanding": from_ten_point(_score(text_result, "intent_score"))
                },
                "voice": {
                    "score": clamp_score(_score(text_result, "final_speech_score")),
                    "speed": {"score": clamp_score(_score(text_result, "speed_score") * 2.5)},
                    "fluency": {"score": clamp_score(_score(text_result, "filler_score") * 2.5)},
                    "tone": {"score": clamp_score(_score(text_result, "pitch_score") * 5.0)},
                    "speed_label": text_result.speed_label if text_result else "없음",
                    "fluency_label": text_result.fluency_label if text_result else "없음",
                    "tone_label": text_result.tone_label if text_result else "없음"
                },
                "video": {
                    "score": clamp_score(_score(video_result, "final_video_score")),
                    "gaze_rate": {"percentage": clamp_score(_score(video_result, "gaze_score"))},
                    # 경고가 많으면 음수가 됐다. 실제로 -310 이 나왔다.
                    "shoulder_posture": {
                        "score": clamp_score(100 - _score(video_result, "shoulder_warning") * 10)
                    },
                    "hand_posture": {
                        "score": clamp_score(100 - _score(video_result, "hand_warning") * 10)
                    }
                }
            },
            "feedback": (
                text_result.final_feedback if text_result
                else "이 문항의 분석이 완료되지 않았습니다."
            ),
            "strengths": (
                text_result.strengths.split("\n") if text_result and text_result.strengths else []
            ),
            "improvements": (
                text_result.improvements.split("\n")
                if text_result and text_result.improvements else []
            )
        }

        question_analyses.append(question_data)

    return {
        "user_info": {
            "user_id": str(user.id),
            "user_nickname": user.nickname,
            "interview_id": f"session_{session_id}",
            "interview_date": session.started_at.date().isoformat(),
            "interview_duration": 25  # 기본값 (옵션)
        },
        "question_analyses": question_analyses
    }
