"""Endpoints de salud (liveness / readiness)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness: el proceso responde."""
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    """Readiness: la base de datos responde."""
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
