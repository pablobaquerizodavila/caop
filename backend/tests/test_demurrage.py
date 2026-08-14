"""Tests unitarios del motor de demurrage."""

from datetime import date, timedelta
from decimal import Decimal

from app.models.shipment import Container
from app.services.demurrage import compute

TODAY = date(2026, 8, 14)


def _c(**kw):
    kw.setdefault("container_number", "TEST1234567")
    kw.setdefault("status", "AT_PORT")
    return Container(**kw)


def test_overdue_accrues_demurrage():
    r = compute(_c(arrival_date=TODAY - timedelta(days=10), free_days=5, daily_rate=Decimal("100")), TODAY)
    assert r.last_free_day == TODAY - timedelta(days=5)
    assert r.days_overdue == 5
    assert r.estimated_demurrage == Decimal("500")
    assert r.alarm == "CRITICAL"


def test_one_day_left_is_at_risk():
    r = compute(_c(arrival_date=TODAY - timedelta(days=4), free_days=5, daily_rate=Decimal("100")), TODAY)
    assert r.days_to_last_free_day == 1
    assert r.days_overdue == 0
    assert r.alarm == "AT_RISK"


def test_three_days_left_is_warn():
    r = compute(_c(arrival_date=TODAY - timedelta(days=2), free_days=5, daily_rate=Decimal("100")), TODAY)
    assert r.alarm == "WARN"


def test_far_future_is_ok():
    r = compute(_c(arrival_date=TODAY, free_days=10, daily_rate=Decimal("100")), TODAY)
    assert r.alarm == "OK" and r.days_overdue == 0


def test_returned_freezes_and_clears_alarm():
    r = compute(
        _c(arrival_date=TODAY - timedelta(days=10), free_days=5, daily_rate=Decimal("100"),
           status="EMPTY_RETURNED", empty_return_date=TODAY - timedelta(days=2)),
        TODAY,
    )
    # devuelto tarde: se congela en la fecha de devolución (overdue 3 días) pero sin alarma futura
    assert r.days_overdue == 3
    assert r.estimated_demurrage == Decimal("300")
    assert r.alarm == "OK"


def test_no_dates_is_ok():
    r = compute(_c(), TODAY)
    assert r.last_free_day is None and r.alarm == "OK"
