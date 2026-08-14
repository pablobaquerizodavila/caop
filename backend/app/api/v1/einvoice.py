"""Endpoints de facturación electrónica SRI (modo simulador, sin transmisión real)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Customer
from app.models.einvoice import ElectronicInvoice
from app.models.settlement import Settlement
from app.models.shipment import CustomsCase, Shipment
from app.schemas.einvoice import EinvoiceAuthorizeRequest, EinvoiceRead
from app.services import sri_service
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
