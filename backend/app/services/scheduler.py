"""Scheduler interno (asyncio) para tareas periódicas — sin infraestructura extra.

Por ahora dispara la evaluación de SLA cada N minutos. Corre dentro del proceso
del backend (un solo worker en dev/prod). Si en el futuro se escala a múltiples
workers, mover esto a Temporal o a un cron externo con lock distribuido.
"""

from __future__ import annotations

import asyncio
import logging

from app.db.session import get_sessionmaker
from app.services.alerts import send_digest
from app.services.sla_engine import evaluate_all

logger = logging.getLogger("caop.scheduler")


async def run_sla_evaluation(sessionmaker=None) -> dict:
    """Ejecuta una evaluación de SLA. `sessionmaker` inyectable para tests."""
    maker = sessionmaker or get_sessionmaker()
    async with maker() as session:
        result = await evaluate_all(session)
        await session.commit()
        return result


async def sla_scheduler_loop(interval_minutes: int) -> None:
    logger.info("SLA scheduler activo: cada %s min", interval_minutes)
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            result = await run_sla_evaluation()
            if result.get("escalated") or result.get("breached"):
                logger.info("SLA evaluate: %s", result)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo en la evaluación periódica de SLA")


async def run_alert_digest(sessionmaker=None) -> dict:
    """Envía el digest de excepciones (solo si hay). `sessionmaker` inyectable para tests."""
    maker = sessionmaker or get_sessionmaker()
    async with maker() as session:
        result = await send_digest(session, skip_if_empty=True)
        await session.commit()
        return result


async def alert_digest_loop(interval_minutes: int) -> None:
    logger.info("Digest de alertas activo: cada %s min", interval_minutes)
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            result = await run_alert_digest()
            if not result.get("skipped"):
                logger.info("Digest de alertas enviado: %s", result)
        except Exception:  # noqa: BLE001
            logger.exception("Fallo en el envío del digest de alertas")
