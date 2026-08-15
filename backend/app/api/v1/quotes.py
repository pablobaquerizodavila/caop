"""Endpoints de Cotización + Landed Cost."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Customer
from app.models.quote import CostLine, Quote, QuoteItem, QuoteStatusHistory
from app.models.shipment import CustomsCase, Shipment
from app.models.trade import CertificateOfOrigin
from app.schemas.case import CustomsCaseRead
from app.schemas.trade import CertificateCreate, CertificateRead, CertificateValidate
from app.schemas.quote import (
    LinkCustomer,
    LinkResult,
    QuoteCreate,
    QuoteReadInternal,
    QuoteReadPublic,
    StatusUpdate,
)
from app.services.conversion import ConversionError, convert_quote_to_case
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


async def _case_map(session: AsyncSession, quote_ids: list[uuid.UUID]) -> dict:
    """quote_id -> (case_id, case_number) para las cotizaciones ya convertidas."""
    if not quote_ids:
        return {}
    rows = await session.execute(
        select(Shipment.source_quote_id, CustomsCase.id, CustomsCase.case_number)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
        .where(Shipment.source_quote_id.in_(quote_ids))
    )
    return {qid: (cid, cnum) for qid, cid, cnum in rows.all()}


def _with_case(read: QuoteReadInternal, mapping: dict) -> QuoteReadInternal:
    if read.id in mapping:
        read.case_id, read.case_number = mapping[read.id]
    return read


def _items_from_payload(payload: QuoteCreate) -> list[QuoteItem]:
    """Construye los ítems y prorratea flete/seguro. Compartido por crear/editar."""
    tmp_items: list[QuoteItem] = []
    for idx, it in enumerate(payload.items, start=1):
        line_value = it.line_value if it.line_value is not None else (it.unit_price * it.quantity)
        tmp_items.append(
            QuoteItem(
                line_no=idx,
                description=it.description,
                model=it.model,
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
                attributes=it.attributes or None,
            )
        )
    _allocate(tmp_items, payload.total_freight, payload.total_insurance)
    return tmp_items


def _cost_lines_from_payload(payload: QuoteCreate) -> list[CostLine]:
    cost_lines: list[CostLine] = []
    for cl in payload.cost_lines:
        quoted = cl.quoted_amount
        if quoted is None:
            quoted = cl.estimated_amount * (Decimal(1) + cl.contingency_pct / Decimal(100))
        cost_lines.append(
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
    return cost_lines


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

    # Ítems (con prorrateo de flete/seguro) y rubros de costo.
    quote.items = _items_from_payload(payload)
    # Rubros de costo: asignar la lista completa deja la colección "cargada"
    # aun si viene vacía, evitando un lazy-load al recalcular.
    quote.cost_lines = _cost_lines_from_payload(payload)

    quote.status_history = [QuoteStatusHistory(status="DRAFT")]
    session.add(quote)
    await session.flush()
    await recompute_quote(session, quote)
    await session.flush()
    await session.refresh(quote, attribute_names=["items", "cost_lines", "status_history"])
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
    quotes = list(await session.scalars(stmt.limit(limit).offset(offset)))
    mapping = await _case_map(session, [q.id for q in quotes])
    return [_with_case(QuoteReadInternal.model_validate(q), mapping) for q in quotes]


@router.get("/{quote_id}", response_model=QuoteReadInternal)
async def get_quote(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> QuoteReadInternal:
    quote = await _load(session, quote_id)
    mapping = await _case_map(session, [quote.id])
    return _with_case(QuoteReadInternal.model_validate(quote), mapping)


@router.get("/{quote_id}/public", response_model=QuoteReadPublic)
async def get_quote_public(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> QuoteReadPublic:
    quote = await _load(session, quote_id)
    data = QuoteReadPublic.model_validate(quote)
    data.disclaimer = DISCLAIMER
    return data


@router.post("/{quote_id}/link-customer", response_model=LinkResult)
async def link_customer(
    quote_id: uuid.UUID, payload: LinkCustomer, session: AsyncSession = Depends(get_session)
) -> Quote:
    """Vincula/reasigna un cliente a la cotización. Si ya tiene expediente, lo propaga."""
    customer = await session.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    quote = await _load(session, quote_id)
    quote.customer_id = customer.id
    # UPDATE masivo del expediente (si existe) sin cargar el objeto ni sus relaciones.
    await session.execute(
        update(Shipment).where(Shipment.source_quote_id == quote.id).values(customer_id=customer.id)
    )
    await session.flush()
    return quote


@router.post("/{quote_id}/recompute", response_model=QuoteReadInternal)
async def recompute(quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Quote:
    quote = await _load(session, quote_id)
    if quote.status != "DRAFT":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo se puede recalcular una cotización en DRAFT"
        )
    await recompute_quote(session, quote)
    await session.flush()
    await session.refresh(quote, attribute_names=["items", "cost_lines", "status_history"])
    return quote


@router.put("/{quote_id}", response_model=QuoteReadInternal)
async def update_quote(
    quote_id: uuid.UUID, payload: QuoteCreate, session: AsyncSession = Depends(get_session)
) -> Quote:
    """Edita una cotización en DRAFT: reemplaza cabecera, ítems y rubros, y recalcula."""
    quote = await _load(session, quote_id)
    if quote.status != "DRAFT":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Solo se puede editar una cotización en DRAFT"
        )
    quote.customer_id = payload.customer_id
    quote.transport_mode = payload.transport_mode
    quote.load_type = payload.load_type
    quote.incoterm = payload.incoterm
    quote.origin_country = payload.origin_country
    quote.currency = payload.currency
    quote.exchange_rate = payload.exchange_rate
    quote.exchange_rate_date = payload.exchange_rate_date
    if payload.calculation_date:
        quote.calculation_date = payload.calculation_date
    quote.expected_import_date = payload.expected_import_date
    quote.valid_until = payload.valid_until
    quote.notes = payload.notes
    # Reemplaza ítems y rubros (cascade delete-orphan borra los anteriores).
    quote.items = _items_from_payload(payload)
    quote.cost_lines = _cost_lines_from_payload(payload)
    await session.flush()
    await recompute_quote(session, quote)
    await session.flush()
    await session.refresh(quote, attribute_names=["items", "cost_lines", "status_history"])
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
    # Al ACEPTAR se exige cliente vinculado (se convertirá en expediente).
    if payload.status == "ACCEPTED" and quote.customer_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Vincula un cliente a la cotización antes de aceptarla (se convierte en expediente).",
        )

    quote.status = payload.status
    quote.status_history.append(
        QuoteStatusHistory(status=payload.status, channel=payload.channel, meta=payload.meta)
    )
    await session.flush()

    # AUTOMATION FIRST: aceptar => crear expediente automáticamente (idempotente).
    if payload.status == "ACCEPTED":
        await convert_quote_to_case(session, quote)

    await session.refresh(quote, attribute_names=["items", "cost_lines", "status_history"])
    return quote


@router.post("/{quote_id}/convert", response_model=CustomsCaseRead, status_code=201)
async def convert_quote(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CustomsCase:
    """Convierte manualmente la cotización en expediente (idempotente)."""
    quote = await _load(session, quote_id)
    try:
        case = await convert_quote_to_case(session, quote)
    except ConversionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await session.flush()
    return case


@router.get("/{quote_id}/case", response_model=CustomsCaseRead)
async def get_quote_case(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CustomsCase:
    quote = await _load(session, quote_id)
    shipment = await session.scalar(select(Shipment).where(Shipment.source_quote_id == quote.id))
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La cotización aún no tiene expediente")
    case = await session.scalar(
        select(CustomsCase).where(CustomsCase.shipment_id == shipment.id)
    )
    return case


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
    new.items = [
        QuoteItem(
            line_no=it.line_no, description=it.description, hs_code=it.hs_code,
            hs_status=it.hs_status, origin_country=it.origin_country,
            commercial_agreement=it.commercial_agreement, quantity=it.quantity,
            unit=it.unit, unit_price=it.unit_price, line_value=it.line_value,
            weight=it.weight, freight_alloc=it.freight_alloc,
            insurance_alloc=it.insurance_alloc,
        )
        for it in src.items
    ]
    new.cost_lines = [
        CostLine(
            category=cl.category, description=cl.description,
            estimated_amount=cl.estimated_amount, contingency_pct=cl.contingency_pct,
            quoted_amount=cl.quoted_amount, confidence=cl.confidence,
            is_included=cl.is_included,
        )
        for cl in src.cost_lines
    ]
    new.status_history = [QuoteStatusHistory(status="DRAFT")]
    session.add(new)
    await session.flush()
    await recompute_quote(session, new)
    await session.flush()
    await session.refresh(new, attribute_names=["items", "cost_lines", "status_history"])
    return new


# ---------- Certificados de origen ----------
async def _recompute_quote(session: AsyncSession, quote_id: uuid.UUID) -> None:
    quote = await _load(session, quote_id)
    await recompute_quote(session, quote)
    await session.flush()


@router.get("/{quote_id}/certificates", response_model=list[CertificateRead])
async def list_certificates(
    quote_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[CertificateOfOrigin]:
    return list(await session.scalars(
        select(CertificateOfOrigin).where(CertificateOfOrigin.quote_id == quote_id)
        .order_by(CertificateOfOrigin.created_at.desc())
    ))


@router.post("/{quote_id}/certificates", response_model=CertificateRead, status_code=201)
async def add_certificate(
    quote_id: uuid.UUID, payload: CertificateCreate, session: AsyncSession = Depends(get_session)
) -> CertificateOfOrigin:
    await _load(session, quote_id)
    data = payload.model_dump()
    if data.get("issuing_country"):
        data["issuing_country"] = data["issuing_country"].upper()
    cert = CertificateOfOrigin(quote_id=quote_id, **data)
    session.add(cert)
    await session.flush()
    await _recompute_quote(session, quote_id)  # por si nace VALID en el futuro (hoy PENDING)
    await session.refresh(cert)
    return cert


@router.patch("/{quote_id}/certificates/{cert_id}", response_model=CertificateRead)
async def validate_certificate(
    quote_id: uuid.UUID, cert_id: uuid.UUID, payload: CertificateValidate,
    session: AsyncSession = Depends(get_session),
) -> CertificateOfOrigin:
    cert = await session.get(CertificateOfOrigin, cert_id)
    if cert is None or cert.quote_id != quote_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificado no encontrado")
    cert.validation_status = payload.validation_status
    if payload.notes is not None:
        cert.notes = payload.notes
    await session.flush()
    await _recompute_quote(session, quote_id)  # actualiza 'certificate_present' de la preferencia
    await session.refresh(cert)
    return cert


@router.delete("/{quote_id}/certificates/{cert_id}", status_code=204)
async def delete_certificate(
    quote_id: uuid.UUID, cert_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    cert = await session.get(CertificateOfOrigin, cert_id)
    if cert is not None and cert.quote_id == quote_id:
        await session.delete(cert)
        await session.flush()
        await _recompute_quote(session, quote_id)
