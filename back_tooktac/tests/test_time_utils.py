"""utils/time_utils.py — UTC 저장/KST 조회 변환 유닛 테스트"""
from datetime import date, datetime

from app.utils.time_utils import kst_day_utc_range, kst_today, to_kst, utcnow_naive


def test_utcnow_naive_is_naive():
    now = utcnow_naive()
    assert now.tzinfo is None


def test_to_kst_shifts_nine_hours():
    utc = datetime(2026, 7, 3, 0, 30, 0)  # UTC 00:30
    kst = to_kst(utc)
    assert (kst.hour, kst.minute) == (9, 30)
    assert kst.date() == date(2026, 7, 3)


def test_to_kst_crosses_date_boundary():
    # UTC 7/2 16:00 = KST 7/3 01:00 → 기존 로컬 날짜 조회에서 하루 어긋나던 케이스
    utc = datetime(2026, 7, 2, 16, 0, 0)
    assert to_kst(utc).date() == date(2026, 7, 3)


def test_kst_day_utc_range():
    start, end = kst_day_utc_range(date(2026, 7, 3))
    # KST 7/3 00:00 = UTC 7/2 15:00
    assert start == datetime(2026, 7, 2, 15, 0, 0)
    assert end == datetime(2026, 7, 3, 15, 0, 0)
    assert start.tzinfo is None and end.tzinfo is None

    # 경계 검증: KST 7/3 01:00(UTC 7/2 16:00)은 구간 안, KST 7/2 23:59는 구간 밖
    assert start <= datetime(2026, 7, 2, 16, 0, 0) < end
    assert not (start <= datetime(2026, 7, 2, 14, 59, 0) < end)


def test_kst_today_type():
    assert isinstance(kst_today(), date)
