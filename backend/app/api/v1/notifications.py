"""Endpoints de notificaciones y plantillas."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_session
from app.models.notification import Notification, NotificationTemplate
from app.schemas.notification import (
    NotificationRead,
    NotificationSendRequest,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
)
from app.services.notification_seed import seed_notification_templates
from app.services.notifications import dispatch

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/templates/seed-defaults", dependencies=[Depends(require_admin)])
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


@router.post("/templates", response_model=TemplateRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_template(
    payload: TemplateCreate, session: AsyncSession = Depends(get_session)
) -> NotificationTemplate:
    tpl = NotificationTemplate(**payload.model_dump())
    session.add(tpl)
    await session.flush()
    await session.refresh(tpl)
    return tpl


@router.patch("/templates/{template_id}", response_model=TemplateRead,
              dependencies=[Depends(require_admin)])
async def update_template(
    template_id: uuid.UUID, payload: TemplateUpdate, session: AsyncSession = Depends(get_session)
) -> NotificationTemplate:
    tpl = await session.get(NotificationTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plantilla no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, field, value)
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
    channel: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if customer_id:
        stmt = stmt.where(Notification.customer_id == customer_id)
    if customs_case_id:
        stmt = stmt.where(Notification.customs_case_id == customs_case_id)
    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    if channel:
        stmt = stmt.where(Notification.channel == channel)
    return list(await session.scalars(stmt.limit(limit)))


@router.post("/{notification_id}/resend", response_model=NotificationRead)
async def resend_notification(
    notification_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Notification:
    """Reintenta el envío re-renderizando desde la plantilla y el contexto guardados."""
    original = await session.get(Notification, notification_id)
    if original is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada")
    context = dict(original.payload or {})
    if original.body and "body" not in context:
        context.setdefault("body", original.body)
    return await dispatch(
        session,
        channel=original.channel,
        template_code=original.template_code or "",
        to=original.to_address,
        context=context,
        customer_id=original.customer_id,
        customs_case_id=original.customs_case_id,
    )
