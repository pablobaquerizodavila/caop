"""Motor de almacenaje: free days, último día libre, costo estimado y alarmas.

Estima el costo de permanencia en bodega/depósito temporal tras los días libres,
según el tipo de tarifa. Estimador configurable — no una tarifa oficial.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass
class StorageResult:
    last_free_day: date | None
    days_to_last_free_day: int | None
    days_overdue: int
    estimated_storage: Decimal
    alarm: str  # OK / WARN / AT_RISK / CRITICAL

    @property
    def at_risk(self) -> bool:
        return self.alarm in ("WARN", "AT_RISK", "CRITICAL")


def compute(storage, today: date) -> StorageResult:
    """Calcula el estado de almacenaje de un lote a una fecha de referencia."""
    lfd: date | None = None
    if storage.entry_date and storage.free_days is not None:
        lfd = storage.entry_date + timedelta(days=int(storage.free_days))

    withdrawn = storage.status == "WITHDRAWN" or storage.withdrawal_date is not None
    end = storage.withdrawal_date or today

    days_overdue = 0
    est = Decimal(0)
    if lfd is not None and end > lfd:
        days_overdue = (end - lfd).days
        rate = Decimal(storage.daily_rate or 0)
        rate_type = (storage.rate_type or "PER_DAY").upper()
        if rate_type == "PER_KG_DAY":
            weight = Decimal(storage.chargeable_weight_kg or 0)
            est = Decimal(days_overdue) * rate * weight
        elif rate_type == "FLAT":
            est = rate  # monto único mientras haya sobre-estadía
        else:  # PER_DAY
            est = Decimal(days_overdue) * rate

    days_to = (lfd - today).days if lfd else None

    if withdrawn or lfd is None:
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

    return StorageResult(lfd, days_to, days_overdue, est, alarm)
