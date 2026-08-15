"""Endpoints de guía de remisión SRI (modo simulador, sin transmisión real)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.waybill import WaybillGuide
from app.schemas.waybill import WaybillAuthorize, WaybillCreate, WaybillRead
from app.services import waybill_service
from app.services.sri_service import SriError

router = APIRouter(prefix="/waybills", tags=["waybill"])


async def _g(session: AsyncSession, g_id: uuid.UUID) -> WaybillGuide:
    g = await session.get(WaybillGuide, g_id)
    if g is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guía de remisión no encontrada")
    return g


@router.get("", response_model=list[WaybillRead])
async def list_waybills(session: AsyncSession = Depends(get_session)) -> list[WaybillGuide]:
    return await waybill_service.list_guides(session)


@router.post("", response_model=WaybillRead, status_code=201)
async def create_waybill(
    payload: WaybillCreate, session: AsyncSession = Depends(get_session)
) -> WaybillGuide:
    data = payload.model_dump(exclude={"items"})
    items = [it.model_dump() for it in payload.items]
    try:
        return await waybill_service.create(session, data, items)
    except SriError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/{g_id}", response_model=WaybillRead)
async def get_waybill(g_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> WaybillGuide:
    return await _g(session, g_id)


@router.post("/{g_id}/authorize", response_model=WaybillRead)
async def authorize_waybill(
    g_id: uuid.UUID, payload: WaybillAuthorize, session: AsyncSession = Depends(get_session)
) -> WaybillGuide:
    return await waybill_service.authorize(session, await _g(session, g_id), payload.scenario)


@router.get("/{g_id}/xml")
async def get_waybill_xml(
    g_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    g = await _g(session, g_id)
    return Response(
        content=g.xml or "", media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{g.access_key}.xml"'},
    )
