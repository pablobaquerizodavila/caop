"""Endpoints VUE — documentos de control previo (contra el simulador VUE)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.shipment import CaseEvent, CustomsCase
from app.models.vue import VuePermit
from app.schemas.vue import (
    VueCatalogEntry,
    VuePermitCreate,
    VuePermitExempt,
    VuePermitRead,
    VuePermitRequest,
    VuePermitUpdate,
)
from app.services import vue_service

router = APIRouter(tags=["vue"])


def _read(permit: VuePermit) -> VuePermitRead:
    r = VuePermitRead.model_validate(permit)
    r.satisfied = permit.is_satisfied(date.today())
    return r


async def _permit_or_404(session: AsyncSession, permit_id: uuid.UUID) -> VuePermit:
    permit = await session.get(VuePermit, permit_id)
    if permit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Permiso VUE no encontrado")
    return permit


@router.get("/vue/catalog", response_model=list[VueCatalogEntry])
async def vue_catalog() -> list[dict]:
    """Catálogo de referencia de documentos de control previo (verificar normativa)."""
    return vue_service.CATALOG


@router.get("/cases/{case_id}/vue-permits", response_model=list[VuePermitRead])
async def list_permits(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[VuePermitRead]:
    return [_read(p) for p in await vue_service.list_permits(session, case_id)]


@router.post("/cases/{case_id}/vue-permits", response_model=VuePermitRead, status_code=201)
async def create_permit(
    case_id: uuid.UUID, payload: VuePermitCreate, session: AsyncSession = Depends(get_session)
) -> VuePermitRead:
    if await session.get(CustomsCase, case_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    permit = VuePermit(customs_case_id=case_id, **payload.model_dump())
    session.add(permit)
    session.add(
        CaseEvent(
            customs_case_id=case_id, event_type="VUE_PERMIT_ADDED", event_source="USER",
            normalized_payload={"entity": permit.entity, "document_code": permit.document_code},
        )
    )
    await session.flush()
    return _read(permit)


@router.patch("/vue-permits/{permit_id}", response_model=VuePermitRead)
async def update_permit(
    permit_id: uuid.UUID, payload: VuePermitUpdate, session: AsyncSession = Depends(get_session)
) -> VuePermitRead:
    permit = await _permit_or_404(session, permit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(permit, field, value)
    await session.flush()
    return _read(permit)


@router.post("/vue-permits/{permit_id}/request", response_model=VuePermitRead)
async def request_permit(
    permit_id: uuid.UUID, payload: VuePermitRequest, session: AsyncSession = Depends(get_session)
) -> VuePermitRead:
    permit = await _permit_or_404(session, permit_id)
    permit = await vue_service.request_permit(session, permit, payload.scenario)
    return _read(permit)


@router.post("/vue-permits/{permit_id}/exempt", response_model=VuePermitRead)
async def exempt_permit(
    permit_id: uuid.UUID, payload: VuePermitExempt, session: AsyncSession = Depends(get_session)
) -> VuePermitRead:
    permit = await _permit_or_404(session, permit_id)
    permit = await vue_service.mark_exempt(session, permit, payload.reason)
    return _read(permit)


@router.delete("/vue-permits/{permit_id}", status_code=204)
async def delete_permit(
    permit_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    permit = await _permit_or_404(session, permit_id)
    await session.delete(permit)
    await session.flush()
