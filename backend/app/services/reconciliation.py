"""Reconciliación tributaria: estimado (motor/cotización) vs. liquidación real (SENAE).

Mide la precisión del motor arancelario. El estimado se agrega desde la cotización de
origen del expediente (por componente y total). La liquidación real la ingresa el
operador. Se persiste la diferencia por total y porcentaje.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.reconciliation import TaxReconciliation
from app.models.shipment import CustomsCase, Shipment


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


async def estimate_from_case(session: AsyncSession, case: CustomsCase) -> tuple[dict, Decimal]:
    """Agrega el estimado de tributos desde la cotización de origen (por componente + total)."""
    ship = await session.get(Shipment, case.shipment_id)
    if ship is None or ship.source_quote_id is None:
        return {}, Decimal(0)
    quote = await session.scalar(select(Quote).where(Quote.id == ship.source_quote_id))
    if quote is None:
        return {}, Decimal(0)
    comps: dict[str, Decimal] = defaultdict(Decimal)
    for it in quote.items:
        for c in (it.tax_breakdown or []):
            comps[c.get("tax_type", "OTHER")] += _d(c.get("amount"))
    total = _d(quote.total_taxes)
    return {k: float(v) for k, v in comps.items()}, total


async def get_reconciliation(session: AsyncSession, case: CustomsCase) -> dict:
    """Vista actual: estimado (recalculado en vivo) + real almacenado + diferencias."""
    est, est_total = await estimate_from_case(session, case)
    rec = await session.scalar(
        select(TaxReconciliation).where(TaxReconciliation.customs_case_id == case.id)
    )
    actual = rec.actual if rec else None
    actual_total = _d(rec.actual_total) if rec else Decimal(0)
    diff = actual_total - est_total if actual else Decimal(0)
    diff_pct = (diff / est_total * 100) if (actual and est_total) else Decimal(0)
    return {
        "estimated": est,
        "estimated_total": float(est_total),
        "actual": actual,
        "actual_total": float(actual_total) if actual else None,
        "difference": float(diff) if actual else None,
        "difference_pct": float(round(diff_pct, 2)) if actual else None,
        "reason": rec.reason if rec else None,
        "recorded_at": rec.recorded_at.isoformat() if (rec and rec.recorded_at) else None,
    }


async def set_actual(
    session: AsyncSession, case: CustomsCase, actual: dict, reason: str | None, recorded_by: str | None
) -> dict:
    est, est_total = await estimate_from_case(session, case)
    rec = await session.scalar(
        select(TaxReconciliation).where(TaxReconciliation.customs_case_id == case.id)
    )
    if rec is None:
        rec = TaxReconciliation(customs_case_id=case.id)
        session.add(rec)
    clean = {k: float(_d(v)) for k, v in (actual or {}).items()}
    actual_total = sum((_d(v) for v in clean.values()), Decimal(0))
    rec.estimated = est
    rec.estimated_total = est_total
    rec.actual = clean
    rec.actual_total = actual_total
    rec.difference = actual_total - est_total
    rec.difference_pct = (rec.difference / est_total * 100) if est_total else Decimal(0)
    rec.reason = reason
    rec.recorded_by = recorded_by
    rec.recorded_at = datetime.now(timezone.utc)
    await session.flush()
    return await get_reconciliation(session, case)


async def summary(session: AsyncSession) -> dict:
    """Métricas de precisión del motor sobre los expedientes reconciliados."""
    recs = list(await session.scalars(
        select(TaxReconciliation).where(TaxReconciliation.recorded_at.is_not(None))
    ))
    n = len(recs)
    if n == 0:
        return {"count": 0, "avg_abs_difference_pct": None, "within_1pct": 0,
                "total_estimated": 0.0, "total_actual": 0.0}
    abs_pcts = [abs(float(r.difference_pct)) for r in recs]
    within_1 = sum(1 for p in abs_pcts if p <= 1.0)
    return {
        "count": n,
        "avg_abs_difference_pct": round(sum(abs_pcts) / n, 2),
        "within_1pct": within_1,
        "total_estimated": round(sum(float(r.estimated_total) for r in recs), 2),
        "total_actual": round(sum(float(r.actual_total) for r in recs), 2),
    }


async def _case(session: AsyncSession, case_id: uuid.UUID) -> CustomsCase | None:
    return await session.get(CustomsCase, case_id)
