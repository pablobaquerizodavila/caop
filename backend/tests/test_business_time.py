"""Tests de la aritmética de tiempo laborable."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.business_time import (
    DEFAULT_WORKING_HOURS,
    add_business_minutes,
    business_minutes_between,
)

TZ = "America/Guayaquil"
GYE = ZoneInfo(TZ)
WH = DEFAULT_WORKING_HOURS
HOL: set[str] = set()


def _next_weekday(d: date, wd: int) -> date:
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


def test_add_minutes_skips_weekend():
    sat = _next_weekday(date(2026, 8, 1), 5)  # sábado
    start = datetime.combine(sat, datetime.min.time(), GYE).replace(hour=10)
    # 60 min hábiles desde sábado 10:00 -> lunes 09:00 (primer tramo laborable)
    end = add_business_minutes(start, 60, TZ, WH, HOL).astimezone(GYE)
    assert end.weekday() == 0  # lunes
    assert end.hour == 9 and end.minute == 0


def test_add_minutes_within_day():
    mon = _next_weekday(date(2026, 8, 1), 0)
    start = datetime.combine(mon, datetime.min.time(), GYE).replace(hour=8)
    end = add_business_minutes(start, 480, TZ, WH, HOL).astimezone(GYE)  # 8h
    assert end.weekday() == 0 and end.hour == 16


def test_minutes_between_weekend():
    sat = _next_weekday(date(2026, 8, 1), 5)
    a = datetime.combine(sat, datetime.min.time(), GYE).replace(hour=10)
    b = add_business_minutes(a, 60, TZ, WH, HOL)
    assert round(business_minutes_between(a, b, TZ, WH, HOL)) == 60


def test_holiday_is_skipped():
    mon = _next_weekday(date(2026, 8, 1), 0)
    start = datetime.combine(mon, datetime.min.time(), GYE).replace(hour=8)
    holidays = {mon.isoformat()}  # el lunes es feriado
    end = add_business_minutes(start, 60, TZ, WH, holidays).astimezone(GYE)
    assert end.weekday() == 1 and end.hour == 9  # pasa a martes 09:00
