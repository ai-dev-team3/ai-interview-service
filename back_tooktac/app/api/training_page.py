# app/api/training_page.py
"""훈련 페이지 통계 엔드포인트 (/training/*).

랭킹(/rank/*)은 rank.py로 분리됨.
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.repository.interview import InterviewSession
from app.repository.report import (
    FinalReportSummary,
    ReportAreaScore,
    ReportQuestionScore,
)
from app.services.interview.plan import FOLLOWUP_ORDERS
from app.services.report.score_utils import avg_or_zero, find_area_score, normalize_question_type
from app.services.user.dependencies import get_current_user # 프로젝트에서 사용 중인 인증 의존성
from app.utils.time_utils import kst_date_expr, kst_day_utc_range, kst_today, to_kst  # UTC 저장 → KST 조회 변환


router = APIRouter(tags=["training"])

# -----------------------------
# 1) 모든 사용자: 일차별 평균 점수
# -----------------------------
@router.get("/training/averages")
def get_daily_average_scores(
    days: int = Query(7, ge=1, le=30, description="몇 일차까지 평균을 구할지 (기본 7)"),
    db: Session = Depends(get_db),
):
    """
    모든 사용자에 대해 '캘린더 날짜별 마지막 세션'만 남기고,
    사용자별 날짜 순서를 DENSE_RANK()로 1일차, 2일차...를 매긴 뒤,
    일차(day_index)별 final_report_summary.total_score 평균을 계산한다.
    MySQL 8+ (윈도우 함수) 전제.
    """

    # 날짜 단위 컬럼
    session_date = kst_date_expr(InterviewSession.started_at).label("session_date")

    # 같은 유저-같은 날짜 내 '마지막 세션' 선정을 위한 ROW_NUMBER()
    rn_in_day = func.row_number().over(
        partition_by=(InterviewSession.user_id, session_date),
        order_by=InterviewSession.started_at.desc()
    ).label("rn_in_day")

    # 사용자별 학습 날짜의 순번을 부여하는 DENSE_RANK() -> 1일차, 2일차...
    day_index = func.dense_rank().over(
        partition_by=InterviewSession.user_id,
        order_by=session_date.asc()
    ).label("day_index")

    # 윈도 컬럼을 포함한 세션 서브쿼리
    sess_subq = (
        select(
            InterviewSession.id.label("session_id"),
            InterviewSession.user_id.label("user_id"),
            session_date,
            rn_in_day,
            day_index
        ).subquery()
    )

    # 하루의 마지막 세션만 남긴 서브쿼리
    last_of_day_subq = (
        select(
            sess_subq.c.session_id,
            sess_subq.c.user_id,
            sess_subq.c.session_date,
            sess_subq.c.day_index
        )
        .where(sess_subq.c.rn_in_day == 1)
        .subquery()
    )

    # 마지막 세션과 final_report_summary 조인 → day_index별 total_score 수집
    joined = (
        select(
            last_of_day_subq.c.day_index,
            FinalReportSummary.total_score
        )
        .join(FinalReportSummary, FinalReportSummary.session_id == last_of_day_subq.c.session_id)
        .where(FinalReportSummary.total_score.isnot(None))
        .subquery()
    )

    # 일차별 평균
    avg_query = (
        select(
            joined.c.day_index,
            func.avg(joined.c.total_score).label("avg_score")
        )
        .where(joined.c.day_index <= days)
        .group_by(joined.c.day_index)
        .order_by(joined.c.day_index.asc())
    )

    rows = db.execute(avg_query).all()
    if not rows:
        raise HTTPException(status_code=404, detail="일차별 평균을 계산할 데이터가 없습니다.")

    # 결과: [일차1 평균, 일차2 평균, ...] 형태
    # 비어있는 일차를 0/None으로 채우려면 여기서 보정하면 됨.
    day_to_avg: Dict[int, float] = {int(r[0]): float(r[1]) for r in rows}
    result: List[float] = []
    for d in range(1, days + 1):
        if d in day_to_avg:
            result.append(round(day_to_avg[d], 2))
        else:
            # 정책 1) 비어있는 일차는 건너뜀 → 주석 처리
            # 정책 2) 0으로 채움 → 아래 주석 해제
            # result.append(0.0)
            # 정책 3) None으로 채움 → 프론트에서 보간
            # result.append(None)  # 타입 허용 시
            pass

    # 존재하는 일차만 반환하려면 아래 한 줄을 사용
    # result = [round(float(r[1]), 2) for r in rows]

    return {"success": True, "data": result}


# ---------------------------------------------------------
# 2) 로그인 사용자 기준: 다른 사용자들의 일차별 평균 (내 일수까지)
# ---------------------------------------------------------
@router.get("/training/peer-averages")
def get_peer_average_scores_up_to_my_days(
    min_population: int = Query(5, ge=1, description="일차별 평균 산출 최소 표본(미만이면 해당 일차 제외)"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """
    로그인 사용자의 '학습 일수'(내 최대 day_index)를 구하고,
    동일한 일차에 대해 '다른 사용자들'만 대상으로 final_report_summary.total_score 평균을 산출한다.
    하루에 여러 세션이면 그 날의 마지막 세션만 반영한다.
    결과는 [일차1 평균, ... 일차N 평균] 형태. N=내 학습 일수.
    MySQL 8+ (윈도우 함수) 전제.
    """

    session_date = kst_date_expr(InterviewSession.started_at).label("session_date")

    rn_in_day = func.row_number().over(
        partition_by=(InterviewSession.user_id, session_date),
        order_by=InterviewSession.started_at.desc()
    ).label("rn_in_day")

    day_index = func.dense_rank().over(
        partition_by=InterviewSession.user_id,
        order_by=session_date.asc()
    ).label("day_index")

    sess_subq = (
        select(
            InterviewSession.id.label("session_id"),
            InterviewSession.user_id.label("user_id"),
            session_date,
            rn_in_day,
            day_index
        ).subquery()
    )

    last_of_day_subq = (
        select(
            sess_subq.c.session_id,
            sess_subq.c.user_id,
            sess_subq.c.session_date,
            sess_subq.c.day_index
        )
        .where(sess_subq.c.rn_in_day == 1)
        .subquery()
    )

    # 내 최대 day_index = 내 학습 일수
    my_day_query = (
        select(func.max(last_of_day_subq.c.day_index))
        .where(last_of_day_subq.c.user_id == user_id)
    )
    my_days: Optional[int] = db.execute(my_day_query).scalar()
    if not my_days or my_days < 1:
        raise HTTPException(status_code=404, detail="사용자의 학습 일수가 없습니다. 최소 1일 이상 학습 후 다시 시도하세요.")

    # 다른 사용자들 + 내 일수까지
    joined = (
        select(
            last_of_day_subq.c.day_index,
            FinalReportSummary.total_score
        )
        .join(FinalReportSummary, FinalReportSummary.session_id == last_of_day_subq.c.session_id)
        .where(
            FinalReportSummary.total_score.isnot(None),
            last_of_day_subq.c.user_id != user_id,
            last_of_day_subq.c.day_index <= my_days
        )
        .subquery()
    )

    # 일차별 표본 수와 평균
    agg = (
        select(
            joined.c.day_index,
            func.count(joined.c.total_score).label("n"),
            func.avg(joined.c.total_score).label("avg_score")
        )
        .group_by(joined.c.day_index)
        .order_by(joined.c.day_index.asc())
    )
    rows = db.execute(agg).all()
    if not rows:
        raise HTTPException(status_code=404, detail="다른 사용자들의 일차별 데이터가 없습니다.")

    # 1..my_days까지 배열을 만들고, 표본 부족 일차는 None으로 둔다.
    day_to_avg: Dict[int, Optional[float]] = {d: None for d in range(1, int(my_days) + 1)}
    for d, n, avg in rows:
        if int(n) >= min_population:
            day_to_avg[int(d)] = float(avg)

    result: List[Optional[float]] = [
        round(day_to_avg[d], 2) if day_to_avg[d] is not None else None
        for d in range(1, int(my_days) + 1)
    ]

    return {"success": True, "my_days": int(my_days), "min_population": int(min_population), "data": result}


# ---------------------------------------------------
# 3) 7일치 주간 데이터: areas + questionTypes 포함
# ---------------------------------------------------
@router.get("/training/weekly")
def get_weekly_training_data(
        db: Session = Depends(get_db),
        user_id: int = Depends(get_current_user)
):
    today = kst_today()  # 사용자 기준(KST) 오늘
    week_ago = today - timedelta(days=6)
    weekly_data = []

    weekdays = ['월', '화', '수', '목', '금', '토', '일']

    for i in range(7):
        target_date = week_ago + timedelta(days=i)

        # 해당 KST 날짜의 최신 세션 1건 (UTC 구간으로 환산해 조회)
        day_start, day_end = kst_day_utc_range(target_date)
        session = (
            db.query(InterviewSession)
            .filter(
                InterviewSession.user_id == user_id,
                InterviewSession.started_at >= day_start,
                InterviewSession.started_at < day_end,
            )
            .order_by(InterviewSession.started_at.desc())
            .first()
        )
        if not session:
            # 세션 없으면 스킵 (프론트는 없는 날짜는 라벨만, 데이터는 비움)
            continue

        summary = db.query(FinalReportSummary).filter_by(
            user_id=user_id, session_id=session.id
        ).first()
        if not summary:
            continue

        # 영역 점수
        area_scores = db.query(ReportAreaScore).filter_by(report_id=summary.id).all()
        areas = {
            "text": find_area_score(area_scores, "text"),
            "voice": find_area_score(area_scores, "voice"),
            "video": find_area_score(area_scores, "video"),
            "emotion": find_area_score(area_scores, "emotion"),
        }

        # 질문유형별 평균 점수
        q_rows: List[ReportQuestionScore] = (
            db.query(ReportQuestionScore)
            .filter_by(report_id=summary.id)
            .all()
        )
        buckets: Dict[str, List[int]] = {
            "concept": [], "technical": [], "situation": [], "behavior": [], "followUp": []
        }

        for q in q_rows:
            score = int(q.score or 0)

            # 꼬리질문 위치는 면접 구성 단일 소스(plan.FOLLOWUP_ORDERS) 기준
            if q.question_order in FOLLOWUP_ORDERS:
                buckets["followUp"].append(score)
            else:
                key = normalize_question_type(q.question_type)
                buckets[key].append(score)

        # 평균 계산
        question_types = {k: avg_or_zero(v) for k, v in buckets.items()}

        weekly_data.append({
            "date": target_date.strftime("%m/%d"),
            "fullDate": target_date.strftime("%Y-%m-%d"),
            "score": int(summary.total_score),
            "day": weekdays[target_date.weekday()],
            "areas": areas,
            "questionTypes": question_types,
            "routineAchieved": True  # 필요 시 스트릭 로직으로 교체
        })

    return {"success": True, "data": weekly_data}


# ---------------------------------------------------
# 4) 일차 카운터 (프로그램 n일차, 훈련일수, 스트릭)
# ---------------------------------------------------
@router.get("/training/day-counters")
def get_training_day_counters(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    # 1) 사용자의 모든 세션 중 첫 세션 날짜를 가져온다.
    first_session = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.started_at.asc())
        .first()
    )

    # 2) 세션이 하나도 없으면 기본값 반환.
    if not first_session:
        return {
            "success": True,
            "data": {
                "programDayToday": 0,            # 프로그램 기준 n일차(없으면 0)
                "trainedDays": 0,                # 실제로 훈련한 날짜 수(중복 제외)
                "consecutiveStreak": 0,          # 오늘 포함 연속 스트릭
                "firstSessionDate": None,        # 첫 훈련일
                "dayIndexByDate": {}             # 날짜별 n일차 매핑
            }
        }

    # 3) 사용자 세션의 'KST 날짜'만 distinct로 정렬해 가져온다.
    #    started_at은 UTC 저장이므로 KST로 변환 후 중복 제거.
    started_rows = (
        db.query(InterviewSession.started_at)
        .filter(InterviewSession.user_id == user_id)
        .all()
    )
    distinct_dates: List[date] = sorted({to_kst(r[0]).date() for r in started_rows})

    # 4) 프로그램 기준 오늘 n일차 = (오늘 - 첫 세션일) + 1  (KST 기준)
    first_date = distinct_dates[0]
    today = kst_today()
    program_day_today = (today - first_date).days + 1

    # 5) 실제 훈련한 '일수'(중복 제거된 날짜 수)
    trained_days = len(distinct_dates)

    # 6) 날짜 → n일차 매핑 만들기(첫 훈련일을 1일차로)
    day_index_by_date: Dict[str, int] = {
        d.strftime("%Y-%m-%d"): idx + 1
        for idx, d in enumerate(distinct_dates)
    }

    # 7) 연속 스트릭 계산:
    #    가장 최근 훈련일에서 하루씩 거꾸로 내려가며 연속성 확인.
    streak = 0
    if distinct_dates:
        last = distinct_dates[-1]
        streak = 1
        i = len(distinct_dates) - 2
        cur = last
        while i >= 0:
            if (cur - distinct_dates[i]) == timedelta(days=1):
                streak += 1
                cur = distinct_dates[i]
                i -= 1
            else:
                break

    return {
        "success": True,
        "data": {
            "programDayToday": program_day_today,           # 오늘이 '몇일차'
            "trainedDays": trained_days,                    # 실제 훈련한 날짜 수
            "consecutiveStreak": streak,                    # 연속 스트릭
            "firstSessionDate": first_date.strftime("%Y-%m-%d"),
            "dayIndexByDate": day_index_by_date            # 날짜별 n일차 매핑
        }
    }


