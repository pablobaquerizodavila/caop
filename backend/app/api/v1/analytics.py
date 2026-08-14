"""Endpoint de métricas ejecutivas."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.analytics import operations, overview
from app.services.payments_service import receivables

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(session: AsyncSession = Depends(get_session)) -> dict:
    return await overview(session)


@router.get("/operations")
async def analytics_operations(session: AsyncSession = Depends(get_session)) -> dict:
    return await operations(session)


@router.get("/receivables")
async def analytics_receivables(session: AsyncSession = Depends(get_session)) -> dict:
    return await receivables(session)
