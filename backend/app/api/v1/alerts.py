"""Endpoints de alertas proactivas: excepciones de la operación y envío de digest."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


class DigestSendRequest(BaseModel):
    to: list[str] | None = None  # si se omite, usa los destinatarios configurados


@router.get("/exceptions")
async def list_exceptions(session: AsyncSession = Depends(get_session)) -> dict:
    """Excepciones actuales (demurrage, almacenaje, SLA y control previo en riesgo)."""
    return await alerts.gather_exceptions(session)


@router.post("/digest/send")
async def send_digest(
    payload: DigestSendRequest | None = None, session: AsyncSession = Depends(get_session)
) -> dict:
    """Envía el digest de excepciones ahora (a los destinatarios indicados o configurados)."""
    recipients = payload.to if payload else None
    return await alerts.send_digest(session, recipients=recipients)
