"""Aritmética de tiempo laborable (horas hábiles y feriados).

Los SLA deben distinguir tiempo calendario de horas laborables. Estas funciones
puras calculan vencimientos y transcurso en minutos hábiles según un calendario
(horario por día + feriados) y su zona horaria.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def _intervals(d: date, working_hours: dict) -> list[tuple[time, time]]:
    return [(_parse(a), _parse(b)) for a, b in working_hours.get(DAYS[d.weekday()], [])]


def add_business_minutes(
    start_utc: datetime,
    minutes: float,
    tz: str,
    working_hours: dict,
    holidays: set[str],
) -> datetime:
    """Devuelve (UTC) el instante tras consumir `minutes` minutos hábiles desde start."""
    tzinfo = ZoneInfo(tz)
    cur = start_utc.astimezone(tzinfo)
    remaining = float(minutes)
    guard = 0
    while remaining > 1e-9 and guard < 4000:
        guard += 1
        d = cur.date()
        if d.isoformat() in holidays:
            cur = datetime.combine(d + timedelta(days=1), time(0, 0), tzinfo)
            continue
        for s, e in _intervals(d, working_hours):
            istart = datetime.combine(d, s, tzinfo)
            iend = datetime.combine(d, e, tzinfo)
            if cur < istart:
                cur = istart
            if cur >= iend:
                continue
            avail = (iend - cur).total_seconds() / 60
            if remaining <= avail:
                cur = cur + timedelta(minutes=remaining)
                return cur.astimezone(timezone.utc)
            remaining -= avail
            cur = iend
        # siguiente día
        cur = datetime.combine(d + timedelta(days=1), time(0, 0), tzinfo)
    return cur.astimezone(timezone.utc)


def business_minutes_between(
    a_utc: datetime,
    b_utc: datetime,
    tz: str,
    working_hours: dict,
    holidays: set[str],
) -> float:
    """Minutos hábiles transcurridos entre a y b (0 si b<=a)."""
    if b_utc <= a_utc:
        return 0.0
    tzinfo = ZoneInfo(tz)
    a = a_utc.astimezone(tzinfo)
    b = b_utc.astimezone(tzinfo)
    total = 0.0
    cur = a
    guard = 0
    while cur < b and guard < 4000:
        guard += 1
        d = cur.date()
        if d.isoformat() not in holidays:
            for s, e in _intervals(d, working_hours):
                istart = datetime.combine(d, s, tzinfo)
                iend = datetime.combine(d, e, tzinfo)
                lo = max(cur, istart)
                hi = min(b, iend)
                if hi > lo:
                    total += (hi - lo).total_seconds() / 60
        cur = datetime.combine(d + timedelta(days=1), time(0, 0), tzinfo)
    return total


DEFAULT_WORKING_HOURS = {
    "mon": [["08:00", "17:00"]],
    "tue": [["08:00", "17:00"]],
    "wed": [["08:00", "17:00"]],
    "thu": [["08:00", "17:00"]],
    "fri": [["08:00", "17:00"]],
}
