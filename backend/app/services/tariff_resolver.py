"""Resolvedor arancelario: orquesta el maestro + reglas y alimenta al tax_engine.

Aquí vive la regla NO NEGOCIABLE «faltante ≠ 0%»: se distingue explícitamente entre
una tarifa 0% OFICIAL (existe una regla con 0) y la AUSENCIA de dato (no hay regla /
subpartida no está en el maestro), que produce TARIFF_DATA_NOT_FOUND y marca la
estimación como incompleta. Nunca se asume 0% por falta de información.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tariff import TariffCode
from app.models.tax import TaxRule
from app.services.tariff_ingest import active_version
from app.services.tax_engine import TaxComponent, TaxItemInput, TaxItemResult, compute_item

# Tributos que SIEMPRE deben poder determinarse en una importación general.
EXPECTED_MANDATORY = ("AD_VALOREM", "FODINFA", "IVA")


@dataclass
class ResolvedItem:
    result: TaxItemResult
    tariff_code_id: uuid.UUID | None
    hs_validation: str  # VALID / NOT_FOUND / UNKNOWN


def _normalize(hs_code: str | None) -> str:
    return (hs_code or "").replace(".", "").replace(" ", "").strip()


async def _active_rules(session: AsyncSession) -> list[TaxRule]:
    return list(await session.scalars(select(TaxRule).where(TaxRule.status == "ACTIVE")))


async def _lookup_code(session: AsyncSession, hs_code: str | None) -> TariffCode | None:
    norm = _normalize(hs_code)
    if not norm:
        return None
    return await session.scalar(
        select(TariffCode).where(
            TariffCode.code_normalized == norm, TariffCode.status == "ACTIVE"
        )
    )


def _finalize(
    result: TaxItemResult,
    item: TaxItemInput,
    tc: TariffCode | None,
    version_number: str | None,
    injected_types: set[str] | None = None,
) -> str:
    """Aplica 'faltante ≠ 0%' y devuelve el hs_validation."""
    result.data_version = version_number
    present = {c.tax_type for c in result.components} | (injected_types or set())

    hs_validation = "UNKNOWN"
    if item.hs_code:
        hs_validation = "VALID" if tc is not None else "NOT_FOUND"
        if tc is None:
            result.complete = False
            result.warnings.append(
                f"TARIFF_DATA_NOT_FOUND: la subpartida {item.hs_code} no está en el "
                "maestro arancelario vigente"
            )
    else:
        result.complete = False
        result.warnings.append(
            "SIN_SUBPARTIDA: no se indicó subpartida; no se puede determinar el arancel"
        )

    for t in EXPECTED_MANDATORY:
        if t not in present:
            result.missing_information.append(t)
            result.complete = False
            if t == "AD_VALOREM" and tc is not None:
                result.warnings.append(
                    f"TARIFF_DATA_NOT_FOUND: no hay arancel Ad-Valorem vigente para "
                    f"{item.hs_code} en la versión arancelaria activa"
                )

    unverified = sorted({c.tax_type for c in result.components if not c.verified})
    if unverified:
        result.warnings.append(
            "TARIFA_NO_VERIFICADA: pendiente de verificación oficial: " + ", ".join(unverified)
        )
    return hs_validation


async def resolve_item(
    session: AsyncSession,
    item: TaxItemInput,
    on: date,
    *,
    rules: list[TaxRule] | None = None,
    version_number: str | None = None,
    injected: list[TaxComponent] | None = None,
) -> ResolvedItem:
    if rules is None:
        rules = await _active_rules(session)
    if version_number is None:
        ver = await active_version(session)
        version_number = ver.number if ver else None
    tc = await _lookup_code(session, item.hs_code)
    result = compute_item(rules, item, on, injected=injected)
    injected_types = {c.tax_type for c in (injected or [])}
    hs_validation = _finalize(result, item, tc, version_number, injected_types)
    return ResolvedItem(result=result, tariff_code_id=(tc.id if tc else None), hs_validation=hs_validation)


async def resolve_items(
    session: AsyncSession, items: list[TaxItemInput], on: date
) -> list[ResolvedItem]:
    """Resuelve varios ítems cargando reglas y versión una sola vez (para cotizaciones)."""
    rules = await _active_rules(session)
    ver = await active_version(session)
    vn = ver.number if ver else None
    out: list[ResolvedItem] = []
    for it in items:
        out.append(await resolve_item(session, it, on, rules=rules, version_number=vn))
    return out
