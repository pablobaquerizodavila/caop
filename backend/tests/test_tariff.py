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
        base_formula="CIF+AD_VALOREM+FODINFA+ICE+SAFP+SAFEGUARD",
        depends_on=["AD_VALOREM", "FODINFA", "ICE", "SAFP", "SAFEGUARD"],
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


@pytest.mark.asyncio
async def test_api_history(client, db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    r = await client.get("/api/v1/tariff/codes/8471.30.00.00/history")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["status"] == "ACTIVE" and float(row["ad_valorem"]) == 5 for row in rows)


@pytest.mark.asyncio
async def test_api_ficha_hierarchy(client, db_sessionmaker):
    parent = TariffRecord(
        code="8471.30", code_normalized="847130", level=6,
        description="Máquinas automáticas portátiles", physical_unit=None,
        ad_valorem=None, parent_code=None,
    )
    child = TariffRecord(
        code="8471.30.00.00", code_normalized="8471300000", level=10,
        description="De peso inferior o igual a 10 kg", physical_unit="u",
        ad_valorem=Decimal("5"), parent_code="847130",
    )
    async with db_sessionmaker() as s:
        await _seed_general(s)
        res = await import_arancel(s, records=[parent, child], version_number="H-1",
                                   effective_from=date(2023, 9, 1))
        await publish_version(s, res.version_id)
        await s.commit()

    r = await client.get("/api/v1/tariff/codes/8471.30.00.00")
    assert any(a["code"] == "8471.30" for a in r.json()["ancestors"])
    r2 = await client.get("/api/v1/tariff/codes/8471.30")
    assert any(c["code"] == "8471.30.00.00" for c in r2.json()["children"])


# ---------- preferencias (Fase 2B) ----------
async def _seed_agreements(session):
    from app.services.trade_agreement_seed import seed_agreements, seed_countries
    await seed_countries(session)
    await seed_agreements(session)


@pytest.mark.asyncio
async def test_preference_scenario_can(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)          # 8471.30.00.00 con Ad-Valorem 5%
        await _seed_agreements(s)  # CAN 100% liberación para originarios
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00", origin_country="CO"),
            date.today(),
        )
        assert ri.preference is not None
        assert ri.preference.agreement_code == "CAN"
        assert ri.preference.preferential_adval_pct == Decimal("0")   # 100% liberación
        assert ri.preference.result.total_taxes < ri.result.total_taxes
        assert ri.preference.savings > 0
        assert ri.preference.requires_certificate is True


@pytest.mark.asyncio
async def test_no_preference_for_nonmember(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
        await _seed_agreements(s)
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00", origin_country="US"),
            date.today(),
        )
        assert ri.preference is None   # EE.UU. no es miembro de un acuerdo con preferencia cargada


@pytest.mark.asyncio
async def test_api_calculate_with_preference(client, db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
        await _seed_agreements(s)
        await s.commit()
    r = await client.post("/api/v1/tariff/calculate", json={
        "items": [{"hs_code": "8471.30.00.00", "invoice_value": 1000, "origin_country": "PE"}]
    })
    out = r.json()
    pref = out["items"][0]["preference"]
    assert pref is not None
    assert pref["agreement_code"] == "CAN"
    assert pref["savings"] > 0


@pytest.mark.asyncio
async def test_quote_preference_and_certificate(db_sessionmaker):
    from app.models.quote import Quote, QuoteItem
    from app.models.trade import CertificateOfOrigin
    from app.services.quotation import recompute_quote

    async with db_sessionmaker() as s:
        await _ingest(s)
        await _seed_agreements(s)
        await s.commit()
    async with db_sessionmaker() as s:
        q = Quote(quote_number="Q-1", currency="USD", calculation_date=date.today(),
                  origin_country="CO")
        q.items = [QuoteItem(
            line_no=1, description="Laptop", hs_code="8471.30.00.00", origin_country="CO",
            quantity=Decimal(1), unit_price=Decimal(1000), line_value=Decimal(1000),
        )]
        q.cost_lines = []
        q.status_history = []
        s.add(q)
        await s.flush()
        await recompute_quote(s, q)
        await s.flush()
        it = q.items[0]
        assert it.preference is not None
        assert it.preference["agreement_code"] == "CAN"
        assert it.preference["certificate_present"] is False  # aún sin certificado → potencial

        s.add(CertificateOfOrigin(quote_id=q.id, issuing_country="CO", validation_status="VALID"))
        await s.flush()
        await recompute_quote(s, q)
        await s.flush()
        assert q.items[0].preference["certificate_present"] is True  # certificado válido → aplicable


@pytest.mark.asyncio
async def test_ice_ad_valorem_chains_into_iva(db_sessionmaker):
    from app.models.trade import IceMeasure
    async with db_sessionmaker() as s:
        await _ingest(s)  # 8471.30.00.00 Ad-Valorem 5%, FODINFA/IVA
        s.add(IceMeasure(hs_prefix="847130", method="AD_VALOREM", ad_valorem_pct=Decimal("10"),
                         base_type="EX_ADUANA", effective_from=date(2020, 1, 1),
                         verification_status="VERIFIED"))
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00"), date.today()
        )
        comps = {c.tax_type: c.amount for c in ri.result.components}
        assert comps.get("ICE") == Decimal("105.50")   # 10% de ex-aduana (1000+50+5)
        assert comps.get("IVA") == Decimal("174.08")    # IVA sobre base que incluye ICE
        assert ri.result.complete is True


