"""Track & Trace.

- Router público (SIN auth): la vista de seguimiento del cliente por token.
- Router de gestión (protegido): generar/rotar/activar el enlace y enviarlo al cliente.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Contact, Customer
from app.models.shipment import CustomsCase, Shipment
from app.schemas.tracking import (
    TrackingLink,
    TrackingSend,
    TrackingSendResult,
    TrackingToggle,
    TrackView,
)
from app.services import tracking
from app.services.notifications import dispatch

# ---------- Público (sin autenticación) ----------
public_router = APIRouter(tags=["track"])


@public_router.get("/track/{token}", response_model=TrackView)
async def track_public(token: str, session: AsyncSession = Depends(get_session)) -> TrackView:
    case = await tracking.get_case_by_token(session, token)
    if case is None or not case.tracking_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Seguimiento no disponible")
    return await tracking.build_view(session, case)


# ---------- Gestión (protegido con Keycloak) ----------
admin_router = APIRouter(tags=["track-admin"])


async def _load_case(session: AsyncSession, case_id: uuid.UUID) -> CustomsCase:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    return case


def _link(case: CustomsCase) -> TrackingLink:
    return TrackingLink(
        token=case.tracking_token or "",
        url=tracking.public_url(case.tracking_token) if case.tracking_token else "",
        enabled=case.tracking_enabled,
    )


@admin_router.get("/cases/{case_id}/tracking", response_model=TrackingLink)
async def get_tracking(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TrackingLink:
    case = await _load_case(session, case_id)
    await tracking.ensure_token(session, case)
    return _link(case)


@admin_router.post("/cases/{case_id}/tracking/rotate", response_model=TrackingLink)
async def rotate_tracking(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TrackingLink:
    case = await _load_case(session, case_id)
    case.tracking_token = tracking.generate_token()
    await session.flush()
    return _link(case)


@admin_router.patch("/cases/{case_id}/tracking", response_model=TrackingLink)
async def toggle_tracking(
    case_id: uuid.UUID, payload: TrackingToggle, session: AsyncSession = Depends(get_session)
) -> TrackingLink:
    case = await _load_case(session, case_id)
    case.tracking_enabled = payload.enabled
    await tracking.ensure_token(session, case)
    await session.flush()
    return _link(case)


async def _resolve_recipient(
    session: AsyncSession, case: CustomsCase, payload: TrackingSend
) -> str | None:
    if payload.to:
        return payload.to
    shipment = await session.get(Shipment, case.shipment_id)
    if not shipment:
        return None
    customer = await session.get(Customer, shipment.customer_id)
    if payload.channel == "WHATSAPP":
        contact = await session.scalar(
            select(Contact)
            .where(Contact.customer_id == shipment.customer_id, Contact.phone.is_not(None))
            .order_by(Contact.is_primary.desc())
        )
        return contact.phone if contact else None
    return customer.email if customer else None


@admin_router.post("/cases/{case_id}/tracking/send", response_model=TrackingSendResult)
async def send_tracking(
    case_id: uuid.UUID, payload: TrackingSend, session: AsyncSession = Depends(get_session)
) -> TrackingSendResult:
    case = await _load_case(session, case_id)
    await tracking.ensure_token(session, case)
    if not case.tracking_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "El enlace de seguimiento está desactivado")

    to = await _resolve_recipient(session, case, payload)
    if not to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No hay destinatario: el cliente no tiene email/teléfono y no se indicó 'to'.",
        )

    shipment = await session.get(Shipment, case.shipment_id)
    customer = await session.get(Customer, shipment.customer_id) if shipment else None
    context = {
        "customer_name": (customer.trade_name or customer.legal_name) if customer else "Cliente",
        "case_number": case.case_number,
        "tracking_url": tracking.public_url(case.tracking_token),
    }
    notif = await dispatch(
        session,
        channel=payload.channel,
        template_code="TRACKING_LINK",
        to=to,
        context=context,
        customer_id=shipment.customer_id if shipment else None,
        customs_case_id=case.id,
    )
    return TrackingSendResult(status=notif.status, to=to, error=notif.error)
