from __future__ import annotations

import app.repository.model_registry
import random
from datetime import datetime
from statistics import mean
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

# 프로젝트의 실제 ORM 경로(업로드해주신 코드 기준)
from app.repository.database import SessionLocal
from app.repository.user import User
from app.repository.interview import InterviewSession, InterviewQuestion, InterviewAnswer
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.repository.report import (
    FinalReportSummary,
    ReportStrength,
    ReportImprovement,
    ReportAreaScore,
    ReportQuestionScore,
)

# ---------------------------
# 질문 템플릿(6문항, 한글 타입 유지)
# ---------------------------
QUESTION_TEMPLATES: List[Tuple[str, str]] = [
    ("머신러닝 모델 학습 시 발생하는 오버피팅(Overfitting)과 언더피팅(Underfitting)의 개념, 발생 원인, 그리고 이를 해결하기 위한 주요 기법들에 대해 설명해주세요.", "개념설명형"),
    ("프로젝트에서 크롤링으로 수집한 대량의 데이터를 PostgreSQL에 저장하고 분석하는 파이프라인을 구축하셨을 텐데, 데이터의 정합성과 안정성을 확보하기 위해 어떤 방식을 채택하고 구현하셨는지 구체적으로 설명해주세요.", "기술형"),
    ("기술 스택에 기재된 머신러닝, 크롤링, PostgreSQL 관련 질문에 연이어 답변이 어려웠는데, 그렇다면 지원자님께서 가장 자신 있게 설명하고 실제 프로젝트에서 다룬 경험이 있는 기술은 무엇인가요?", "개념설명형"),
    ("새로운 데이터 기반 서비스 출시 직전, 핵심 데이터에서 예상치 못한 오류가 발견되어 서비스 출시가 지연될 위기에 처했고 여러 이해관계자들이 조속한 해결을 요구합니다. 만약 이런 상황이라면 어떻게 문제를 해결하고 상황을 조율하시겠습니까?", "상황형"),
    ("IT 교육 과정 중 협업 프로젝트에서 예상치 못한 기술적 문제나 의견 차이에 부딪혔을 때, 논리적 사고와 유연한 소통으로 이를 해결하여 긍정적인 결과를 얻었던 경험을 구체적으로 말씀해주세요.", "행동형"),
    ("이전 답변들에서 예상치 못한 문제나 협업 상황에서의 구체적인 해결 경험이 부족하다고 하셨는데, 향후 데이터 기반 서비스 개발 과정에서 발생할 수 있는 문제나 동료들과의 협업 이슈를 어떻게 극복하고 성장해 나갈 계획이신가요?", "상황형"),
]

# ---------------------------
# 답변/모범답안/요약 더미 풀
# ---------------------------
ANSWER_POOL_WEAK = [
    "잘 모르겠습니다.",
    "테스트 영상 안 주는 거는 테스트 영상 잘 모르겠습니다.",
    "따로 없는 것 같습니다.",
    "할 것 같습니다.",
    "경험이 부족해 구체적으로는 답변드리기 어렵습니다.",
]

MODEL_ANSWER_POOL = [
    "오버피팅은 학습 데이터에 과적합된 상태, 언더피팅은 모델 복잡도가 부족한 상태로 볼 수 있습니다.",
    "데이터 정합성은 제약조건, 트랜잭션, 검증 파이프라인으로 확보합니다.",
    "Docker와 CI/CD로 환경 일치 및 배포 자동화를 구현합니다.",
    "이슈는 원인분석-가설검증-커뮤니케이션-리스크완화 순으로 대응합니다.",
    "협업 이슈는 합의 형성, 역할 재정의, 회고로 해결합니다.",
    "자료 미제공 시 대체 데이터, 샘플링, 사전협의 프로세스로 대응합니다.",
]

QUESTION_SUMMARY_POOL = [
    "솔직한 태도가 인상적이었습니다.",
    "질문에 솔직하게 답했습니다.",
    "향후 개선 의지가 보였습니다.",
    "간결하게 답변을 마쳤습니다.",
    "모르는 점을 명확히 밝혔습니다.",
]

