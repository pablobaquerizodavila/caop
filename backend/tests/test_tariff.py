"""Tests del módulo arancelario (Fase 1): parser, ingesta, resolver (faltante ≠ 0%), API."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.tax import TaxRule
from app.services.tariff_ingest import import_arancel, publish_version
from app.services.tariff_parser import TariffRecord, _split_columns
from app.services.tariff_resolver import resolve_item
from app.services.tax_engine import TaxItemInput


def _rec(code, desc, uf, av, level=10):
    return TariffRecord(
        code=code, code_normalized=code.replace(".", ""), level=level,
        description=desc, physical_unit=uf,
        ad_valorem=(Decimal(str(av)) if av is not None else None),
    )


RECS = [
    _rec("8517.13.00.00", "Teléfonos celulares", "u", 0),      # 0% OFICIAL
    _rec("8471.30.00.00", "Portátiles", "u", 5),               # 5%
    _rec("9999.99.99.99", "En maestro sin arancel", None, None),  # en maestro, sin regla
]


async def _seed_general(session):
    now = datetime.now(timezone.utc)
    session.add(TaxRule(
        tax_type="FODINFA", calculation_method="AD_VALOREM_PCT", percentage=Decimal("0.5"),
        base_formula="CIF", depends_on=[], effective_from=date(2020, 1, 1), status="ACTIVE",
        version=1, verification_status="VERIFIED", verified_at=now, last_verified_at=now,
    ))
    session.add(TaxRule(
        tax_type="IVA", calculation_method="AD_VALOREM_PCT", percentage=Decimal("15"),
        base_formula="CIF+AD_VALOREM+FODINFA", depends_on=["AD_VALOREM", "FODINFA"],
        effective_from=date(2020, 1, 1), status="ACTIVE", version=1,
        verification_status="VERIFIED", verified_at=now, last_verified_at=now,
    ))
    await session.flush()


async def _ingest(session, eff=date(2023, 9, 1), version="TEST-1"):
    await _seed_general(session)
    res = await import_arancel(session, records=RECS, version_number=version, effective_from=eff)
    await publish_version(session, res.version_id)
    await session.commit()
    return res


# ---------- parser ----------
def test_split_columns_relative():
    toks = [(51, "8517.13.00.00"), (104, "-"), (112, "Teléfonos"), (345, "u"), (382, "0")]
    code, desc, uf, tar, obs = _split_columns(toks)
    assert code == "8517.13.00.00"
    assert "Teléfonos" in desc
    assert uf == "u"
    assert tar == "0"


def test_split_columns_shifted():
    # columnas desplazadas ~15pt (otra página): UF a 327, tarifa a 363
    toks = [(57, "1008.60.00.00"), (104, "-"), (108, "Triticale"), (327, "Kg"), (363, "20")]
    code, desc, uf, tar, obs = _split_columns(toks)
    assert code == "1008.60.00.00"
    assert uf == "Kg"
    assert tar == "20"


# ---------- ingesta + resolver ----------
@pytest.mark.asyncio
async def test_ingest_publishes_and_creates_rules(db_sessionmaker):
    async with db_sessionmaker() as s:
        res = await _ingest(s)
        assert res.codes == 3
        assert res.rules == 2  # solo 8517 (0%) y 8471 (5%) tienen tarifa; 9999 no
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(100), hs_code="8471.30.00.00"), date(2024, 1, 1)
        )
        assert ri.hs_validation == "VALID"
        assert ri.result.complete is True
        types = {c.tax_type for c in ri.result.components}
        assert {"AD_VALOREM", "FODINFA", "IVA"} <= types
        assert ri.result.data_version == "TEST-1"


@pytest.mark.asyncio
async def test_zero_percent_is_official_not_missing(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(100), hs_code="8517.13.00.00"), date(2024, 1, 1)
        )
        adval = [c for c in ri.result.components if c.tax_type == "AD_VALOREM"]
        assert adval and adval[0].amount == Decimal("0.00")  # 0% presente = OFICIAL
        assert ri.result.complete is True
        assert "AD_VALOREM" not in ri.result.missing_information


@pytest.mark.asyncio
async def test_missing_is_not_zero(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    async with db_sessionmaker() as s:
        # subpartida que NO está en el maestro
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(100), hs_code="0101.21.00.00"), date(2024, 1, 1)
        )
        assert ri.hs_validation == "NOT_FOUND"
        assert ri.result.complete is False
        assert any("TARIFF_DATA_NOT_FOUND" in w for w in ri.result.warnings)
        assert "AD_VALOREM" in ri.result.missing_information


@pytest.mark.asyncio
async def test_in_master_without_rule_flags_missing(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(100), hs_code="9999.99.99.99"), date(2024, 1, 1)
        )
        assert ri.hs_validation == "VALID"          # está en el maestro
        assert ri.result.complete is False           # pero sin arancel vigente
        assert "AD_VALOREM" in ri.result.missing_information


@pytest.mark.asyncio
async def test_historical_date_before_version(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s, eff=date(2023, 9, 1))
    async with db_sessionmaker() as s:
        # antes de la vigencia del arancel: la regla AD_VALOREM no aplica
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(100), hs_code="8471.30.00.00"), date(2023, 1, 1)
        )
        assert ri.result.complete is False
        assert "AD_VALOREM" in ri.result.missing_information


# ---------- API ----------
@pytest.mark.asyncio
async def test_api_search_and_calculate(client, db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)

    # autocompletar por texto
    r = await client.get("/api/v1/tariff/codes", params={"q": "Portátiles"})
    assert r.status_code == 200
    assert any(c["code"] == "8471.30.00.00" for c in r.json())

    # autocompletar por prefijo
    r = await client.get("/api/v1/tariff/codes", params={"q": "8517"})
    assert any(c["code"] == "8517.13.00.00" for c in r.json())

    # detalle
    r = await client.get("/api/v1/tariff/codes/8471.30.00.00")
    assert r.status_code == 200
    body = r.json()
    assert any(t["tax_type"] == "AD_VALOREM" and float(t["percentage"]) == 5 for t in body["taxes"])

    # cálculo
    r = await client.post("/api/v1/tariff/calculate", json={
        "items": [{"hs_code": "8471.30.00.00", "invoice_value": 1000, "freight": 100, "insurance": 10}]
    })
    assert r.status_code == 200
    out = r.json()
    assert out["complete"] is True
    assert out["total_taxes"] > 0

    # sync-status
    r = await client.get("/api/v1/tariff/sync-status")
    assert r.json()["total_codes"] == 3


@pytest.mark.asyncio
async def test_api_calculate_incomplete(client, db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    r = await client.post("/api/v1/tariff/calculate", json={
        "items": [{"hs_code": "0101.21.00.00", "invoice_value": 1000}]
    })
    out = r.json()
    assert out["complete"] is False
    assert out["items"][0]["hs_validation"] == "NOT_FOUND"
