"""Requisitos documentales base (Ecuador, importación a consumo).

Punto de partida configurable; verificar contra normativa vigente. Los documentos
de control previo (VUE) dependen de la mercancía y se agregarán por regla específica.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist import Requirement

DEFAULTS: list[dict] = [
    {"doc_type": "COMMERCIAL_INVOICE", "category": "SUPPORT", "blocking": True, "applies_when": {}},
    {"doc_type": "PACKING_LIST", "category": "SUPPORT", "blocking": True, "applies_when": {}},
    {"doc_type": "BILL_OF_LADING", "category": "SUPPORT", "blocking": True,
     "applies_when": {"transport_mode": "OCEAN"}},
    {"doc_type": "AIR_WAYBILL", "category": "SUPPORT", "blocking": True,
     "applies_when": {"transport_mode": "AIR"}},
    {"doc_type": "INSURANCE_POLICY", "category": "SUPPORT", "blocking": False, "applies_when": {}},
    {"doc_type": "CERTIFICATE_OF_ORIGIN", "category": "ACCOMPANY", "blocking": False,
     "applies_when": {"requires_agreement": True}},
]


async def seed_requirement_defaults(session: AsyncSession) -> list[str]:
    created: list[str] = []
    for spec in DEFAULTS:
        exists = await session.scalar(
            select(Requirement).where(Requirement.doc_type == spec["doc_type"])
        )
        if exists:
            continue
        session.add(Requirement(status="ACTIVE", **spec))
        created.append(spec["doc_type"])
    await session.flush()
    return created
