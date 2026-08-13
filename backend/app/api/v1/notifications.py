"""Endpoints de notificaciones y plantillas."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.notification import Notification, NotificationTemplate
from app.schemas.notification import (
    NotificationRead,
    NotificationSendRequest,
    TemplateCreate,
    TemplateRead,
)
from app.services.notification_seed import seed_notification_templates
from app.services.notifications import dispatch

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/templates/seed-defaults")
async def seed_templates(session: AsyncSession = Depends(get_session)) -> dict:
    created = await seed_notification_templates(session)
    return {"created": created}


@router.get("/templates", response_model=list[TemplateRead])
async def list_templates(session: AsyncSession = Depends(get_session)) -> list[NotificationTemplate]:
    return list(
        await session.scalars(
            select(NotificationTemplate).order_by(
                NotificationTemplate.code, NotificationTemplate.channel
            )
        )
    )


@router.post("/templates", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate, session: AsyncSession = Depends(get_session)
) -> NotificationTemplate:
    tpl = NotificationTemplate(**payload.model_dump())
    session.add(tpl)
    await session.flush()
    await session.refresh(tpl)
    return tpl


@router.post("/send", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def send_notification(
    payload: NotificationSendRequest, session: AsyncSession = Depends(get_session)
) -> Notification:
    return await dispatch(
        session,
        channel=payload.channel,
        template_code=payload.template_code,
        to=payload.to,
        context=payload.context,
        customer_id=payload.customer_id,
        customs_case_id=payload.customs_case_id,
    )


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    session: AsyncSession = Depends(get_session),
    customer_id: uuid.UUID | None = Query(None),
    customs_case_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if customer_id:
        stmt = stmt.where(Notification.customer_id == customer_id)
    if customs_case_id:
        stmt = stmt.where(Notification.customs_case_id == customs_case_id)
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    return list(await session.scalars(stmt.limit(limit)))
