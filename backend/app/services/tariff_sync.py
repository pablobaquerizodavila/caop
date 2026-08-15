"""Vigilante de fuentes oficiales (#9): detecta resoluciones nuevas y notifica.

NO escribe producción: solo monitorea la(s) `OfficialSource` con URL, extrae referencias
de resolución (p. ej. 002-2023), las compara con las normas ya registradas
(`legal_instrument`) y, si hay nuevas, registra la corrida en `tariff_sync_log` y envía
una alerta. La carga/aprobación de la norma sigue siendo manual (respeta el pipeline).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tariff import LegalInstrument, OfficialSource, TariffSyncLog
from app.services.notifications import get_notifier

# Referencia de resolución COMEX: NNN-AAAA (p. ej. 002-2023, 007-2026).
_RES_RE = re.compile(r"\b(\d{3}-20\d{2})\b")


async def _default_fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


async def run_sync(session: AsyncSession, *, source_code: str | None = None, fetcher=None) -> dict:
    """Ejecuta el vigilante sobre las fuentes con URL. `fetcher` inyectable para tests."""
    fetch = fetcher or _default_fetch
    now = datetime.now(timezone.utc)
    stmt = select(OfficialSource).where(OfficialSource.active.is_(True))
    if source_code:
        stmt = stmt.where(OfficialSource.code == source_code)
    sources = [s for s in await session.scalars(stmt) if s.base_url]

    if not sources:
        log = TariffSyncLog(source_code=source_code, status="NO_SOURCE", finished_at=now,
                            error="Ninguna fuente activa con URL configurada.")
        session.add(log)
        await session.flush()
        return {"status": "NO_SOURCE", "sources": 0, "new": 0}

    known = set(await session.scalars(select(LegalInstrument.number)))
    total_new = 0
    for src in sources:
        log = TariffSyncLog(source_id=src.id, source_code=src.code)
        session.add(log)
        try:
            text = await fetch(src.base_url)
            refs = sorted(set(_RES_RE.findall(text)))
            new = [r for r in refs if r not in known]
            log.status = "OK"
            log.found = len(refs)
            log.new_count = len(new)
            log.detected = new or None
            total_new += len(new)
            if new:
                await _notify(src, new)
        except Exception as exc:  # noqa: BLE001
            log.status = "FAILED"
            log.error = str(exc)[:500]
        log.finished_at = datetime.now(timezone.utc)
    await session.flush()
    return {"status": "OK", "sources": len(sources), "new": total_new}


async def _notify(src: OfficialSource, new_refs: list[str]) -> None:
    recipients = settings.alerts_recipients_list
    if not recipients:
        return
    notifier = get_notifier()
    subject = f"Arancel: {len(new_refs)} resolución(es) nueva(s) en {src.code}"
    body = (f"El vigilante detectó posibles resoluciones nuevas en {src.name}:\n"
            + ", ".join(new_refs)
            + "\n\nRevísalas y cárgalas/apruébalas desde el panel del arancel.")
    for to in recipients:
        try:
            await notifier.send("EMAIL", to, subject, body)
        except Exception:  # noqa: BLE001
            pass


async def recent_logs(session: AsyncSession, limit: int = 20) -> list[TariffSyncLog]:
    return list(await session.scalars(
        select(TariffSyncLog).order_by(TariffSyncLog.created_at.desc()).limit(limit)
    ))
