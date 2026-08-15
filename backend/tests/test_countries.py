"""Test del catálogo ISO 3166-1 (249) con continente."""

import pytest
from sqlalchemy import func, select

from app.models.trade import Country
from app.services.country_seed import COUNTRIES, seed_countries


def test_catalog_has_249_unique_iso2():
    codes = [c[0] for c in COUNTRIES]
    assert len(codes) == 249
    assert len(set(codes)) == 249  # sin duplicados
    conts = {c[3] for c in COUNTRIES}
    assert conts == {"América", "Europa", "África", "Asia", "Oceanía", "Antártida"}


@pytest.mark.asyncio
async def test_seed_countries_upsert(db_sessionmaker):
    async with db_sessionmaker() as s:
        res = await seed_countries(s)
        assert res["total"] == 249
        total = await s.scalar(select(func.count()).select_from(Country))
        assert total >= 249
        cn = await s.scalar(select(Country).where(Country.iso2 == "CN"))
        assert cn is not None and cn.continent == "Asia"
        # Idempotente: correr de nuevo no crea duplicados.
        res2 = await seed_countries(s)
        assert res2["created"] == 0
