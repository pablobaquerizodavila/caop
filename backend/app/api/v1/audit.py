"""Visor de auditoría / trazabilidad (solo administración y auditoría)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_audit
from app.db.session import get_session
from app.models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    timestamp: datetime
    action: str
    entity: str
    entity_id: str | None
    role: str | None
    service: str | None
    correlation_id: str | None
    old_value: dict | None
    new_value: dict | None


@router.get("", response_model=list[AuditEventRead], dependencies=[Depends(require_audit)])
async def list_audit(
    session: AsyncSession = Depends(get_session),
    entity: str | None = Query(None),
    entity_id: str | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if entity:
        stmt = stmt.where(AuditEvent.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    return list(await session.scalars(stmt.limit(limit).offset(offset)))
