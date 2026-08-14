"""Calendario laboral y políticas de SLA base (configurables/verificables)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sla_config import BusinessCalendar, SLAPolicy
from app.services.business_time import DEFAULT_WORKING_HOURS

# Feriados de ejemplo (fijos). Ajustar/completar según calendario oficial vigente.
SAMPLE_HOLIDAYS = ["2026-01-01", "2026-05-01", "2026-12-25"]

POLICIES = [
    {"milestone": "DOCUMENTS_COMPLETE", "business_minutes": 480, "calendar_name": "INTERNO",
     "severity": "NORMAL"},
]


async def seed_sla_config(session: AsyncSession) -> dict:
    created_cal: list[str] = []
    created_pol: list[str] = []

    cal = await session.scalar(select(BusinessCalendar).where(BusinessCalendar.name == "INTERNO"))
    if cal is None:
        session.add(
            BusinessCalendar(
                name="INTERNO",
                timezone="America/Guayaquil",
                working_hours=DEFAULT_WORKING_HOURS,
                holidays=SAMPLE_HOLIDAYS,
            )
        )
        created_cal.append("INTERNO")

    for spec in POLICIES:
        exists = await session.scalar(
            select(SLAPolicy).where(SLAPolicy.milestone == spec["milestone"])
        )
        if exists:
            continue
        session.add(SLAPolicy(**spec))
        created_pol.append(spec["milestone"])

    await session.flush()
    return {"calendars": created_cal, "policies": created_pol}