@pytest.mark.asyncio
async def test_ice_not_subject(db_sessionmaker):
    async with db_sessionmaker() as s:
        await _ingest(s)
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00"), date.today()
        )
        assert all(c.tax_type != "ICE" for c in ri.result.components)  # sin IceMeasure => no sujeto


@pytest.mark.asyncio
async def test_ice_insufficient_info(db_sessionmaker):
    from app.models.trade import IceMeasure
    async with db_sessionmaker() as s:
        await _ingest(s)
        s.add(IceMeasure(hs_prefix="847130", method="SPECIFIC", specific_rate=Decimal("10.41"),
                         specific_unit="LITRO_ALCOHOL_PURO", effective_from=date(2020, 1, 1),
                         verification_status="VERIFIED"))
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00"), date.today()
        )
        assert ri.result.complete is False
        assert any("ICE_INFO_INSUFICIENTE" in w for w in ri.result.warnings)


@pytest.mark.asyncio
async def test_safp_variable_duty(db_sessionmaker):
    from datetime import timedelta

    from app.models.trade import PriceBandMeasure, PriceBandPeriod
    async with db_sessionmaker() as s:
        await _ingest(s)  # 8471.30 Ad-Valorem 5%
        band = PriceBandMeasure(hs_prefix="8471", product="Prueba franja", is_marker=True)
        s.add(band)
        await s.flush()
        today = date.today()
        s.add(PriceBandPeriod(
            measure_id=band.id, period_start=today - timedelta(days=7),
            period_end=today + timedelta(days=7), reference_price=Decimal("100"),
            floor_price=Decimal("120"), ceiling_price=Decimal("150"),
            variable_method="AD_VALOREM", variable_value=Decimal("10"),
            verification_status="VERIFIED",
        ))
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00"), date.today()
        )
        comps = {c.tax_type: c.amount for c in ri.result.components}
        assert comps.get("SAFP") == Decimal("105.50")   # 10% de ex-aduana (1000+50+5)
        assert comps.get("IVA") == Decimal("174.08")     # IVA incluye SAFP en su base
        assert ri.result.complete is True


@pytest.mark.asyncio
async def test_safp_missing_period_insufficient(db_sessionmaker):
    from app.models.trade import PriceBandMeasure
    async with db_sessionmaker() as s:
        await _ingest(s)
        s.add(PriceBandMeasure(hs_prefix="8471", product="Prueba franja", is_marker=True))
        await s.commit()
    async with db_sessionmaker() as s:
        ri = await resolve_item(
            s, TaxItemInput(invoice_value=Decimal(1000), hs_code="8471.30.00.00"), date.today()
        )
        assert ri.result.complete is False
        assert any("SAFP_INFO_INSUFICIENTE" in w for w in ri.result.warnings)


@pytest.mark.asyncio
async def test_reconciliation(db_sessionmaker):
    from app.models.customer import Customer
    from app.models.quote import Quote, QuoteItem
    from app.models.shipment import CustomsCase, Shipment
    from app.services.quotation import recompute_quote
    from app.services.reconciliation import estimate_from_case, get_reconciliation, set_actual

    async with db_sessionmaker() as s:
        await _ingest(s)
        cust = Customer(ruc="1790012345001", legal_name="ACME")
        s.add(cust)
        await s.flush()
        q = Quote(quote_number="Q-R", currency="USD", calculation_date=date.today())
        q.items = [QuoteItem(line_no=1, hs_code="8471.30.00.00", description="Laptop",
                             quantity=Decimal(1), unit_price=Decimal(1000), line_value=Decimal(1000))]
        q.cost_lines = []
        q.status_history = []
        s.add(q)
        await s.flush()
        await recompute_quote(s, q)
        await s.flush()
        ship = Shipment(customer_id=cust.id, source_quote_id=q.id)
        s.add(ship)
        await s.flush()
        case = CustomsCase(shipment_id=ship.id, case_number="CASE-R")
        s.add(case)
        await s.flush()

        est, total = await estimate_from_case(s, case)
        assert total == q.total_taxes
        assert "AD_VALOREM" in est and "IVA" in est

        view = await set_actual(
            s, case,
            {"AD_VALOREM": est["AD_VALOREM"] + 10, "FODINFA": est.get("FODINFA", 0), "IVA": est.get("IVA", 0)},
            "ajuste de base", "tester",
        )
        assert view["difference"] is not None
        assert round(view["difference"], 2) == 10.0
        assert view["actual_total"] > view["estimated_total"]
