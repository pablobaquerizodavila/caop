"""Recordatorios de cobro al cliente (manual y automático, con throttling)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Contact, Customer
from app.models.settlement import Settlement
from app.models.shipment import CustomsCase, Shipment
from app.services import payments_service
from app.services.notifications import dispatch


async def _recipient(session: AsyncSession, settlement: Settlement, channel: str) -> tuple[Customer | None, str | None]:
    case = await session.get(CustomsCase, settlement.customs_case_id)
    if case is None:
        return None, None
    shipment = await session.get(Shipment, case.shipment_id)
    if shipment is None:
        return None, None
    customer = await session.get(Customer, shipment.customer_id)
    if channel == "WHATSAPP":
        contact = await session.scalar(
            select(Contact)
            .where(Contact.customer_id == shipment.customer_id, Contact.phone.is_not(None))
            .order_by(Contact.is_primary.desc())
        )
        return customer, (contact.phone if contact else None)
    to = customer.email if customer and customer.email else None
    if not to:
        contact = await session.scalar(
            select(Contact)
            .where(Contact.customer_id == shipment.customer_id, Contact.email.is_not(None))
            .order_by(Contact.is_primary.desc())
        )
        to = contact.email if contact else None
    return customer, to


async def send_reminder(
    session: AsyncSession, settlement: Settlement, *, channel: str = "EMAIL",
    force: bool = False, min_days: int = 7,
) -> dict:
    s = payments_service.summarize(settlement)
    if s["balance"] <= 0:
        return {"status": "SKIPPED", "reason": "sin saldo"}

    now = datetime.now(timezone.utc)
    if not force and settlement.last_reminder_at:
        if (now - settlement.last_reminder_at) < timedelta(days=min_days):
            return {"status": "SKIPPED", "reason": "recordado recientemente"}

    customer, to = await _recipient(session, settlement, channel)
    if not to:
        return {"status": "SKIPPED", "reason": "sin destinatario"}

    due = settlement.due_date or (settlement.issued_at.date() if settlement.issued_at else None)
    days_overdue = (date.today() - due).days if due else 0
    context = {
        "customer_name": (customer.trade_name or customer.legal_name) if customer else "Cliente",
        "settlement_number": settlement.settlement_number,
        "currency": settlement.currency,
        "balance": f"{s['balance']:,.2f}",
        "due_date": due.isoformat() if due else "—",
        "days_overdue": max(0, days_overdue),
    }
    notif = await dispatch(
        session, channel=channel, template_code="PAYMENT_REMINDER", to=to, context=context,
        customs_case_id=settlement.customs_case_id,
    )
    settlement.last_reminder_at = now
    await session.flush()
    return {"status": notif.status, "to": to, "error": notif.error}


async def send_due_reminders(session: AsyncSession, min_days: int) -> dict:
    """Envía recordatorios a las liquidaciones emitidas, vencidas y con saldo (throttled)."""
    today = date.today()
    settlements = list(
        await session.scalars(select(Settlement).where(Settlement.status == "ISSUED"))
    )
    sent = 0
    for stl in settlements:
        due = stl.due_date or (stl.issued_at.date() if stl.issued_at else None)
        if due is None or today < due:
            continue  # aún no vence
        r = await send_reminder(session, stl, force=False, min_days=min_days)
        if r["status"] not in ("SKIPPED", "FAILED"):
            sent += 1
    return {"sent": sent, "evaluated": len(settlements)}
