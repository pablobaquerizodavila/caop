"""Tests unitarios del motor de cálculo de tributos (cadena de bases)."""

from datetime import date
from decimal import Decimal

from app.models.tax import TaxRule
from app.services.tax_engine import TaxItemInput, compute_item

TODAY = date(2026, 1, 1)


def _rule(tax_type, pct, base="CIF", depends=None, hs=None, origin=None, agreement=None, v=1):
    return TaxRule(
        tax_type=tax_type,
        hs_code=hs,
        origin_country=origin,
        commercial_agreement=agreement,
        calculation_method="AD_VALOREM_PCT",
        percentage=Decimal(str(pct)),
        base_formula=base,
        depends_on=depends or [],
        effective_from=date(2020, 1, 1),
        effective_to=None,
        status="ACTIVE",
        version=v,
    )


def test_chained_calculation_order_and_amounts():
    rules = [
        _rule("AD_VALOREM", 5, hs="8471.30.00"),
        _rule("FODINFA", 0.5),
        _rule("IVA", 15, base="CIF+AD_VALOREM+FODINFA", depends=["AD_VALOREM", "FODINFA"]),
    ]
    item = TaxItemInput(
        invoice_value=Decimal("1000"),
        freight=Decimal("100"),
        insurance=Decimal("10"),
        hs_code="8471.30.00",
    )
    res = compute_item(rules, item, TODAY)
    amounts = {c.tax_type: c.amount for c in res.components}

    assert res.cif_value == Decimal("1110.00")
    assert amounts["AD_VALOREM"] == Decimal("55.50")  # 1110 * 5%
    assert amounts["FODINFA"] == Decimal("5.55")  # 1110 * 0.5%
    assert amounts["IVA"] == Decimal("175.66")  # (1110+55.50+5.55) * 15%
    assert res.total_taxes == Decimal("236.71")

    # IVA debe calcularse DESPUÉS de sus dependencias
    seq = {c.tax_type: c.sequence for c in res.components}
    assert seq["IVA"] > seq["AD_VALOREM"] and seq["IVA"] > seq["FODINFA"]


def test_preferential_rule_wins_by_specificity():
    rules = [
        _rule("AD_VALOREM", 10, hs="0801.11.00"),  # general para esa subpartida
        _rule("AD_VALOREM", 0, hs="0801.11.00", origin="PE", agreement="CAN"),  # preferencial
    ]
    item = TaxItemInput(
        invoice_value=Decimal("1000"),
        hs_code="0801.11.00",
        origin_country="PE",
        commercial_agreement="CAN",
    )
    res = compute_item(rules, item, TODAY)
    adval = next(c for c in res.components if c.tax_type == "AD_VALOREM")
    assert adval.amount == Decimal("0.00")  # gana la regla preferencial más específica


def test_general_rules_apply_without_hs():
    rules = [_rule("FODINFA", 0.5), _rule("IVA", 15, base="CIF+FODINFA", depends=["FODINFA"])]
    item = TaxItemInput(invoice_value=Decimal("2000"))  # sin hs_code
    res = compute_item(rules, item, TODAY)
    amounts = {c.tax_type: c.amount for c in res.components}
    assert amounts["FODINFA"] == Decimal("10.00")
    assert amounts["IVA"] == Decimal("301.50")  # (2000+10)*15%
