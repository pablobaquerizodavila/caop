"""Test del scheduler de SLA (una ejecución con sessionmaker inyectado)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.sla import SLAInstance
from app.services.scheduler import run_sla_evaluation


@pytest.mark.asyncio
async def test_run_sla_evaluation_once(db_sessionmaker):
    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as s:
        s.add(
            SLAInstance(
                entity_type="CUSTOMS_CASE",
                entity_id=uuid.uuid4(),
                milestone="X",
                start_time=now - timedelta(hours=10),
                deadline=now - timedelta(hours=1),
                status="ON_TIME",
            )
        )
        await s.commit()

    result = await run_sla_evaluation(db_sessionmaker)
    assert result["evaluated"] >= 1
    assert result["breached"] >= 1
