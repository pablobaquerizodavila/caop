"""Endpoints de la DAI (contra el simulador SENAE)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, require_sign
from app.db.session import get_session
from app.models.shipment import CustomsCase
from app.schemas.dai import AdvanceRequest, DeclarationRead, TransmitRequest
from app.services import dai_service

router = APIRouter(tags=["dai"])


async def _case(session: AsyncSession, case_id: uuid.UUID) -> CustomsCase:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    return case


@router.get("/cases/{case_id}/dai", response_model=DeclarationRead)
async def get_dai(case_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    dec = await dai_service.get_declaration(session, case_id)
    if dec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El expediente no tiene DAI")
    return dec


@router.post("/cases/{case_id}/dai/prepare", response_model=DeclarationRead, status_code=201)
async def prepare_dai(case_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    dec = await dai_service.prepare(session, await _case(session, case_id))
    await session.flush()
    return dec


@router.post("/cases/{case_id}/dai/sign", response_model=DeclarationRead)
async def sign_dai(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_sign),
):
    dec = await dai_service.sign(
        session, await _case(session, case_id), principal.username or principal.subject
    )
    await session.flush()
    return dec


@router.post("/cases/{case_id}/dai/transmit", response_model=DeclarationRead)
async def transmit_dai(
    case_id: uuid.UUID, payload: TransmitRequest, session: AsyncSession = Depends(get_session)
):
    dec = await dai_service.transmit(session, await _case(session, case_id), payload.scenario)
    await session.flush()
    return dec


@router.post("/cases/{case_id}/dai/advance", response_model=DeclarationRead)
async def advance_dai(
    case_id: uuid.UUID, payload: AdvanceRequest, session: AsyncSession = Depends(get_session)
):
    dec = await dai_service.advance(
        session, await _case(session, case_id), payload.aforo_channel, payload.observation
    )
    await session.flush()
    return dec


@router.post("/cases/{case_id}/dai/resolve-observation", response_model=DeclarationRead)
async def resolve_dai_observation(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    dec = await dai_service.resolve_observation(session, await _case(session, case_id))
    await session.flush()
    return dec
