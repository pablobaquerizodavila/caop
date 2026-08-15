"""Motor de cálculo de tributos de importación.

Principios:
- Nada de porcentajes en código: todo sale de TaxRule (versionadas por fecha).
- Cálculo POR ÍTEM.
- Cálculo EN CADENA: cada tributo declara su base (base_formula) y sus
  dependencias (depends_on). El orden se resuelve por dependencias, de modo que
  p. ej. IVA se calcula sobre CIF + AD_VALOREM + FODINFA + ICE + SAFEGUARD.
- Selección por especificidad: gana la regla más específica (hs_code > origen/acuerdo)
  y, a igualdad, la de mayor versión.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models.tax import TaxRule

CENT = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class TaxItemInput:
    invoice_value: Decimal
    freight: Decimal = Decimal(0)
    insurance: Decimal = Decimal(0)
    quantity: Decimal = Decimal(1)
    hs_code: str | None = None
    origin_country: str | None = None
    commercial_agreement: str | None = None
    description: str | None = None
    # Atributos para tarifas condicionales/por tramos (p. ej. {"CC": 2000} para vehículos).
    attributes: dict = field(default_factory=dict)

    @property
    def cif(self) -> Decimal:
        return self.invoice_value + self.freight + self.insurance

    @property
    def unit_value(self) -> Decimal:
        return self.invoice_value / self.quantity if self.quantity else self.invoice_value


@dataclass
class TaxComponent:
    tax_type: str
    base_amount: Decimal
    rate_applied: Decimal | None
    amount: Decimal
    sequence: int
    rule_id: str
    legal_source: str | None
    verified: bool


@dataclass
class TaxItemResult:
    description: str | None
    hs_code: str | None
    cif_value: Decimal
    components: list[TaxComponent] = field(default_factory=list)
    # --- S48: trazabilidad y señalización (aditivo, con defaults → retrocompatible) ---
    rules_used: list[str] = field(default_factory=list)
    legal_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    data_version: str | None = None
    complete: bool = True

    @property
    def total_taxes(self) -> Decimal:
        return _q(sum((c.amount for c in self.components), Decimal(0)))


class TaxEngineError(ValueError):
    pass


def _specificity(rule: TaxRule) -> int:
    return (2 if rule.hs_code else 0) + (1 if rule.origin_country else 0) + (
        1 if rule.commercial_agreement else 0
    )


def select_rules(rules: list[TaxRule], item: TaxItemInput, on: date) -> dict[str, TaxRule]:
    """Devuelve, por tax_type, la regla ACTIVE más específica vigente en la fecha."""
    best: dict[str, tuple[int, TaxRule]] = {}
    for r in rules:
        if r.status != "ACTIVE":
            continue
        if not (r.effective_from <= on and (r.effective_to is None or on <= r.effective_to)):
            continue
        if r.hs_code and r.hs_code != item.hs_code:
            continue
        if r.origin_country and r.origin_country != item.origin_country:
            continue
        if r.commercial_agreement and r.commercial_agreement != item.commercial_agreement:
            continue
        score = _specificity(r)
        cur = best.get(r.tax_type)
        if cur is None or score > cur[0] or (score == cur[0] and r.version > cur[1].version):
            best[r.tax_type] = (score, r)
    return {t: rp[1] for t, rp in best.items()}


def _eval_base(formula: str, cif: Decimal, computed: dict[str, Decimal]) -> Decimal:
    total = Decimal(0)
    for raw in (formula or "CIF").split("+"):
        tok = raw.strip().upper()
        if not tok:
            continue
        if tok == "CIF":
            total += cif
        else:
            total += computed.get(tok, Decimal(0))  # tributo aún no presente = 0
    return total


def _amount_for(rule: TaxRule, base: Decimal, quantity: Decimal) -> tuple[Decimal, Decimal | None]:
    method = (rule.calculation_method or "AD_VALOREM_PCT").upper()
    if method == "SPECIFIC":
        rate = rule.specific_rate or Decimal(0)
        return rate * quantity, None
    if method == "MIXED":
        adval = base * (rule.percentage or Decimal(0)) / Decimal(100)
        spec = (rule.specific_rate or Decimal(0)) * quantity
        return adval + spec, rule.percentage
    # AD_VALOREM_PCT
    pct = rule.percentage or Decimal(0)
    return base * pct / Decimal(100), pct


def compute_item(
    rules: list[TaxRule],
    item: TaxItemInput,
    on: date,
    injected: list[TaxComponent] | None = None,
    overrides: dict[str, Decimal] | None = None,
) -> TaxItemResult:
    """Calcula los tributos de un ítem. `injected` permite aportar componentes de
    medidas con metodología propia (ICE/SAFP/antidumping) para que participen en la
    base compuesta (p. ej. IVA) sin vivir en TaxRule. `overrides` reemplaza el % de un
    tributo (p. ej. AD_VALOREM preferencial) recalculando la cadena. Sin ambos, idéntico."""
    selected = select_rules(rules, item, on)
    result = TaxItemResult(description=item.description, hs_code=item.hs_code, cif_value=_q(item.cif))

    computed: dict[str, Decimal] = {}
    seq = 0
    # Componentes inyectados (metodología propia): entran a la base antes de resolver.
    for comp in injected or []:
        computed[comp.tax_type] = comp.amount
        seq += 1
        result.components.append(comp)

    pending = dict(selected)
    # Resolución por dependencias: se calcula una regla cuando todas sus
    # dependencias (que están seleccionadas) ya fueron computadas.
    progress = True
    while pending and progress:
        progress = False
        for tax_type in list(pending):
            rule = pending[tax_type]
            deps = [d.upper() for d in (rule.depends_on or []) if d.upper() in selected]
            if all(d in computed for d in deps):
                base = _eval_base(rule.base_formula, item.cif, computed)
                if overrides and tax_type in overrides:
                    rate = overrides[tax_type]
                    amount = base * rate / Decimal(100)
                else:
                    amount, rate = _amount_for(rule, base, item.quantity)
                amount = _q(amount)
                computed[tax_type] = amount
                seq += 1
                result.components.append(
                    TaxComponent(
                        tax_type=tax_type,
                        base_amount=_q(base),
                        rate_applied=rate,
                        amount=amount,
                        sequence=seq,
                        rule_id=str(rule.id),
                        legal_source=rule.legal_source,
                        verified=rule.last_verified_at is not None,
                    )
                )
                del pending[tax_type]
                progress = True
    if pending:
        raise TaxEngineError(
            f"Dependencia circular o no resoluble en tributos: {list(pending)}"
        )
    result.components.sort(key=lambda c: c.sequence)
    result.rules_used = [c.rule_id for c in result.components if c.rule_id]
    result.legal_sources = sorted({c.legal_source for c in result.components if c.legal_source})
    return result


def compute_items(
    rules: list[TaxRule], items: list[TaxItemInput], on: date
) -> list[TaxItemResult]:
    return [compute_item(rules, it, on) for it in items]
