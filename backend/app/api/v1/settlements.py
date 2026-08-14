"""Endpoints de liquidación al cliente (estado de cuenta por expediente)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Customer
from app.models.settlement import Settlement, SettlementLine
from app.models.shipment import CustomsCase, Shipment
from app.schemas.settlement import (
    SettlementLineCreate,
    SettlementLineUpdate,
    SettlementRead,
    SettlementUpdate,
)
from app.services import settlement_service
from app.services.settlement_pdf import build_settlement_pdf
from app.services.storage import StorageService, get_storage

router = APIRouter(tags=["settlements"])


async def _case(session: AsyncSession, case_id: uuid.UUID) -> CustomsCase:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    return case


async def _stl(session: AsyncSession, settlement_id: uuid.UUID) -> Settlement:
    stl = await session.get(Settlement, settlement_id)
    if stl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Liquidación no encontrada")
    return stl


@router.get("/cases/{case_id}/settlement", response_model=SettlementRead | None)
async def get_settlement(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Settlement | None:
    return await settlement_service.get_for_case(session, case_id)


@router.post("/cases/{case_id}/settlement", response_model=SettlementRead, status_code=201)
async def create_settlement(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Settlement:
    case = await _case(session, case_id)
    return await settlement_service.build_draft(session, case)


@router.patch("/settlements/{settlement_id}", response_model=SettlementRead)
async def update_settlement(
    settlement_id: uuid.UUID, payload: SettlementUpdate, session: AsyncSession = Depends(get_session)
) -> Settlement:
    stl = await _stl(session, settlement_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(stl, field, value)
    await session.flush()
    return await settlement_service.recompute(session, stl)


@router.post("/settlements/{settlement_id}/issue", response_model=SettlementRead)
async def issue_settlement(
    settlement_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Settlement:
    return await settlement_service.issue(session, await _stl(session, settlement_id))


@router.post("/settlements/{settlement_id}/lines", response_model=SettlementRead, status_code=201)
async def add_line(
    settlement_id: uuid.UUID, payload: SettlementLineCreate,
    session: AsyncSession = Depends(get_session),
) -> Settlement:
    stl = await _stl(session, settlement_id)
    session.add(SettlementLine(settlement_id=stl.id, **payload.model_dump()))
    await session.flush()
    return await settlement_service.recompute(session, stl)


@router.patch("/settlement-lines/{line_id}", response_model=SettlementRead)
async def update_line(
    line_id: uuid.UUID, payload: SettlementLineUpdate,
    session: AsyncSession = Depends(get_session),
) -> Settlement:
    line = await session.get(SettlementLine, line_id)
    if line is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rubro no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(line, field, value)
    await session.flush()
    stl = await _stl(session, line.settlement_id)
    return await settlement_service.recompute(session, stl)


@router.delete("/settlement-lines/{line_id}", response_model=SettlementRead)
async def delete_line(
    line_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Settlement:
    line = await session.get(SettlementLine, line_id)
    if line is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rubro no encontrado")
    settlement_id = line.settlement_id
    await session.delete(line)
    await session.flush()
    stl = await _stl(session, settlement_id)
    return await settlement_service.recompute(session, stl)


@router.post("/settlements/{settlement_id}/pdf")
async def generate_pdf(
    settlement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> dict:
    stl = await _stl(session, settlement_id)
    case = await session.get(CustomsCase, stl.customs_case_id)
    customer_name = "Cliente"
    if case:
        shipment = await session.get(Shipment, case.shipment_id)
        if shipment:
            customer = await session.get(Customer, shipment.customer_id)
            if customer:
                customer_name = customer.trade_name or customer.legal_name
    pdf = await run_in_threadpool(
        build_settlement_pdf, stl, case.case_number if case else "-", customer_name
    )
    key = f"settlements/{stl.id}/{stl.settlement_number}.pdf"
    await run_in_threadpool(storage.ensure_bucket)
    await run_in_threadpool(storage.put_object, key, pdf, "application/pdf")
    stl.pdf_object_key = key
    await session.flush()
    return {"object_key": key, "size": len(pdf)}


@router.get("/settlements/{settlement_id}/pdf/download")
async def download_pdf(
    settlement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> dict:
    stl = await _stl(session, settlement_id)
    if not stl.pdf_object_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF no generado")
    url = await run_in_threadpool(storage.presigned_get_url, stl.pdf_object_key, 3600)
    return {"url": url, "expires_seconds": 3600}
