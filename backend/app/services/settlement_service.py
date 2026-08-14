"""Liquidación al cliente: numeración, recálculo de totales y borrador autopoblado.

El borrador se arma con lo que ya existe en la plataforma (rubros de la cotización,
tributos estimados, almacenaje y demurrage), para que el agente solo ajuste y emita.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.settlement import Settlement, SettlementLine
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.models.warehouse import WarehouseStorage
from app.services.demurrage import compute as compute_demurrage
from app.services.warehouse import compute as compute_storage

CENT = Decimal("0.01")

# categoría del rubro de la cotización -> (kind, categoría liquidación, gravado IVA)
_CAT_MAP = {
    "FEE": ("FEE", "HONORARIO", True),
    "FREIGHT": ("DISBURSEMENT", "FLETE", False),
    "INSURANCE": ("DISBURSEMENT", "SEGURO", False),
    "PORT": ("DISBURSEMENT", "PORTUARIO", False),
    "HANDLING": ("DISBURSEMENT", "PORTUARIO", False),
    "TRANSPORT": ("DISBURSEMENT", "TRANSPORTE", False),
    "OTHER": ("DISBURSEMENT", "OTRO", False),
}


async def _next_number(session: AsyncSession, year: int) -> str:
    prefix = f"LIQ-{year}-"
    last = await session.scalar(
        select(func.max(Settlement.settlement_number)).where(
            Settlement.settlement_number.like(f"{prefix}%")
        )
    )
    seq = (int(last.split("-")[-1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


async def get_for_case(session: AsyncSession, case_id) -> Settlement | None:
    return await session.scalar(
        select(Settlement)
        .where(Settlement.customs_case_id == case_id)
        .order_by(Settlement.created_at.desc())
    )


async def recompute(session: AsyncSession, stl: Settlement) -> Settlement:
    lines = list(
        await session.scalars(
            select(SettlementLine).where(SettlementLine.settlement_id == stl.id)
        )
    )
    fees = sum((Decimal(ln.amount or 0) for ln in lines if ln.kind == "FEE"), Decimal(0))
    disb = sum((Decimal(ln.amount or 0) for ln in lines if ln.kind == "DISBURSEMENT"), Decimal(0))
    taxable = sum(
        (Decimal(ln.amount or 0) for ln in lines if ln.kind == "FEE" and ln.taxable), Decimal(0)
    )
    tax = (taxable * Decimal(stl.iva_rate or 0) / Decimal(100)).quantize(CENT)
    stl.subtotal_fees = fees.quantize(CENT)
    stl.subtotal_disbursements = disb.quantize(CENT)
    stl.tax_amount = tax
    stl.total = (fees + tax + disb).quantize(CENT)
    await session.flush()
    return stl


async def build_draft(session: AsyncSession, case: CustomsCase) -> Settlement:
    existing = await get_for_case(session, case.id)
    if existing is not None:
        return existing

    shipment = await session.get(Shipment, case.shipment_id)
    quote = (
        await session.get(Quote, shipment.source_quote_id)
        if shipment and shipment.source_quote_id
        else None
    )
    currency = quote.currency if quote else "USD"
    year = case.created_at.year if case.created_at else datetime.now(timezone.utc).year

    stl = Settlement(
        customs_case_id=case.id,
        settlement_number=await _next_number(session, year),
        currency=currency,
        iva_rate=Decimal("15.00"),
    )
    session.add(stl)
    await session.flush()

    sort = 0

    def add_line(kind: str, category: str, desc: str, amount: Decimal, taxable: bool) -> None:
        nonlocal sort
        session.add(
            SettlementLine(
                settlement_id=stl.id, kind=kind, category=category, description=desc,
                amount=Decimal(amount).quantize(CENT), taxable=taxable, sort_no=sort,
            )
        )
        sort += 1

    if quote:
        for cl in quote.cost_lines:
            amt = Decimal(cl.quoted_amount or 0)
            if amt == 0:
                continue
            kind, cat, taxable = _CAT_MAP.get(cl.category, ("DISBURSEMENT", "OTRO", False))
            add_line(kind, cat, cl.description or cat, amt, taxable)
        if quote.total_taxes and Decimal(quote.total_taxes) > 0:
            add_line("DISBURSEMENT", "TRIBUTO", "Tributos aduaneros (estimados)",
                     Decimal(quote.total_taxes), False)

    if shipment:
        today = date.today()
        wh = list(
            await session.scalars(
                select(WarehouseStorage).where(WarehouseStorage.shipment_id == shipment.id)
            )
        )
        wsum = sum(
            (compute_storage(w, today).estimated_storage for w in wh if w.status != "WITHDRAWN"),
            Decimal(0),
        )
        if wsum > 0:
            add_line("DISBURSEMENT", "ALMACENAJE", "Almacenaje / bodega (estimado)", wsum, False)

        conts = list(
            await session.scalars(
                select(Container).where(Container.shipment_id == shipment.id)
            )
        )
        dsum = sum(
            (compute_demurrage(c, today).estimated_demurrage
             for c in conts if c.status != "EMPTY_RETURNED"),
            Decimal(0),
        )
        if dsum > 0:
            add_line("DISBURSEMENT", "DEMURRAGE", "Demurrage / detención (estimado)", dsum, False)

    await session.flush()
    await recompute(session, stl)
    session.add(
        CaseEvent(
            customs_case_id=case.id, event_type="SETTLEMENT_CREATED", event_source="SYSTEM",
            normalized_payload={"settlement": stl.settlement_number, "total": float(stl.total)},
        )
    )
    await session.flush()
    return stl


async def issue(session: AsyncSession, stl: Settlement) -> Settlement:
    await recompute(session, stl)
    stl.status = "ISSUED"
    stl.issued_at = datetime.now(timezone.utc)
    session.add(
        CaseEvent(
            customs_case_id=stl.customs_case_id, event_type="SETTLEMENT_ISSUED",
            event_source="USER",
            normalized_payload={"settlement": stl.settlement_number, "total": float(stl.total)},
        )
    )
    await session.flush()
    return stl
