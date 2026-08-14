"""Endpoints de facturación electrónica SRI (modo simulador, sin transmisión real)."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.credit_note import CreditNote
from app.models.customer import Customer
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement
from app.models.shipment import CustomsCase, Shipment
from app.schemas.einvoice import (
    CreditNoteCreate,
    CreditNoteRead,
    EinvoiceAuthorizeRequest,
    EinvoiceRead,
)
from app.services import credit_note_service, sri_service
from app.services.einvoice_pdf import build_ride
from app.services.sri_service import SriError

router = APIRouter(tags=["einvoice"])


async def _invoice(session: AsyncSession, invoice_id: uuid.UUID) -> ElectronicInvoice:
    inv = await session.get(ElectronicInvoice, invoice_id)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comprobante no encontrado")
    return inv


@router.get("/settlements/{settlement_id}/invoice", response_model=EinvoiceRead | None)
async def get_invoice(
    settlement_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ElectronicInvoice | None:
    return await sri_service.get_for_settlement(session, settlement_id)


@router.post("/settlements/{settlement_id}/invoice", response_model=EinvoiceRead, status_code=201)
async def create_invoice(
    settlement_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ElectronicInvoice:
    stl = await session.get(Settlement, settlement_id)
    if stl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    try:
        return await sri_service.create_from_settlement(session, stl)
    except SriError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/invoices/{invoice_id}/authorize", response_model=EinvoiceRead)
async def authorize_invoice(
    invoice_id: uuid.UUID, payload: EinvoiceAuthorizeRequest,
    session: AsyncSession = Depends(get_session),
) -> ElectronicInvoice:
    inv = await _invoice(session, invoice_id)
    return await sri_service.authorize(session, inv, payload.scenario)


@router.get("/invoices/{invoice_id}", response_model=EinvoiceRead)
async def get_invoice_by_id(
    invoice_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ElectronicInvoice:
    return await _invoice(session, invoice_id)


@router.get("/invoices/{invoice_id}/xml")
async def get_invoice_xml(
    invoice_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    inv = await _invoice(session, invoice_id)
    return Response(
        content=inv.xml or "",
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{inv.access_key}.xml"'},
    )


async def _render_ride(session: AsyncSession, inv: ElectronicInvoice) -> bytes:
    stl = await session.get(Settlement, inv.settlement_id)
    name, ident = "Cliente", "9999999999999"
    if inv.customs_case_id:
        case = await session.get(CustomsCase, inv.customs_case_id)
        if case:
            shipment = await session.get(Shipment, case.shipment_id)
            if shipment:
                customer = await session.get(Customer, shipment.customer_id)
                if customer:
                    name, ident = customer.legal_name, customer.ruc
    return build_ride(inv, stl, name, ident)


@router.get("/invoices/{invoice_id}/ride")
async def get_invoice_ride(
    invoice_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    inv = await _invoice(session, invoice_id)
    pdf = await _render_ride(session, inv)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="RIDE-{inv.access_key}.pdf"'},
    )


# ---------- Notas de crédito ----------
async def _cn(session: AsyncSession, cn_id: uuid.UUID) -> CreditNote:
    cn = await session.get(CreditNote, cn_id)
    if cn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota de crédito no encontrada")
    return cn


@router.get("/invoices/{invoice_id}/credit-notes", response_model=list[CreditNoteRead])
async def list_credit_notes(
    invoice_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[CreditNote]:
    return await credit_note_service.list_for_invoice(session, invoice_id)


@router.post("/invoices/{invoice_id}/credit-notes", response_model=CreditNoteRead, status_code=201)
async def create_credit_note(
    invoice_id: uuid.UUID, payload: CreditNoteCreate, session: AsyncSession = Depends(get_session)
) -> CreditNote:
    inv = await _invoice(session, invoice_id)
    try:
        amount = Decimal(str(payload.amount)) if payload.amount is not None else None
        return await credit_note_service.create_from_invoice(session, inv, amount, payload.motivo)
    except SriError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/credit-notes/{cn_id}/authorize", response_model=CreditNoteRead)
async def authorize_credit_note(
    cn_id: uuid.UUID, payload: EinvoiceAuthorizeRequest,
    session: AsyncSession = Depends(get_session),
) -> CreditNote:
    return await credit_note_service.authorize(session, await _cn(session, cn_id), payload.scenario)


@router.get("/credit-notes/{cn_id}", response_model=CreditNoteRead)
async def get_credit_note(
    cn_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CreditNote:
    return await _cn(session, cn_id)


@router.get("/credit-notes/{cn_id}/xml")
async def get_credit_note_xml(
    cn_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    cn = await _cn(session, cn_id)
    return Response(
        content=cn.xml or "", media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{cn.access_key}.xml"'},
    )
