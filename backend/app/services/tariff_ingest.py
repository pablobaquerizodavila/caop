"""Pipeline de ingesta arancelaria: PARSE → VALIDATE → STAGE → PUBLISH.

Nunca escribe producción directamente: la carga crea una `TariffVersion` en estado
STAGED con sus `TariffCode` y sus reglas AD_VALOREM (`TaxRule`) también en STAGED.
`publish_version` supersede la versión anterior y activa la nueva (reversible).

La inserción usa Core bulk (evita eventos ORM por fila): la trazabilidad de la carga
queda en `TariffImport` + `TariffVersion`, no en miles de filas de auditoría.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tariff import (
    OfficialSource,
    TariffChange,
    TariffCode,
    TariffImport,
    TariffVersion,
)
from app.models.tax import TaxRule
from app.services.notifications import get_notifier
from app.services.tariff_parser import ArancelPdfAdapter, TariffRecord

VERIFIED_BY = "Arancel del Ecuador (COMEX) · ArancelPdfAdapter"


@dataclass
class ImportResult:
    import_id: uuid.UUID
    version_id: uuid.UUID
    version_number: str
    status: str
    codes: int
    rules: int
    errors: list[str]
    changes: dict = field(default_factory=dict)  # resumen del diff vs versión activa (#10)


async def _get_or_create_source(session: AsyncSession, code: str, kind: str, name: str) -> OfficialSource:
    src = await session.scalar(select(OfficialSource).where(OfficialSource.code == code))
    if src is None:
        src = OfficialSource(code=code, kind=kind, name=name, adapter="ArancelPdfAdapter")
        session.add(src)
        await session.flush()
    return src


def validate_records(records: list[TariffRecord]) -> list[str]:
    """Validaciones de calidad previas a publicar (no exhaustivas: bloquean lo grave)."""
    errors: list[str] = []
    seen: set[str] = set()
    dups = 0
    for r in records:
        if not r.code_normalized.isdigit():
            errors.append(f"código no numérico: {r.code}")
        if r.level not in (2, 4, 6, 8, 10):
            errors.append(f"nivel inválido ({r.level}) en {r.code}")
        if r.ad_valorem is not None and (r.ad_valorem < 0 or r.ad_valorem > 200):
            errors.append(f"ad_valorem fuera de rango ({r.ad_valorem}) en {r.code}")
        if r.code_normalized in seen:
            dups += 1
        seen.add(r.code_normalized)
    if dups:
        errors.append(f"{dups} códigos duplicados")
    national = [r for r in records if r.level == 10]
    if len(national) < 100:
        errors.append(f"muy pocas subpartidas nacionales ({len(national)}): posible parseo fallido")
    return errors[:50]  # cota para no explotar


async def import_arancel(
    session: AsyncSession,
    *,
    version_number: str,
    effective_from: date,
    path: str | None = None,
    records: list[TariffRecord] | None = None,
    filename: str | None = None,
    file_hash: str | None = None,
    source_code: str = "COMEX",
) -> ImportResult:
    """Ingesta el arancel a una versión STAGED (no activa hasta publish_version)."""
    now = datetime.now(timezone.utc)
    src = await _get_or_create_source(session, source_code, "COMEX", "Comité de Comercio Exterior")

    imp = TariffImport(
        source_id=src.id, filename=filename, file_hash=file_hash,
        parser="ArancelPdfAdapter", status="PARSED", started_at=now,
    )
    session.add(imp)
    await session.flush()

    recs = records if records is not None else ArancelPdfAdapter().parse(path)  # type: ignore[arg-type]
    errors = validate_records(recs)

    national_with_rate = [r for r in recs if r.level == 10 and r.ad_valorem is not None]
    version = TariffVersion(
        number=version_number, source_id=src.id, status="STAGED",
        codes_count=len(recs), rules_count=len(national_with_rate), source_hash=file_hash,
    )
    session.add(version)
    await session.flush()

    # --- Bulk insert de códigos (Core: evita eventos ORM por fila) ---
    code_id_by_norm: dict[str, uuid.UUID] = {}
    code_rows = []
    for r in recs:
        cid = uuid.uuid4()
        code_id_by_norm[r.code_normalized] = cid
        code_rows.append({
            "id": cid, "code": r.code, "code_normalized": r.code_normalized,
            "level": r.level, "description": r.description or (r.full_description or r.code),
            "full_description": r.full_description, "parent_code": r.parent_code,
            "physical_unit": r.physical_unit, "effective_from": effective_from,
            "status": "STAGED", "source_id": src.id, "tariff_version_id": version.id,
            "ad_valorem": r.ad_valorem, "last_verified_at": now,
        })
    if code_rows:
        await session.execute(insert(TariffCode), code_rows)

    # --- Bulk insert de reglas AD_VALOREM (una por subpartida nacional con tarifa) ---
    rule_rows = []
    for r in national_with_rate:
        rule_rows.append({
            "id": uuid.uuid4(), "tax_type": "AD_VALOREM", "hs_code": r.code,
            "calculation_method": "AD_VALOREM_PCT", "percentage": r.ad_valorem,
            "base_formula": "CIF", "depends_on": [], "status": "STAGED", "version": 1,
            "effective_from": effective_from,
            "legal_source": f"Arancel del Ecuador · versión {version_number}",
            "verification_status": "VERIFIED", "verified_at": now, "verified_by": VERIFIED_BY,
            "last_verified_at": now, "official_source_id": src.id,
            "tariff_version_id": version.id, "tariff_code_id": code_id_by_norm.get(r.code_normalized),
        })
    if rule_rows:
        await session.execute(insert(TaxRule), rule_rows)

    imp.tariff_version_id = version.id
    imp.status = "STAGED" if not errors else "VALIDATED"
    imp.records_total = len(recs)
    imp.records_valid = len(national_with_rate)
    imp.errors = errors or None
    imp.finished_at = datetime.now(timezone.utc)
    await session.flush()

    # #10: diff tipado vs. la versión activa (para revisar antes de publicar).
    changes = await compute_diff(session, version.id)

    return ImportResult(
        import_id=imp.id, version_id=version.id, version_number=version_number,
        status=version.status, codes=len(recs), rules=len(rule_rows), errors=errors, changes=changes,
    )


def _dot(norm: str) -> str:
    """Reconstruye el código con puntos desde el normalizado (10 díg. → dddd.dd.dd.dd)."""
    if len(norm) == 10:
        return f"{norm[:4]}.{norm[4:6]}.{norm[6:8]}.{norm[8:10]}"
    return norm


async def compute_diff(session: AsyncSession, new_version_id: uuid.UUID) -> dict:
    """Compara la versión (staged) contra la ACTIVA y registra cambios tipados (#10)."""
    active = await active_version(session)
    if active is None or active.id == new_version_id:
        return {}

    def _map(rows):
        return {r.code_normalized: (r.code, r.ad_valorem, r.description or "") for r in rows}

    new_map = _map(await session.scalars(
        select(TariffCode).where(TariffCode.tariff_version_id == new_version_id, TariffCode.level == 10)
    ))
    old_map = _map(await session.scalars(
        select(TariffCode).where(TariffCode.tariff_version_id == active.id, TariffCode.level == 10)
    ))

    rows = []
    counts = {"NEW_CODE": 0, "REMOVED_CODE": 0, "RATE_CHANGED": 0, "DESCRIPTION_CHANGED": 0}
    for norm, (code, av, desc) in new_map.items():
        if norm not in old_map:
            counts["NEW_CODE"] += 1
            rows.append(("NEW_CODE", code, norm, None, str(av)))
        else:
            _, oav, odesc = old_map[norm]
            if (av if av is None else str(av)) != (oav if oav is None else str(oav)):
                counts["RATE_CHANGED"] += 1
                rows.append(("RATE_CHANGED", code, norm, str(oav), str(av)))
            elif desc != odesc:
                counts["DESCRIPTION_CHANGED"] += 1
                rows.append(("DESCRIPTION_CHANGED", code, norm, odesc[:250], desc[:250]))
    for norm, (code, oav, _odesc) in old_map.items():
        if norm not in new_map:
            counts["REMOVED_CODE"] += 1
            rows.append(("REMOVED_CODE", _dot(norm), norm, str(oav), None))

    if rows:
        await session.execute(insert(TariffChange), [
            {"id": uuid.uuid4(), "tariff_version_id": new_version_id, "change_type": t,
             "hs_code": code, "code_normalized": norm, "old_value": o, "new_value": n}
            for (t, code, norm, o, n) in rows
        ])
    total = sum(counts.values())
    counts["total"] = total
    if total:
        await _notify_changes(new_version_id, counts)
    return counts


async def _notify_changes(version_id: uuid.UUID, counts: dict) -> None:
    recipients = settings.alerts_recipients_list
    if not recipients:
        return
    notifier = get_notifier()
    subject = f"Arancel: {counts['total']} cambio(s) en una versión nueva (revisar)"
    body = (f"Se ingirió una versión arancelaria nueva con cambios vs. la activa:\n"
            f"- Subpartidas nuevas: {counts.get('NEW_CODE', 0)}\n"
            f"- Eliminadas: {counts.get('REMOVED_CODE', 0)}\n"
            f"- Cambios de tarifa: {counts.get('RATE_CHANGED', 0)}\n"
            f"- Cambios de descripción: {counts.get('DESCRIPTION_CHANGED', 0)}\n\n"
            "Revísala y publícala desde el panel del arancel.")
    for to in recipients:
        try:
            await notifier.send("EMAIL", to, subject, body)
        except Exception:  # noqa: BLE001
            pass


async def import_arancel_from_url(
    session: AsyncSession, *, url: str, version_number: str, effective_from: date,
    source_code: str = "COMEX",
) -> ImportResult:
    """#8: descarga automática del arancel (PDF) desde una URL y lo ingiere a versión STAGED."""
    import hashlib
    import tempfile

    import httpx

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        resp = await c.get(url)
        resp.raise_for_status()
        data = resp.content
    file_hash = hashlib.sha256(data).hexdigest()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    return await import_arancel(
        session, version_number=version_number, effective_from=effective_from,
        path=tmp_path, filename=url.rsplit("/", 1)[-1], file_hash=file_hash, source_code=source_code,
    )


async def changes_for_version(session: AsyncSession, version_id: uuid.UUID, limit: int = 500):
    return list(await session.scalars(
        select(TariffChange).where(TariffChange.tariff_version_id == version_id)
        .order_by(TariffChange.change_type).limit(limit)
    ))


async def publish_version(session: AsyncSession, version_id: uuid.UUID) -> dict:
    """Activa una versión STAGED y supersede la anterior (reversible)."""
    version = await session.get(TariffVersion, version_id)
    if version is None:
        raise ValueError("Versión no encontrada")
    now = datetime.now(timezone.utc)

    # Supersede reglas/códigos AD_VALOREM de OTRAS versiones actualmente activas.
    await session.execute(
        update(TaxRule)
        .where(
            TaxRule.tax_type == "AD_VALOREM",
            TaxRule.status == "ACTIVE",
            TaxRule.tariff_version_id.is_not(None),
            TaxRule.tariff_version_id != version_id,
        )
        .values(status="SUPERSEDED", verification_status="SUPERSEDED")
    )
    await session.execute(
        update(TariffCode)
        .where(
            TariffCode.status == "ACTIVE",
            TariffCode.tariff_version_id.is_not(None),
            TariffCode.tariff_version_id != version_id,
        )
        .values(status="SUPERSEDED")
    )
    await session.execute(
        update(TariffVersion)
        .where(TariffVersion.status == "ACTIVE", TariffVersion.id != version_id)
        .values(status="SUPERSEDED")
    )

    # Activa la versión nueva.
    await session.execute(
        update(TaxRule).where(TaxRule.tariff_version_id == version_id).values(status="ACTIVE")
    )
    await session.execute(
        update(TariffCode).where(TariffCode.tariff_version_id == version_id).values(status="ACTIVE")
    )
    version.status = "ACTIVE"
    version.published_at = now
    await session.flush()

    codes = await session.scalar(
        select(func.count()).select_from(TariffCode).where(TariffCode.tariff_version_id == version_id)
    )
    rules = await session.scalar(
        select(func.count()).select_from(TaxRule).where(TaxRule.tariff_version_id == version_id)
    )
    return {"version": version.number, "status": "ACTIVE", "codes": codes, "rules": rules}


async def active_version(session: AsyncSession) -> TariffVersion | None:
    return await session.scalar(
        select(TariffVersion).where(TariffVersion.status == "ACTIVE").order_by(
            TariffVersion.published_at.desc()
        )
    )
