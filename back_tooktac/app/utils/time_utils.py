"""시간대 처리 유틸.

저장은 naive UTC로 통일하고, 사용자에게 보여주는 '날짜' 기준은 KST로 변환한다.
(기존에는 저장 utcnow / 조회 datetime.now(KST 로컬)가 섞여 있어
KST 오전 9시 이전 세션의 날짜별 조회가 하루 어긋났다.)
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, text

KST = timezone(timedelta(hours=9))


def utcnow_naive() -> datetime:
    """DB 저장용 naive UTC now (datetime.utcnow의 deprecated 대체)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_kst(dt_utc_naive: datetime) -> datetime:
    """naive UTC → aware KST"""
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(KST)


def kst_today() -> date:
    return datetime.now(KST).date()


def kst_day_utc_range(target: date) -> tuple[datetime, datetime]:
    """KST 기준 하루(target)의 [시작, 끝) 구간을 naive UTC로 반환.

    started_at(naive UTC) 컬럼을 'KST 날짜'로 필터링할 때 사용:
        start, end = kst_day_utc_range(d)
        query.filter(col >= start, col < end)
    """
    start_kst = datetime(target.year, target.month, target.day, tzinfo=KST)
    start_utc = start_kst.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, start_utc + timedelta(days=1)


def kst_date_expr(column):
    """SQL에서 naive UTC 컬럼을 KST 날짜로 변환하는 표현식 (MySQL, tz 테이블 불필요)"""
    return func.date(func.date_add(column, text("INTERVAL 9 HOUR")))