# ---------------------------
# 5개 실력 프로필 정의
# 각 프로필은 영역별(텍스트/음성/비디오/감정) 점수 분포를 다르게 만듭니다.
# 범위는 대략적인 기대치를 의미하며, 난수로 실제 값을 생성합니다.
# ---------------------------
PROFILE_SPECS = {
    "초급": {
        "text":   ( 5, 25),  # 최종 텍스트 점수 범위
        "speech": (25, 45),  # 최종 음성 점수 범위
        "video":  (10, 35),  # 최종 비디오 점수 범위
        "emotion":(40, 60),  # 감정 점수 범위
        "posture":(70, 90),  # 비디오 내부지표: 자세
        "gaze":   ( 5, 25),  # 비디오 내부지표: 시선
        "labels": {"speed":"느림","fluency_min":40,"tone_min":20}
    },
    "중하": {
        "text":   (25, 45),
        "speech": (40, 55),
        "video":  (30, 55),
        "emotion":(50, 70),
        "posture":(75, 92),
        "gaze":   (15, 35),
        "labels": {"speed":"느림","fluency_min":50,"tone_min":30}
    },
    "중": {
        "text":   (45, 65),
        "speech": (55, 70),
        "video":  (55, 75),
        "emotion":(60, 80),
        "posture":(80, 95),
        "gaze":   (25, 50),
        "labels": {"speed":"보통","fluency_min":60,"tone_min":40}
    },
    "중상": {
        "text":   (65, 80),
        "speech": (70, 85),
        "video":  (75, 90),
        "emotion":(70, 90),
        "posture":(85, 98),
        "gaze":   (40, 65),
        "labels": {"speed":"보통","fluency_min":70,"tone_min":55}
    },
    "상": {
        "text":   (80, 95),
        "speech": (85, 95),
        "video":  (88, 97),
        "emotion":(80, 95),
        "posture":(88, 99),
        "gaze":   (55, 80),
        "labels": {"speed":"빠름","fluency_min":80,"tone_min":70}
    },
}

# 프로필 추첨 가중치(필요 시 조정 가능, 현재는 동일 가중치)
PROFILE_NAMES = ["초급", "중하", "중", "중상", "상"]
PROFILE_WEIGHTS = [1, 1, 1, 1, 1]  # 예: [3,3,2,1,1]로 바꾸면 초급/중하가 더 자주 나옴

# ---------------------------
# 등급/랭크 메세지
# ---------------------------
def grade_of(score: int):
    if score >= 90: return ("상위 10%", "S",  "S등급 - 탁월한 면접 실력입니다!")
    if score >= 85: return ("상위 15%", "A+","A+등급 - 매우 우수한 실력입니다.")
    if score >= 80: return ("상위 25%", "A", "A등급 - 우수한 실력입니다.")
    if score >= 75: return ("상위 35%", "B+","B+등급 - 안정적인 실력입니다.")
    if score >= 70: return ("상위 50%", "B", "B등급 - 기본기가 갖춰져 있습니다.")
    if score >= 60: return ("하위 50%", "C", "C등급 - 꾸준한 연습으로 실력을 키워나가세요!")
    return ("하위 70% 이하", "C-", "C-등급 - 기초부터 보완이 필요합니다.")

def speed_label_from(avg_speed_like: int) -> str:
    return "빠름" if avg_speed_like >= 70 else ("보통" if avg_speed_like >= 40 else "느림")

def fluency_label_from(filler_like: int) -> str:
    return "매끄러움" if filler_like >= 60 else "보통"

def tone_label_from(pitch_like: int) -> str:
    return "밝음" if pitch_like >= 70 else "단조로움"

# ---------------------------
# 유틸: 프로필 범위에서 점수 생성
# ---------------------------
def rand_in(a: int, b: int) -> int:
    return max(0, min(100, random.randint(a, b)))

