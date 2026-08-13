"""Endpoints de Cotización + Landed Cost."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.schemas.quote import (
    QuoteCreate,
    QuoteReadInternal,
    QuoteReadPublic,
    StatusUpdate,
)
from app.services.quote_pdf import DISCLAIMER, build_quote_pdf
from app.services.quotation import recompute_quote
from app.services.storage import StorageService, get_storage

router = APIRouter(prefix="/quotes", tags=["quotes"])

# Transiciones de estado permitidas
TRANSITIONS = {
    "DRAFT": {"SENT", "REJECTED"},
    "SENT": {"DELIVERED", "READ", "ACCEPTED", "REJECTED", "EXPIRED"},
    "DELIVERED": {"READ", "ACCEPTED", "REJECTED", "EXPIRED"},
    "READ": {"ACCEPTED", "REJECTED", "EXPIRED"},
    "ACCEPTED": set(),
    "REJECTED": set(),
    "EXPIRED": set(),
}


async def _next_quote_number(session: AsyncSession, on: date) -> str:
    prefix = f"QT-{on.year}-"
    last = await session.scalar(
        select(func.max(Quote.quote_number)).where(Quote.quote_number.like(f"{prefix}%"))
    )
    seq = (int(last.split("-")[-1]) + 1) if last else 1
    return f"{prefix}{seq:05d}"


def _allocate(items, total_freight: Decimal | None, total_insurance: Decimal | None) -> None:
    """Prorratea flete/seguro de cabecera por valor de línea si no vienen por ítem."""
    base = sum((Decimal(i.line_value or 0) for i in items), Decimal(0))
    for i in items:
        share = (Decimal(i.line_value or 0) / base) if base else Decimal(0)
        if i.freight_alloc is None:
            i.freight_alloc = (Decimal(total_freight) * share) if total_freight else Decimal(0)
        if i.insurance_alloc is None:
            i.insurance_alloc = (Decimal(total_insurance) * share) if total_insurance else Decimal(0)


async def _load(session: AsyncSession, quote_id: uuid.UUID) -> Quote:
    quote = await session.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cotización no encontrada")
    return quote


@router.post("", response_model=QuoteReadInternal, status_code=status.HTTP_201_CREATED)
async def create_quote(payload: QuoteCreate, session: AsyncSession = Depends(get_session)) -> Quote:
    calc_date = payload.calculation_date or date.today()
    quote = Quote(
        quote_number=await _next_quote_number(session, calc_date),
        version=1,
        status="DRAFT",
        customer_id=payload.customer_id,
        transport_mode=payload.transport_mode,
        load_type=payload.load_type,
        incoterm=payload.incoterm,
        origin_country=payload.origin_country,
        currency=payload.currency,
        exchange_rate=payload.exchange_rate,
        exchange_rate_date=payload.exchange_rate_date,
        calculation_date=calc_date,
        expected_import_date=payload.expected_import_date,
        valid_until=payload.valid_until,
        notes=payload.notes,
    )

    # Ítems
    tmp_items = []
    for idx, it in enumerate(payload.items, start=1):
        line_value = it.line_value if it.line_value is not None else (it.unit_price * it.quantity)
        qi = QuoteItem(
            line_no=idx,
            description=it.description,
            hs_code=it.hs_code,
            hs_status=it.hs_status,
            origin_country=it.origin_country or payload.origin_country,
            commercial_agreement=it.commercial_agreement,
            quantity=it.quantity,
            unit=it.unit,
            unit_price=it.unit_price,
            line_value=line_value,
            weight=it.weight,
            freight_alloc=it.freight_alloc,
            insurance_alloc=it.insurance_alloc,
        )
        tmp_items.append(qi)
    _allocate(tmp_items, payload.total_freight, payload.total_insurance)
    quote.items = tmp_items

    # Rubros de costo
    for cl in payload.cost_lines:
        quoted = cl.quoted_amount
        if quoted is None:
            quoted = cl.estimated_amount * (Decimal(1) + cl.contingency_pct / Decimal(100))
        quote.cost_lines.append(
            CostLine(
                category=cl.category,
                description=cl.description,
                estimated_amount=cl.estimated_amount,
                contingency_pct=cl.contingency_pct,
                quoted_amount=quoted,
                confidence=cl.confidence,
                is_included=cl.is_included,
            )
        )

    quote.status_history.append(QuoteStatusHistory(status="DRAFT"))
    session.add(quote)
    await session.flush()
    await recompute_quote(session, quote)
    await session.flush()
    await session.refresh(quote)
    return quote


@router.get("", response_model=list[QuoteReadInternal])
async def list_quotes(
    session: AsyncSession = Depends(get_session),
    customer_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Quote]:
    stmt = select(Quote).order_by(Quote.created_at.desc())
    if customer_id:
        stmt = stmt.where(Quote.customer_id == customer_id)
    return list(await session.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{quote_id}", response_model=QuoteReadInternal)
async def get_quote(quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Quote:
    return await _load(session, quote_id)


@router.get("/{quote_id}/public", response_model=QuoteReadPublic)
async def get_quote_public(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> QuoteReadPublic:
    quote = await _load(session, quote_id)
    data = QuoteReadPublic.model_validate(quote)
    data.disclaimer = DISCLAIMER
    return data


@router.post("/{quote_id}/recompute", response_model=QuoteReadInternal)
async def recompute(quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Quote:
    quote = await _load(session, quote_id)
    if quote.status != "DRAFT":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo se puede recalcular una cotización en DRAFT"
        )
    await recompute_quote(session, quote)
    await session.flush()
    await session.refresh(quote)
    return quote


@router.post("/{quote_id}/status", response_model=QuoteReadInternal)
async def change_status(
    quote_id: uuid.UUID, payload: StatusUpdate, session: AsyncSession = Depends(get_session)
) -> Quote:
    quote = await _load(session, quote_id)
    allowed = TRANSITIONS.get(quote.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Transición inválida {quote.status} → {payload.status}",
        )
    quote.status = payload.status
    quote.status_history.append(
        QuoteStatusHistory(status=payload.status, channel=payload.channel, meta=payload.meta)
    )
    await session.flush()
    await session.refresh(quote)
    return quote


@router.post("/{quote_id}/pdf")
async def generate_pdf(
    quote_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> dict:
    quote = await _load(session, quote_id)
    pdf = build_quote_pdf(quote)
    key = f"quotes/{quote.id}/{quote.quote_number}-v{quote.version}.pdf"
    await run_in_threadpool(storage.ensure_bucket)
    await run_in_threadpool(storage.put_object, key, pdf, "application/pdf")
    quote.pdf_object_key = key
    await session.flush()
    return {"object_key": key, "size": len(pdf)}


@router.get("/{quote_id}/pdf/download")
async def download_pdf(
    quote_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> dict:
    quote = await _load(session, quote_id)
    if not quote.pdf_object_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La cotización aún no tiene PDF generado")
    url = await run_in_threadpool(storage.presigned_get_url, quote.pdf_object_key, 3600)
    return {"url": url, "expires_seconds": 3600}


@router.post("/{quote_id}/revise", response_model=QuoteReadInternal, status_code=201)
async def revise_quote(quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Quote:
    """Crea una nueva versión (DRAFT) a partir de una cotización existente."""
    src = await _load(session, quote_id)
    max_v = await session.scalar(
        select(func.max(Quote.version)).where(Quote.quote_number == src.quote_number)
    )
    new = Quote(
        quote_number=src.quote_number,
        version=(max_v or src.version) + 1,
        status="DRAFT",
        customer_id=src.customer_id,
        transport_mode=src.transport_mode,
        load_type=src.load_type,
        incoterm=src.incoterm,
        origin_country=src.origin_country,
        currency=src.currency,
        calculation_date=date.today(),
        expected_import_date=src.expected_import_date,
        valid_until=src.valid_until,
        notes=src.notes,
    )
    for it in src.items:
        new.items.append(
            QuoteItem(
                line_no=it.line_no, description=it.description, hs_code=it.hs_code,
                hs_status=it.hs_status, origin_country=it.origin_country,
                commercial_agreement=it.commercial_agreement, quantity=it.quantity,
                unit=it.unit, unit_price=it.unit_price, line_value=it.line_value,
                weight=it.weight, freight_alloc=it.freight_alloc,
                insurance_alloc=it.insurance_alloc,
            )
        )
    for cl in src.cost_lines:
        new.cost_lines.append(
            CostLine(
                category=cl.category, description=cl.description,
                estimated_amount=cl.estimated_amount, contingency_pct=cl.contingency_pct,
                quoted_amount=cl.quoted_amount, confidence=cl.confidence,
                is_included=cl.is_included,
            )
        )
    new.status_history.append(QuoteStatusHistory(status="DRAFT"))
    session.add(new)
    await session.flush()
    await recompute_quote(session, new)
    await session.flush()
    await session.refresh(new)
    return new
