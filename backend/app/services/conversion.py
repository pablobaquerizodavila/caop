"""Conversión automática Cotización aceptada → Expediente.

Materializa el "flujo estrella": al aceptar una cotización se crean, sin redigitar,
el Shipment, el CustomsCase, el checklist documental, el SLA y los eventos.
Idempotente: no crea el expediente dos veces para la misma cotización.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist import ChecklistItem
from app.models.customer import Contact, Customer
from app.models.quote import Quote
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.services.checklist import CaseContext, generate_checklist, recompute_readiness
from app.services.notifications import dispatch
from app.services.sla_engine import create_case_sla


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

    await create_case_sla(session, case.id, "DOCUMENTS_COMPLETE")
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

    await _notify_documents_required(session, quote, case)
    await session.flush()
    return case


async def _customer_email(session: AsyncSession, customer_id) -> tuple[Customer | None, str | None]:
    customer = await session.get(Customer, customer_id)
    if customer and customer.email:
        return customer, customer.email
    contact = await session.scalar(
        select(Contact)
        .where(Contact.customer_id == customer_id)
        .order_by(Contact.is_primary.desc())
    )
    return customer, (contact.email if contact else None)


async def _notify_documents_required(
    session: AsyncSession, quote: Quote, case: CustomsCase
) -> None:
    """Best-effort: solicita al cliente los documentos bloqueantes faltantes."""
    customer, email = await _customer_email(session, quote.customer_id)
    missing = list(
        await session.scalars(
            select(ChecklistItem).where(
                ChecklistItem.customs_case_id == case.id,
                ChecklistItem.blocking.is_(True),
                ChecklistItem.status != "COMPLETE",
            )
        )
    )
    missing_docs = ", ".join(m.doc_type for m in missing) or "ninguno"
    if not email:
        session.add(
            CaseEvent(
                customs_case_id=case.id,
                event_type="NOTIFY_SKIPPED_NO_EMAIL",
                event_source="SYSTEM",
            )
        )
        return
    try:
        notif = await dispatch(
            session,
            channel="EMAIL",
            template_code="DOCUMENT_REQUIRED",
            to=email,
            context={
                "customer_name": customer.legal_name if customer else "",
                "case_number": case.case_number,
                "missing_docs": missing_docs,
            },
            customer_id=quote.customer_id,
            customs_case_id=case.id,
        )
        session.add(
            CaseEvent(
                customs_case_id=case.id,
                event_type="DOCUMENT_REQUIRED_SENT",
                event_source="SYSTEM",
                normalized_payload={"to": email, "status": notif.status},
            )
        )
    except Exception as exc:  # noqa: BLE001
        session.add(
            CaseEvent(
                customs_case_id=case.id,
                event_type="NOTIFY_FAILED",
                event_source="SYSTEM",
                normalized_payload={"error": str(exc)[:200]},
            )
        )
