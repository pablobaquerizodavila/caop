"""Conversión automática Cotización aceptada → Expediente.

Materializa el "flujo estrella": al aceptar una cotización se crean, sin redigitar,
el Shipment, el CustomsCase, el checklist documental, el SLA y los eventos.
Idempotente: no crea el expediente dos veces para la misma cotización.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.services.checklist import CaseContext, generate_checklist, recompute_readiness

DOCS_SLA_HOURS = 24


class ConversionError(ValueError):
    pass


async def _next_case_number(session: AsyncSession, year: int) -> str:
    prefix = f"EC-IMP-{year}-"
    last = await session.scalar(
        select(func.max(CustomsCase.case_number)).where(CustomsCase.case_number.like(f"{prefix}%"))
    )
    seq = (int(last.split("-")[-1]) + 1) if last else 1
    return f"{prefix}{seq:08d}"


async def convert_quote_to_case(session: AsyncSession, quote: Quote) -> CustomsCase:
    if quote.customer_id is None:
        raise ConversionError("La cotización no tiene un cliente vinculado; no se puede convertir.")

    # Idempotencia: si ya existe un shipment para esta cotización, devolver su caso.
    existing = await session.scalar(
        select(Shipment).where(Shipment.source_quote_id == quote.id)
    )
    if existing is not None:
        return await session.scalar(
            select(CustomsCase).where(CustomsCase.shipment_id == existing.id)
        )

    shipment = Shipment(
        customer_id=quote.customer_id,
        source_quote_id=quote.id,
        transport_mode=quote.transport_mode,
        incoterm=quote.incoterm,
        origin_country=quote.origin_country,
        status="OPEN",
    )
    session.add(shipment)
    await session.flush()

    case = CustomsCase(
        shipment_id=shipment.id,
        case_number=await _next_case_number(session, quote.calculation_date.year),
        customs_regime="10",
        current_state="CASE_CREATED",
    )
    session.add(case)
    await session.flush()

    has_agreement = any(getattr(i, "commercial_agreement", None) for i in quote.items)
    ctx = CaseContext(transport_mode=quote.transport_mode, has_agreement=has_agreement)
    await generate_checklist(session, case, ctx)
    await session.flush()

    session.add(
        SLAInstance(
            entity_type="CUSTOMS_CASE",
            entity_id=case.id,
            milestone="DOCUMENTS_COMPLETE",
            deadline=datetime.now(timezone.utc) + timedelta(hours=DOCS_SLA_HOURS),
        )
    )
    for etype, payload in [
        ("CASE_CREATED", {"quote": quote.quote_number}),
        ("CHECKLIST_GENERATED", None),
        ("DOCUMENTS_REQUESTED", None),
    ]:
        session.add(
            CaseEvent(
                customs_case_id=case.id,
                event_type=etype,
                event_source="SYSTEM",
                normalized_payload=payload,
            )
        )

    await recompute_readiness(session, case)
    await session.flush()
    return case
