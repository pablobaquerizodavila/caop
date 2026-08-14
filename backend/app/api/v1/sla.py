"""Endpoints del motor de SLA: seed, evaluación y consulta."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.sla import SLAInstance
from app.schemas.sla import SlaInstanceRead
from app.services.sla_engine import evaluate_all
from app.services.sla_seed import seed_sla_config

router = APIRouter(prefix="/sla", tags=["sla"])


@router.post("/seed-defaults")
async def seed_defaults(session: AsyncSession = Depends(get_session)) -> dict:
    return await seed_sla_config(session)


@router.post("/evaluate")
async def evaluate(session: AsyncSession = Depends(get_session)) -> dict:
    """Recalcula estado/escalamiento de los SLA abiertos. Idempotente (llamable por cron)."""
    return await evaluate_all(session)


@router.get("", response_model=list[SlaInstanceRead])
async def list_sla(
    session: AsyncSession = Depends(get_session),
    status_filter: str | None = Query(None, alias="status"),
    entity_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[SLAInstance]:
    stmt = select(SLAInstance).order_by(SLAInstance.deadline)
    if status_filter:
        stmt = stmt.where(SLAInstance.status == status_filter)
    if entity_id:
        stmt = stmt.where(SLAInstance.entity_id == entity_id)
    return list(await session.scalars(stmt.limit(limit)))
