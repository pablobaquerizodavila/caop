"""Reglas tributarias base de Ecuador (tributos generales).

IMPORTANTE: estos valores son un punto de partida y deben VERIFICARSE contra la
fuente oficial (SENAE / COMEX / SRI / Arancel Nacional) antes de usarse en
producción. Por eso quedan con last_verified_at = NULL (el motor los marca como
NO verificados). El arancel AD_VALOREM depende de la subpartida y NO se siembra:
debe cargarse por HS code con su fuente.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax import TaxRule

PENDING = "PENDIENTE VERIFICACIÓN OFICIAL (SENAE/COMEX/SRI)"

ECUADOR_DEFAULTS: list[dict] = [
    {
        "tax_type": "FODINFA",
        "calculation_method": "AD_VALOREM_PCT",
        "percentage": Decimal("0.5"),
        "base_formula": "CIF",
        "depends_on": [],
        "legal_source": PENDING,
        "effective_from": date(2020, 1, 1),
        "notes": "FODINFA 0,5% sobre CIF (general).",
    },
    {
        "tax_type": "IVA",
        "calculation_method": "AD_VALOREM_PCT",
        "percentage": Decimal("15"),
        "base_formula": "CIF+AD_VALOREM+FODINFA+ICE+SAFP+SAFEGUARD+ANTIDUMPING+COMPENSATORY",
        "depends_on": ["AD_VALOREM", "FODINFA", "ICE", "SAFP", "SAFEGUARD",
                       "ANTIDUMPING", "COMPENSATORY"],
        "legal_source": PENDING,
        "effective_from": date(2024, 4, 1),
        "notes": "IVA general 15% sobre base compuesta. Verificar tarifa vigente.",
    },
]


async def seed_ecuador_defaults(session: AsyncSession) -> list[str]:
    """Inserta las reglas generales si no existen (idempotente). Devuelve los tax_type creados."""
    created: list[str] = []
    for spec in ECUADOR_DEFAULTS:
        exists = await session.scalar(
            select(TaxRule).where(
                TaxRule.tax_type == spec["tax_type"],
                TaxRule.hs_code.is_(None),
                TaxRule.effective_from == spec["effective_from"],
            )
        )
        if exists:
            continue
        session.add(TaxRule(status="ACTIVE", version=1, **spec))
        created.append(spec["tax_type"])
    await session.flush()
    return created
