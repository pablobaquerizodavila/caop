"""Motor de demurrage/detention: free days, last free day, money at risk y alarmas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass
class DemurrageResult:
    last_free_day: date | None
    days_to_last_free_day: int | None
    days_overdue: int
    estimated_demurrage: Decimal
    alarm: str  # OK / WARN / AT_RISK / CRITICAL

    @property
    def at_risk(self) -> bool:
        return self.alarm in ("WARN", "AT_RISK", "CRITICAL")


def compute(container, today: date) -> DemurrageResult:
    """Calcula el estado de demurrage de un contenedor a una fecha de referencia."""
    lfd: date | None = None
    if container.arrival_date and container.free_days is not None:
        lfd = container.arrival_date + timedelta(days=int(container.free_days))

    returned = container.status == "EMPTY_RETURNED" or container.empty_return_date is not None
    end = container.empty_return_date or container.gate_out_date or today

    days_overdue = 0
    est = Decimal(0)
    if lfd is not None and end > lfd:
        days_overdue = (end - lfd).days
        est = Decimal(days_overdue) * Decimal(container.daily_rate or 0)

    days_to = (lfd - today).days if lfd else None

    if returned or lfd is None:
        alarm = "OK"
    elif days_to is None:
        alarm = "OK"
    elif days_to <= 0:
        alarm = "CRITICAL"
    elif days_to == 1:
        alarm = "AT_RISK"
    elif days_to <= 3:
        alarm = "WARN"
    else:
        alarm = "OK"

    return DemurrageResult(lfd, days_to, days_overdue, est, alarm)
