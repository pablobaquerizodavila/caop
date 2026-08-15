"""Importación masiva por CSV de datos arancelarios (preferencias, ICE, defensa, restricciones).

Permite cargar los datos oficiales por archivo en vez de uno por uno. NO inventa valores:
solo persiste lo que trae el CSV. Cada tipo tiene sus columnas (ver PLANTILLAS).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import (
    ControlAuthority,
    ControlDocument,
    IceMeasure,
    TariffPreference,
    TariffRestriction,
    TradeAgreement,
    TradeRemedy,
)

PLANTILLAS = {
    "preferences": "agreement_code,origin_country,hs_prefix,liberation_pct,preferential_rate,requires_certificate,effective_from",
    "ice": "hs_prefix,description,method,ad_valorem_pct,specific_rate,specific_unit,base_type,effective_from",
    "remedies": "kind,hs_prefix,origin_country,product,method,ad_valorem_pct,specific_rate,effective_from,effective_to",
    "restrictions": "hs_prefix,kind,authority_code,document_code,requirement,effective_from",
}


def _dec(row: dict, key: str) -> Decimal | None:
    v = (row.get(key) or "").strip().replace(",", ".")
    if not v:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def _date(row: dict, key: str) -> date | None:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    return date.fromisoformat(v)


def _norm(v: str | None) -> str | None:
    return v.replace(".", "").strip() if v else None


def _bool(row: dict, key: str, default: bool = True) -> bool:
    v = (row.get(key) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "si", "sí", "yes", "x")


async def bulk_import(session: AsyncSession, kind: str, csv_text: str) -> dict:
    if kind not in PLANTILLAS:
        raise ValueError(f"Tipo no soportado: {kind}. Opciones: {', '.join(PLANTILLAS)}")
    reader = csv.DictReader(io.StringIO(csv_text))
    created = 0
    errors: list[str] = []

    if kind == "preferences":
        agreements = {a.code: a.id for a in await session.scalars(select(TradeAgreement))}
        for i, row in enumerate(reader, start=2):
            ag = agreements.get((row.get("agreement_code") or "").strip().upper())
            eff = _date(row, "effective_from")
            if ag is None or eff is None:
                errors.append(f"fila {i}: acuerdo o fecha inválida")
                continue
            session.add(TariffPreference(
                agreement_id=ag, origin_country=(row.get("origin_country") or "").strip().upper() or None,
                hs_prefix=_norm(row.get("hs_prefix")), liberation_pct=_dec(row, "liberation_pct") or Decimal(100),
                preferential_rate=_dec(row, "preferential_rate"),
                requires_certificate=_bool(row, "requires_certificate"), effective_from=eff,
                legal_source="Carga masiva CSV",
            ))
            created += 1

    elif kind == "ice":
        for i, row in enumerate(reader, start=2):
            eff = _date(row, "effective_from")
            hp = _norm(row.get("hs_prefix"))
            if not hp or eff is None:
                errors.append(f"fila {i}: hs_prefix o fecha inválida")
                continue
            session.add(IceMeasure(
                hs_prefix=hp, description=(row.get("description") or None),
                method=(row.get("method") or "AD_VALOREM").strip().upper(),
                ad_valorem_pct=_dec(row, "ad_valorem_pct"), specific_rate=_dec(row, "specific_rate"),
                specific_unit=(row.get("specific_unit") or None),
                base_type=(row.get("base_type") or "EX_ADUANA").strip().upper(), effective_from=eff,
            ))
            created += 1

    elif kind == "remedies":
        for i, row in enumerate(reader, start=2):
            eff = _date(row, "effective_from")
            hp = _norm(row.get("hs_prefix"))
            if not hp or eff is None or not (row.get("kind") or "").strip():
                errors.append(f"fila {i}: kind/hs_prefix/fecha inválida")
                continue
            session.add(TradeRemedy(
                kind=(row.get("kind") or "").strip().upper(), hs_prefix=hp,
                origin_country=(row.get("origin_country") or "").strip().upper() or None,
                product=(row.get("product") or None),
                method=(row.get("method") or "AD_VALOREM").strip().upper(),
                ad_valorem_pct=_dec(row, "ad_valorem_pct"), specific_rate=_dec(row, "specific_rate"),
                effective_from=eff, effective_to=_date(row, "effective_to"),
            ))
            created += 1

    elif kind == "restrictions":
        auths = {a.code: a.id for a in await session.scalars(select(ControlAuthority))}
        docs = {d.code: d.id for d in await session.scalars(select(ControlDocument))}
        for i, row in enumerate(reader, start=2):
            eff = _date(row, "effective_from")
            hp = _norm(row.get("hs_prefix"))
            if not hp or eff is None:
                errors.append(f"fila {i}: hs_prefix o fecha inválida")
                continue
            session.add(TariffRestriction(
                hs_prefix=hp, kind=(row.get("kind") or "CONTROL_PREVIO").strip().upper(),
                authority_id=auths.get((row.get("authority_code") or "").strip().upper()),
                control_document_id=docs.get((row.get("document_code") or "").strip().upper()),
                requirement=(row.get("requirement") or None), effective_from=eff,
            ))
            created += 1

    await session.flush()
    return {"kind": kind, "created": created, "errors": errors[:50]}
