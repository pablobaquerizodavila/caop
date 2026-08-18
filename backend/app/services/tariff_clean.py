"""Limpieza in situ de descripciones del arancel ya cargadas.

Aplica `clean_description` (quita encabezados de página colados, puntos de índice
y arregla el espaciado tras puntuación) a las subpartidas existentes, sin crear
una nueva versión ni tocar reglas. No resuelve el pegado genuino todo-minúsculas
del PDF de origen (requeriría diccionario/OCR).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tariff import TariffCode
from app.services.tariff_parser import clean_description


async def clean_existing_descriptions(session: AsyncSession) -> dict:
    codes = list(await session.scalars(select(TariffCode)))
    changed = 0
    for c in codes:
        nd = clean_description(c.description) or c.description
        nf = clean_description(c.full_description)
        if nd != c.description or nf != c.full_description:
            c.description = nd
            c.full_description = nf
            changed += 1
    await session.flush()
    return {"scanned": len(codes), "changed": changed}
