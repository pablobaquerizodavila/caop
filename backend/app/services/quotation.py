"""Cálculo de la cotización: tributos por ítem (Tax Engine) + landed cost + margen."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.trade import CertificateOfOrigin
from app.services.tariff_resolver import resolve_items
from app.services.tax_engine import TaxItemInput

CENT = Decimal("0.01")
MICRO = Decimal("0.000001")


def _q(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


async def recompute_quote(session: AsyncSession, quote: Quote) -> Quote:
    """Recalcula tributos, totales, landed cost y márgenes del quote in situ.

    Usa el resolvedor arancelario (maestro + reglas): valida la subpartida y señaliza
    'estimación incompleta' cuando falta información (nunca convierte faltante en 0%).
    """
    inputs = [
        TaxItemInput(
            invoice_value=Decimal(it.line_value or 0),
            freight=Decimal(it.freight_alloc or 0),
            insurance=Decimal(it.insurance_alloc or 0),
            quantity=Decimal(it.quantity or 0),
            hs_code=it.hs_code,
            origin_country=it.origin_country,
            commercial_agreement=it.commercial_agreement,
            description=it.description,
            attributes=it.attributes or {},
        )
        for it in quote.items
    ]
    resolved = await resolve_items(session, inputs, quote.calculation_date)

    # Certificados de origen VÁLIDOS y vigentes de esta cotización → habilitan la
    # preferencia como 'aplicable' (frente a 'potencial'). Se cruza por país emisor.
    valid_origins: set[str] = set()
    if quote.id is not None:
        certs = await session.scalars(
            select(CertificateOfOrigin).where(
                CertificateOfOrigin.quote_id == quote.id,
                CertificateOfOrigin.validation_status == "VALID",
            )
        )
        for c in certs:
            if c.issuing_country and (c.valid_until is None or c.valid_until >= quote.calculation_date):
                valid_origins.add(c.issuing_country)

    total_units = Decimal(0)
    total_cif = Decimal(0)
    total_taxes = Decimal(0)
    product_value = Decimal(0)
    total_freight = Decimal(0)
    total_insurance = Decimal(0)
    any_preliminary = False
    any_incomplete = False

    for it, ri in zip(quote.items, resolved, strict=True):
        res = ri.result
        it.cif_value = res.cif_value
        it.taxes_total = res.total_taxes
        it.hs_validation = ri.hs_validation
        it.tariff_code_id = ri.tariff_code_id
        it.tax_complete = res.complete
        it.tax_warnings = res.warnings or None
        it.tax_data_version = res.data_version
        it.tax_breakdown = [
            {
                "tax_type": c.tax_type,
                "base_amount": float(c.base_amount),
                "rate_applied": (float(c.rate_applied) if c.rate_applied is not None else None),
                "amount": float(c.amount),
                "sequence": c.sequence,
                "verified": c.verified,
            }
            for c in res.components
        ]
        total_cif += res.cif_value
        total_taxes += res.total_taxes
        product_value += Decimal(it.line_value or 0)
        total_freight += Decimal(it.freight_alloc or 0)
        total_insurance += Decimal(it.insurance_alloc or 0)
        total_units += Decimal(it.quantity or 0)
        if (it.hs_status or "PRELIMINARY") != "VALIDATED":
            any_preliminary = True
        if not res.complete:
            any_incomplete = True

        if ri.preference is not None:
            pf = ri.preference
            it.preference = {
                "agreement_code": pf.agreement_code,
                "agreement_name": pf.agreement_name,
                "preferential_adval_pct": float(pf.preferential_adval_pct),
                "preferential_taxes": float(pf.result.total_taxes),
                "savings": float(pf.savings),
                "requires_certificate": pf.requires_certificate,
                "certificate_present": (it.origin_country in valid_origins) if it.origin_country else False,
                "verified": pf.verified,
            }
        else:
            it.preference = None

    included = [cl for cl in quote.cost_lines if cl.is_included]
    customer_price = sum((Decimal(cl.quoted_amount or 0) for cl in included), Decimal(0))
    internal_cost = sum((Decimal(cl.estimated_amount or 0) for cl in included), Decimal(0))
    margin = customer_price - internal_cost
    margin_pct = (margin / customer_price * 100) if customer_price else Decimal(0)
    any_low = any((cl.confidence or "MEDIUM") == "LOW" for cl in included)

    landed = product_value + total_freight + total_insurance + total_taxes + customer_price
    per_unit = (landed / total_units) if total_units else Decimal(0)

    quote.total_units = _q(total_units)
    quote.total_cif = _q(total_cif)
    quote.total_taxes = _q(total_taxes)
    quote.customer_price_total = _q(customer_price)
    quote.internal_cost_total = _q(internal_cost)
    quote.margin_amount = _q(margin)
    quote.margin_pct = _q(margin_pct)
    quote.landed_cost_total = _q(landed)
    quote.landed_cost_per_unit = per_unit.quantize(MICRO, rounding=ROUND_HALF_UP)

    confidence = Decimal(100)
    if any_preliminary:
        confidence = min(confidence, Decimal(70))  # clasificación preliminar
    if any_incomplete:
        confidence = min(confidence, Decimal(40))  # falta información arancelaria verificada
    if any_low:
        confidence -= Decimal(10)
    quote.confidence = max(confidence, Decimal(0))

    return quote
