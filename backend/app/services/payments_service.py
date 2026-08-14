"""Cobranza: pagos contra la liquidación, saldo/estado y cuentas por cobrar (aging)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.settlement import Payment, Settlement
from app.models.shipment import CustomsCase, Shipment

CENT = Decimal("0.01")


def summarize(settlement: Settlement) -> dict:
    total = Decimal(settlement.total or 0)
    paid = sum((Decimal(p.amount or 0) for p in settlement.payments), Decimal(0))
    balance = (total - paid).quantize(CENT)
    if paid <= 0:
        status = "PENDING"
    elif balance <= 0:
        status = "PAID"
    else:
        status = "PARTIAL"
    return {"total": float(total), "paid": float(paid.quantize(CENT)),
            "balance": float(balance), "status": status}


def _due(settlement: Settlement) -> date | None:
    if settlement.due_date:
        return settlement.due_date
    return settlement.issued_at.date() if settlement.issued_at else None


def _bucket(days: int) -> str:
    if days <= 0:
        return "corriente"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    return "60+"


async def add_payment(session: AsyncSession, settlement: Settlement, **data) -> Payment:
    payment = Payment(settlement_id=settlement.id, **data)
    session.add(payment)
    await session.flush()
    return payment


async def receivables(session: AsyncSession) -> dict:
    """Liquidaciones emitidas con saldo pendiente, con antigüedad (aging)."""
    today = date.today()
    rows = await session.execute(
        select(Settlement, Customer.legal_name)
        .join(CustomsCase, Settlement.customs_case_id == CustomsCase.id)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .join(Customer, Shipment.customer_id == Customer.id, isouter=True)
        .where(Settlement.status == "ISSUED")
        .order_by(Settlement.issued_at)
    )
    items: list[dict] = []
    totals = {"corriente": 0.0, "1-30": 0.0, "31-60": 0.0, "60+": 0.0}
    total_balance = 0.0
    for stl, customer_name in rows.all():
        s = summarize(stl)
        if s["balance"] <= 0:
            continue
        due = _due(stl)
        days = (today - due).days if due else 0
        bucket = _bucket(days)
        totals[bucket] = round(totals[bucket] + s["balance"], 2)
        total_balance = round(total_balance + s["balance"], 2)
        items.append({
            "settlement_id": str(stl.id),
            "settlement_number": stl.settlement_number,
            "customs_case_id": str(stl.customs_case_id) if stl.customs_case_id else None,
            "customer": customer_name or "—",
            "currency": stl.currency,
            "total": s["total"], "paid": s["paid"], "balance": s["balance"],
            "due_date": due.isoformat() if due else None,
            "days_overdue": max(0, days),
            "bucket": bucket,
        })
    items.sort(key=lambda x: x["days_overdue"], reverse=True)
    return {"items": items, "aging": totals, "total_balance": total_balance}