def seed_dummy_data_with_profiles(target_date: datetime | None=None):
    db: Session = SessionLocal()
    now = target_date or datetime.utcnow()

    try:
        users: List[User] = (
            db.query(User).filter(User.id.between(5, 35)).order_by(User.id.asc()).all()
            #db.query(User).filter(User.id == 43).order_by(User.id.asc()).all()
        )
        if not users:
            print("User(1~35)가 없습니다.")
            return

        for user in users:
            # 1) 유저별 프로필 랜덤 배정
            profile = random.choices(PROFILE_NAMES, weights=PROFILE_WEIGHTS, k=1)[0]
            spec = PROFILE_SPECS[profile]

            # 2) 세션 생성
            session = InterviewSession(user_id=user.id, started_at=now)
            db.add(session)
            db.flush()

            # 프로필별 수치 누적
            text_scores, speech_scores, video_scores, emotion_scores = [], [], [], []

            # 3) 6문항 생성
            for order, (q_text, q_type) in enumerate(QUESTION_TEMPLATES, start=1):
                q = InterviewQuestion(
                    session_id=session.id,
                    question_order=order,
                    question_text=q_text,
                    question_type=q_type,
                    created_at=now,
                )
                db.add(q)
                db.flush()

                # 답변(약식)
                ans = InterviewAnswer(
                    session_id=session.id,
                    question_id=q.id,
                    user_id=user.id,
                    question_order=order,
                    answer_text=random.choice(ANSWER_POOL_WEAK),
                    created_at=now,
                )
                db.add(ans)

                # --- 프로필 기반 점수 생성 ---
                # 텍스트 최종 점수
                text_final = rand_in(*spec["text"])

                # 음성 내부 지표(속도/간투어/피치 유사)
                spd_like   = rand_in(max(0, spec["speech"][0]-10), min(100, spec["speech"][1]))
                filler_like= rand_in(max(0, spec["speech"][0]-5), min(100, spec["speech"][1]+5))
                pitch_like = rand_in(max(0, spec["speech"][0]-10), min(100, spec["speech"][1]+5))
                speech_final = int(round(mean([spd_like, filler_like, pitch_like])))

                # 비디오 내부 지표
                posture = rand_in(*spec["posture"])
                gaze    = rand_in(*spec["gaze"])
                video_final = int(round(posture*0.6 + gaze*0.4))
                video_final = max(0, min(100, video_final))

                # 감정
                emotion_final = rand_in(*spec["emotion"])
                emotion_best = "중립" if emotion_final < 75 else "긍정"

                # 의미(0~1 범위는 대략 변환)
                similarity = round(random.uniform(0.1, 0.9) * (text_final/100.0), 4)
                intent     = round(random.uniform(0.3, 0.9) * (text_final/100.0), 4)
                knowledge  = round(random.uniform(0.2, 0.9) * (text_final/100.0), 4)

                # 라벨
                speed_label   = speed_label_from(spd_like)
                fluency_label = fluency_label_from(filler_like)
                tone_label    = tone_label_from(pitch_like)

                # 모범답안/피드백
                model_answer = random.choice(MODEL_ANSWER_POOL)
                strengths = "솔직함" if profile in ["초급","중하"] else "논리적 구조"
                improvements = (
                    "질문 의도 파악과 기초 지식 보완 필요"
                    if profile in ["초급","중하","중"] else
                    "세부 사례의 구체화 및 임팩트 강화"
                )
                final_feedback = (
                    "질문의 핵심을 파악하고, 관련 지식과 경험을 바탕으로 구체적으로 답변하는 연습이 필요합니다."
                    if profile in ["초급","중하"]
                    else "구조화된 답변을 유지하면서 수치, 성과, 리스크 대응을 더 선명히 제시해 보세요."
                )

                # EvaluationResult 저장
                db.add(EvaluationResult(
                    user_id=user.id,
                    session_id=session.id,
                    question_id=q.id,
                    question_order=order,
                    similarity=similarity,
                    intent_score=intent,
                    knowledge_score=knowledge,
                    final_text_score=text_final,
                    model_answer=model_answer,
                    strengths=strengths,
                    improvements=improvements,
                    final_feedback=final_feedback,
                    speed_score=spd_like,
                    filler_score=filler_like,
                    pitch_score=pitch_like,
                    final_speech_score=speech_final,
                    speed_label=speed_label,
                    fluency_label=fluency_label,
                    tone_label=tone_label,
                    created_at=now,
                ))

                # VideoEvaluationResult 저장
                positive = max(0, min(100, int(emotion_final*0.3)))
                neutral  = max(0, min(100, 100 - positive - random.randint(0, 15)))
                negative = max(0, 100 - positive - neutral)
                tense    = max(0, min(100, 100 - emotion_final))

                db.add(VideoEvaluationResult(
                    user_id=user.id,
                    session_id=session.id,
                    question_id=q.id,
                    question_order=order,
                    gaze_score=gaze,
                    shoulder_warning=random.randint(0, 1 if profile in ["중상","상"] else 2),
                    hand_warning=random.randint(0, 1 if profile in ["중상","상"] else 2),
                    posture_score=posture,
                    final_video_score=video_final,
                    positive_rate=positive,
                    neutral_rate=neutral,
                    negative_rate=negative,
                    tense_rate=tense,
                    emotion_best=emotion_best,
                    emotion_score=emotion_final,
                    created_at=now,
                ))

                # 누적
                text_scores.append(text_final)
                speech_scores.append(speech_final)
                video_scores.append(video_final)
                emotion_scores.append(emotion_final)

            # 4) 평균 기반 종합 점수 및 등급
            total_score = int(round(mean([
                mean(text_scores),
                mean(speech_scores),
                mean(video_scores),
                mean(emotion_scores),
            ])))
            rank_value, grade, grade_message = grade_of(total_score)

            # 최종 리포트
            summary = FinalReportSummary(
                user_id=user.id,
                session_id=session.id,
                total_score=total_score,
                rank=rank_value,                 # 모델에서 rank 컬럼은 "rank_value"로 매핑됨
                grade=grade,
                grade_message=grade_message,
                personalized_advice=(
                    f"{profile} 프로필에 기반한 맞춤 조언입니다. "
                    "핵심 개념을 요약 노트로 정리하고, 실제 경험을 구조화하여 STAR 기법으로 답변하세요. "
                    "음성은 일정한 속도·명확한 발음을 유지하고, 시선·자세·표정 등 비언어 요소를 반복 훈련으로 보완하세요."
                ),
                created_at=now,
            )
            db.add(summary)
            db.flush()

            # 5) 강점/개선점
            db.add_all([
                ReportStrength(
                    report_id=summary.id,
                    title="감정 안정성",
                    description="감정 기복이 크지 않고 안정적으로 응대합니다.",
                    score=max(emotion_scores),
                ),
                ReportStrength(
                    report_id=summary.id,
                    title="답변 구조화",
                    description="질문 의도를 파악하여 구조적으로 답변하려는 노력이 보입니다.",
                    score=max(int(mean(text_scores)), int(mean(speech_scores))),
                ),
            ])

            db.add_all([
                ReportImprovement(
                    report_id=summary.id,
                    priority=1,
                    title="질문 의도 파악",
                    description="핵심 키워드를 먼저 정리하고, 요구사항에 직접 답하는 습관을 들이세요.",
                    score=min(35, int(mean(text_scores))),
                ),
                ReportImprovement(
                    report_id=summary.id,
                    priority=2,
                    title="구체 사례/성과 제시",
                    description="수치·성과·임팩트를 명확히 제시해 답변의 신뢰도를 높이세요.",
                    score=min(40, int(mean(text_scores + speech_scores)) // 2),
                ),
                ReportImprovement(
                    report_id=summary.id,
                    priority=3,
                    title="비언어 표현",
                    description="시선 고정, 자세 안정, 표정 관리 등을 훈련해 전달력을 강화하세요.",
                    score=min(40, int(mean(video_scores))),
                ),
            ])

            # 6) 영역별 점수(JSON 구조는 프론트가 기대하는 키를 유지)
            text_total = int(round(mean(text_scores)))
            voice_total = int(round(mean(speech_scores)))
            video_total = int(round(mean(video_scores)))
            emotion_total = int(round(mean(emotion_scores)))

            db.add_all([
                ReportAreaScore(
                    report_id=summary.id,
                    area_name="text",
                    score={
                        "total": text_total,
                        "accuracy": max(0, min(100, int(text_total*0.3))),
                        "similarity": max(0, min(100, int(text_total*0.25))),
                        "understanding": max(0, min(100, int(text_total*0.28))),
                    },
                    created_at=now,
                ),
                ReportAreaScore(
                    report_id=summary.id,
                    area_name="voice",
                    score={
                        "total": voice_total,
                        "speed": max(0, min(100, int(voice_total*0.9))),
                        "fluency": max(0, min(100, int(voice_total*1.0))),
                        "tone": max(0, min(100, int(voice_total*0.7))),
                    },
                    created_at=now,
                ),
                ReportAreaScore(
                    report_id=summary.id,
                    area_name="video",
                    score={
                        "total": video_total,
                        "posture": max(0, min(100, int(video_total*0.9))),
                        "gaze_rate": max(0, min(100, int(video_total*0.35))),
                    },
                    created_at=now,
                ),
                ReportAreaScore(
                    report_id=summary.id,
                    area_name="emotion",
                    score={
                        "total": emotion_total,
                        "positive": max(0, min(100, int(emotion_total*0.35))),
                        "neutral": max(0, min(100, 100 - int(emotion_total*0.35) - random.randint(0, 10))),
                        "negative": max(0, min(100, 100 - int(emotion_total*0.35) - max(0, 100 - int(emotion_total*0.35) - random.randint(0, 10)))),
                        "nervous": max(0, min(100, int(100 - emotion_total))),
                    },
                    created_at=now,
                ),
            ])

            # 7) 질문별 점수(리포트용)
            for order, (q_text, q_type) in enumerate(QUESTION_TEMPLATES, start=1):
                q_score = max(0, min(100, int(round(
                    (text_scores[order-1]*0.35)
                    + (speech_scores[order-1]*0.3)
                    + (video_scores[order-1]*0.2)
                    + (emotion_scores[order-1]*0.15)
                ))))
                db.add(ReportQuestionScore(
                    report_id=summary.id,
                    question_order=order,
                    question_name=f"질문 {order}",
                    question_type=q_type,
                    question_text=q_text,
                    user_answer=random.choice(ANSWER_POOL_WEAK),
                    model_answer=random.choice(MODEL_ANSWER_POOL),
                    score=q_score,
                    summary=random.choice(QUESTION_SUMMARY_POOL),
                    created_at=now,
                ))

            print(f"User {user.id}: 프로필[{profile}] total={total_score}")
        db.commit()
        print("오늘자 더미(프로필 포함) 생성 완료")

    except Exception as e:
        db.rollback()
        print("에러 발생:", e)

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    from datetime import datetime

    # python dummy.py 2025-01-01
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        seed_dummy_data_with_profiles(target_date)
    else:
        seed_dummy_data_with_profiles()

