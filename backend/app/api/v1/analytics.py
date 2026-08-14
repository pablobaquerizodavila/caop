"""Endpoint de métricas ejecutivas."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.analytics import overview

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(session: AsyncSession = Depends(get_session)) -> dict:
    return await overview(session)
