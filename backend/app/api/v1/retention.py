"""Endpoints de comprobante de retención SRI (modo simulador, sin transmisión real)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.retention import RetentionVoucher
from app.schemas.retention import RetentionAuthorize, RetentionCreate, RetentionRead
from app.services import retention_service
from app.services.sri_service import SriError

router = APIRouter(prefix="/retentions", tags=["retention"])


async def _rv(session: AsyncSession, rv_id: uuid.UUID) -> RetentionVoucher:
    rv = await session.get(RetentionVoucher, rv_id)
    if rv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Retención no encontrada")
    return rv


@router.get("", response_model=list[RetentionRead])
async def list_retentions(session: AsyncSession = Depends(get_session)) -> list[RetentionVoucher]:
    return await retention_service.list_vouchers(session)


@router.post("", response_model=RetentionRead, status_code=201)
async def create_retention(
    payload: RetentionCreate, session: AsyncSession = Depends(get_session)
) -> RetentionVoucher:
    data = payload.model_dump(exclude={"lines"})
    lines = [ln.model_dump() for ln in payload.lines]
    try:
        return await retention_service.create(session, data, lines)
    except SriError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/{rv_id}", response_model=RetentionRead)
async def get_retention(
    rv_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RetentionVoucher:
    return await _rv(session, rv_id)


@router.post("/{rv_id}/authorize", response_model=RetentionRead)
async def authorize_retention(
    rv_id: uuid.UUID, payload: RetentionAuthorize, session: AsyncSession = Depends(get_session)
) -> RetentionVoucher:
    return await retention_service.authorize(session, await _rv(session, rv_id), payload.scenario)


@router.get("/{rv_id}/xml")
async def get_retention_xml(
    rv_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    rv = await _rv(session, rv_id)
    return Response(
        content=rv.xml or "", media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{rv.access_key}.xml"'},
    )
