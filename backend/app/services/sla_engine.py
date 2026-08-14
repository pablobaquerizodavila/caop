"""Motor de SLA: cálculo de vencimiento (tiempo hábil), estado y escalamiento.

Umbrales de escalamiento (spec §24):
  70%  -> responsable            (AT_RISK, nivel 1)
  85%  -> + supervisor           (CRITICAL, nivel 2)
  100% -> + gerente              (BREACHED, nivel 3)
  120% -> gerencia               (nivel 4)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sla import SLAInstance
from app.models.sla_config import BusinessCalendar, SLAPolicy
from app.services.business_time import add_business_minutes, business_minutes_between


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normaliza a UTC-aware (SQLite devuelve naive; Postgres devuelve aware)."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _calendar(session: AsyncSession, name: str) -> BusinessCalendar | None:
    return await session.scalar(select(BusinessCalendar).where(BusinessCalendar.name == name))


async def create_case_sla(session: AsyncSession, case_id, milestone: str) -> SLAInstance:
    """Crea el SLA de un hito calculando el vencimiento en tiempo hábil."""
    policy = await session.scalar(select(SLAPolicy).where(SLAPolicy.milestone == milestone))
    start = _now()
    if policy is None:
        deadline = start + timedelta(hours=24)  # fallback tiempo calendario
        severity = "NORMAL"
    else:
        cal = await _calendar(session, policy.calendar_name)
        if cal is None:
            deadline = start + timedelta(hours=24)
        else:
            deadline = add_business_minutes(
                start, policy.business_minutes, cal.timezone, cal.working_hours,
                set(cal.holidays or []),
            )
        severity = policy.severity
    sla = SLAInstance(
        entity_type="CUSTOMS_CASE", entity_id=case_id, milestone=milestone,
        start_time=start, deadline=deadline, severity=severity, status="ON_TIME",
    )
    session.add(sla)
    return sla


def _status_for(pct: float) -> tuple[str, int]:
    if pct >= 120:
        return "BREACHED", 4
    if pct >= 100:
        return "BREACHED", 3
    if pct >= 85:
        return "CRITICAL", 2
    if pct >= 70:
        return "AT_RISK", 1
    return "ON_TIME", 0


async def _pct(session: AsyncSession, sla: SLAInstance, now: datetime) -> float:
    """Porcentaje consumido del SLA en tiempo hábil (0..∞)."""
    start = _as_utc(sla.start_time)
    deadline = _as_utc(sla.deadline)
    if not deadline:
        return 0.0
    # Buscar el calendario del hito para medir en horas hábiles.
    policy = await session.scalar(select(SLAPolicy).where(SLAPolicy.milestone == sla.milestone))
    cal = await _calendar(session, policy.calendar_name) if policy else None
    if cal is None:
        total = (deadline - start).total_seconds() / 60
        elapsed = (now - start).total_seconds() / 60
    else:
        wh, hol, tz = cal.working_hours, set(cal.holidays or []), cal.timezone
        total = business_minutes_between(start, deadline, tz, wh, hol)
        elapsed = business_minutes_between(start, now, tz, wh, hol)
    return (elapsed / total * 100) if total > 0 else 0.0


async def evaluate_all(session: AsyncSession) -> dict:
    """Recalcula estado/escalamiento de los SLA abiertos. Idempotente; llamable por cron."""
    now = _now()
    open_slas = list(
        await session.scalars(select(SLAInstance).where(SLAInstance.status != "MET"))
    )
    escalated = 0
    breached = 0
    for sla in open_slas:
        pct = await _pct(session, sla, now)
        status, level = _status_for(pct)
        if level > sla.escalation_level:
            escalated += 1
        sla.status = status
        sla.escalation_level = level
        if status == "BREACHED":
            breached += 1
            if not sla.breach_reason:
                sla.breach_reason = "Vencido sin cumplir el hito"
    await session.flush()
    return {"evaluated": len(open_slas), "escalated": escalated, "breached": breached}


async def mark_met(session: AsyncSession, case_id, milestone: str) -> None:
    """Marca como cumplido el SLA de un hito (p. ej. al llegar readiness 100)."""
    sla = await session.scalar(
        select(SLAInstance).where(
            SLAInstance.entity_type == "CUSTOMS_CASE",
            SLAInstance.entity_id == case_id,
            SLAInstance.milestone == milestone,
            SLAInstance.status != "MET",
        )
    )
    if sla is not None:
        sla.status = "MET"
