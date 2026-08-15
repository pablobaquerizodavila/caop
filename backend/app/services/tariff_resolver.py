"""Resolvedor arancelario: orquesta el maestro + reglas y alimenta al tax_engine.

Aquí vive la regla NO NEGOCIABLE «faltante ≠ 0%»: se distingue explícitamente entre
una tarifa 0% OFICIAL (existe una regla con 0) y la AUSENCIA de dato (no hay regla /
subpartida no está en el maestro), que produce TARIFF_DATA_NOT_FOUND y marca la
estimación como incompleta. Nunca se asume 0% por falta de información.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from decimal import ROUND_HALF_UP, Decimal

from app.models.tariff import TariffCode
from app.models.tax import TaxRule
from app.models.trade import (
    IceMeasure,
    PriceBandMeasure,
    PriceBandPeriod,
    TariffPreference,
    TradeAgreement,
    TradeRemedy,
)
from app.services.tariff_ingest import active_version
from app.services.tax_engine import TaxComponent, TaxItemInput, TaxItemResult, compute_item

_CENT = Decimal("0.01")


def _q2(v: Decimal) -> Decimal:
    return v.quantize(_CENT, rounding=ROUND_HALF_UP)

# Tributos que SIEMPRE deben poder determinarse en una importación general.
EXPECTED_MANDATORY = ("AD_VALOREM", "FODINFA", "IVA")


@dataclass
class PreferenceScenario:
    agreement_code: str
    agreement_name: str
    liberation_pct: Decimal
    preferential_adval_pct: Decimal
    requires_certificate: bool
    verified: bool
    result: TaxItemResult
    savings: Decimal


@dataclass
class ResolvedItem:
    result: TaxItemResult
    tariff_code_id: uuid.UUID | None
    hs_validation: str  # VALID / NOT_FOUND / UNKNOWN
    preference: PreferenceScenario | None = None


def _normalize(hs_code: str | None) -> str:
    return (hs_code or "").replace(".", "").replace(" ", "").strip()


async def _active_rules(session: AsyncSession) -> list[TaxRule]:
    return list(await session.scalars(select(TaxRule).where(TaxRule.status == "ACTIVE")))


async def _lookup_code(session: AsyncSession, hs_code: str | None) -> TariffCode | None:
    norm = _normalize(hs_code)
    if not norm:
        return None
    return await session.scalar(
        select(TariffCode).where(
            TariffCode.code_normalized == norm, TariffCode.status == "ACTIVE"
        )
    )


def _finalize(
    result: TaxItemResult,
    item: TaxItemInput,
    tc: TariffCode | None,
    version_number: str | None,
    injected_types: set[str] | None = None,
) -> str:
    """Aplica 'faltante ≠ 0%' y devuelve el hs_validation."""
    result.data_version = version_number
    present = {c.tax_type for c in result.components} | (injected_types or set())

    hs_validation = "UNKNOWN"
    if item.hs_code:
        hs_validation = "VALID" if tc is not None else "NOT_FOUND"
        if tc is None:
            result.complete = False
            result.warnings.append(
                f"TARIFF_DATA_NOT_FOUND: la subpartida {item.hs_code} no está en el "
                "maestro arancelario vigente"
            )
    else:
        result.complete = False
        result.warnings.append(
            "SIN_SUBPARTIDA: no se indicó subpartida; no se puede determinar el arancel"
        )

    for t in EXPECTED_MANDATORY:
        if t not in present:
            result.missing_information.append(t)
            result.complete = False
            if t == "AD_VALOREM" and tc is not None:
                result.warnings.append(
                    f"TARIFF_DATA_NOT_FOUND: no hay arancel Ad-Valorem vigente para "
                    f"{item.hs_code} en la versión arancelaria activa"
                )

    unverified = sorted({c.tax_type for c in result.components if not c.verified})
    if unverified:
        result.warnings.append(
            "TARIFA_NO_VERIFICADA: pendiente de verificación oficial: " + ", ".join(unverified)
        )
    return hs_validation


async def _preferences(session: AsyncSession) -> tuple[list[TariffPreference], dict]:
    prefs = list(await session.scalars(
        select(TariffPreference).where(TariffPreference.status == "ACTIVE")
    ))
    ags = {a.id: a for a in await session.scalars(
        select(TradeAgreement).where(TradeAgreement.status == "ACTIVE")
    )}
    return prefs, ags


def _best_preference(prefs, ags, origin: str, hs_norm: str, on: date):
    """Preferencia más específica aplicable a (origen, subpartida, fecha)."""
    best = None
    best_ag = None
    best_spec = -1
    for p in prefs:
        ag = ags.get(p.agreement_id)
        if ag is None:
            continue
        members = ag.members or []
        if p.origin_country:
            if p.origin_country != origin:
                continue
        elif origin not in members:
            continue
        if p.hs_prefix and not hs_norm.startswith(p.hs_prefix):
            continue
        if not (p.effective_from <= on and (p.effective_to is None or on <= p.effective_to)):
            continue
        spec = (2 if p.origin_country else 0) + (len(p.hs_prefix) if p.hs_prefix else 0)
        if spec > best_spec:
            best_spec, best, best_ag = spec, p, ag
    return best, best_ag


async def _ice_measures(session: AsyncSession) -> list[IceMeasure]:
    return list(await session.scalars(select(IceMeasure).where(IceMeasure.status == "ACTIVE")))


def _best_ice(measures: list[IceMeasure], hs_norm: str, on: date) -> IceMeasure | None:
    best = None
    best_len = -1
    for m in measures:
        pref = m.hs_prefix or ""
        if pref and not hs_norm.startswith(pref):
            continue
        if not (m.effective_from <= on and (m.effective_to is None or on <= m.effective_to)):
            continue
        if len(pref) > best_len:
            best_len, best = len(pref), m
    return best


async def _price_bands(session: AsyncSession) -> tuple[list[PriceBandMeasure], list[PriceBandPeriod]]:
    measures = list(await session.scalars(
        select(PriceBandMeasure).where(PriceBandMeasure.status == "ACTIVE")
    ))
    periods = list(await session.scalars(select(PriceBandPeriod)))
    return measures, periods


def _best_band(measures: list[PriceBandMeasure], hs_norm: str) -> PriceBandMeasure | None:
    best = None
    best_len = -1
    for m in measures:
        pref = m.hs_prefix or ""
        if pref and not hs_norm.startswith(pref):
            continue
        if len(pref) > best_len:
            best_len, best = len(pref), m
    return best


def _band_period(periods: list[PriceBandPeriod], measure_id, on: date) -> PriceBandPeriod | None:
    for p in periods:
        if p.measure_id == measure_id and p.period_start <= on <= p.period_end:
            return p
    return None


def _compute_safp(period: PriceBandPeriod, item: TaxItemInput, base_ex_aduana: Decimal):
    """Derecho variable SAFP (ad valorem sobre ex-aduana o específico por unidad). Puede ser
    negativo (rebaja). Devuelve (TaxComponent|None, warning|None)."""
    method = (period.variable_method or "AD_VALOREM").upper()
    val = Decimal(period.variable_value or 0)
    if method == "SPECIFIC":
        unit = (period.specific_unit or "").upper()
        if unit not in ("UNIDAD", "U", ""):
            return None, ("SAFP_INFO_INSUFICIENTE: derecho variable específico en unidad no "
                          "soportada; cargar el valor publicado por la CAN.")
        amount = _q2(val * Decimal(item.quantity or 0))
        rate = None
    else:
        amount = _q2(base_ex_aduana * val / Decimal(100))
        rate = val
    comp = TaxComponent(
        tax_type="SAFP", base_amount=_q2(base_ex_aduana), rate_applied=rate, amount=amount,
        sequence=2, rule_id=f"safp:{period.id}", legal_source=period.legal_source,
        verified=period.verification_status == "VERIFIED",
    )
    return comp, None


def _compute_ice(measure: IceMeasure, item: TaxItemInput, base_ex_aduana: Decimal):
    """ICE por metodología (LRTI). Devuelve (TaxComponent|None, warning|None).

    AD_VALOREM: sobre base ex-aduana (CIF+Ad-Valorem+FODINFA+SAFP). SPECIFIC (unidad):
    tarifa×cantidad. Otras bases (PVP/referencia) o unidades especiales → info insuficiente.
    """
    method = (measure.method or "AD_VALOREM").upper()
    ad = sp = Decimal(0)
    insufficient = False
    rate = None
    base = base_ex_aduana
    if method in ("AD_VALOREM", "MIXED"):
        if measure.ad_valorem_pct is not None and measure.base_type == "EX_ADUANA":
            ad = base * Decimal(measure.ad_valorem_pct) / Decimal(100)
            rate = Decimal(measure.ad_valorem_pct)
        else:
            insufficient = True
    if method in ("SPECIFIC", "MIXED"):
        unit = (measure.specific_unit or "").upper()
        if measure.specific_rate is not None and unit in ("UNIDAD", "U", ""):
            sp = Decimal(measure.specific_rate) * Decimal(item.quantity or 0)
        else:
            insufficient = True
    total = _q2(ad + sp)
    warn = None
    if insufficient:
        warn = ("ICE_INFO_INSUFICIENTE: subpartida sujeta a ICE pero falta información para "
                "calcularlo (base PVP/referencia o unidad especial como grado alcohólico/azúcar).")
    if total == 0 and insufficient:
        return None, warn
    comp = TaxComponent(
        tax_type="ICE", base_amount=_q2(base), rate_applied=rate, amount=total, sequence=3,
        rule_id=f"ice:{measure.id}", legal_source=measure.legal_source,
        verified=measure.verification_status == "VERIFIED",
    )
    return comp, warn


async def _trade_remedies(session: AsyncSession) -> list[TradeRemedy]:
    return list(await session.scalars(select(TradeRemedy).where(TradeRemedy.status == "ACTIVE")))


def _applicable_remedies(remedies: list[TradeRemedy], hs_norm: str, origin: str | None, on: date):
    out = []
    for r in remedies:
        if r.hs_prefix and not hs_norm.startswith(r.hs_prefix):
            continue
        if r.origin_country and r.origin_country != origin:
            continue
        if not (r.effective_from <= on and (r.effective_to is None or on <= r.effective_to)):
            continue
        out.append(r)
    return out


def _compute_remedy(remedy: TradeRemedy, item: TaxItemInput) -> TaxComponent:
    """Derecho de defensa comercial: ad valorem sobre CIF o específico por unidad."""
    if (remedy.method or "AD_VALOREM").upper() == "SPECIFIC":
        amount = _q2(Decimal(remedy.specific_rate or 0) * Decimal(item.quantity or 0))
        rate = None
    else:
        rate = Decimal(remedy.ad_valorem_pct or 0)
        amount = _q2(item.cif * rate / Decimal(100))
    return TaxComponent(
        tax_type=remedy.kind, base_amount=_q2(item.cif), rate_applied=rate, amount=amount,
        sequence=4, rule_id=f"remedy:{remedy.id}", legal_source=remedy.legal_source,
        verified=remedy.verification_status == "VERIFIED",
    )


async def resolve_item(
    session: AsyncSession,
    item: TaxItemInput,
    on: date,
    *,
    rules: list[TaxRule] | None = None,
    version_number: str | None = None,
    injected: list[TaxComponent] | None = None,
    prefs_cache: tuple[list, dict] | None = None,
    ice_cache: list | None = None,
    band_cache: tuple[list, list] | None = None,
    remedy_cache: list | None = None,
) -> ResolvedItem:
    if rules is None:
        rules = await _active_rules(session)
    if version_number is None:
        ver = await active_version(session)
        version_number = ver.number if ver else None
    tc = await _lookup_code(session, item.hs_code)

    base_injected = list(injected or [])
    # Preliminar: obtiene Ad-Valorem/FODINFA (base ex-aduana para SAFP e ICE).
    prelim = compute_item(rules, item, on, injected=base_injected)
    adval_amt = next((c.amount for c in prelim.components if c.tax_type == "AD_VALOREM"), Decimal(0))
    fodinfa_amt = next((c.amount for c in prelim.components if c.tax_type == "FODINFA"), Decimal(0))

    full_injected = list(base_injected)
    extra_warns: list[str] = []
    hs_norm = _normalize(item.hs_code)
    safp_amt = Decimal(0)

    # SAFP (franja de precios): va antes que ICE porque es un arancel adicional.
    if item.hs_code:
        measures, periods = band_cache if band_cache is not None else await _price_bands(session)
        band = _best_band(measures, hs_norm)
        if band is not None:
            period = _band_period(periods, band.id, on)
            if period is None:
                extra_warns.append(
                    "SAFP_INFO_INSUFICIENTE: subpartida sujeta a franja de precios pero sin "
                    "tabla quincenal vigente cargada (precio de referencia/derecho variable)."
                )
            else:
                safp_comp, safp_warn = _compute_safp(period, item, item.cif + adval_amt + fodinfa_amt)
                if safp_comp is not None:
                    full_injected.append(safp_comp)
                    safp_amt = safp_comp.amount
                if safp_warn:
                    extra_warns.append(safp_warn)

    # ICE (base ex-aduana incluye SAFP).
    if item.hs_code:
        ice_measures = ice_cache if ice_cache is not None else await _ice_measures(session)
        ice_msr = _best_ice(ice_measures, hs_norm, on)
        if ice_msr is not None:
            ice_comp, ice_warn = _compute_ice(
                ice_msr, item, item.cif + adval_amt + fodinfa_amt + safp_amt
            )
            if ice_comp is not None:
                full_injected.append(ice_comp)
            if ice_warn:
                extra_warns.append(ice_warn)

    # Medidas de defensa comercial (antidumping/salvaguardia/compensatorio): pueden
    # aplicar varias a la vez, sobre CIF. Se inyectan como su propio tipo.
    if item.hs_code:
        remedies = remedy_cache if remedy_cache is not None else await _trade_remedies(session)
        for r in _applicable_remedies(remedies, hs_norm, item.origin_country, on):
            full_injected.append(_compute_remedy(r, item))

    result = compute_item(rules, item, on, injected=full_injected) if full_injected else prelim
    injected_types = {c.tax_type for c in full_injected}
    hs_validation = _finalize(result, item, tc, version_number, injected_types)
    if extra_warns:
        result.warnings.extend(extra_warns)
        result.complete = False

    resolved = ResolvedItem(
        result=result, tariff_code_id=(tc.id if tc else None), hs_validation=hs_validation
    )

    # Escenario 'con preferencia potencial': requiere país de origen y arancel general conocido.
    adval = next((c for c in result.components if c.tax_type == "AD_VALOREM"), None)
    if item.origin_country and adval is not None and adval.rate_applied is not None:
        prefs, ags = prefs_cache if prefs_cache is not None else await _preferences(session)
        pref, ag = _best_preference(prefs, ags, item.origin_country, _normalize(item.hs_code), on)
        if pref is not None:
            base_pct = Decimal(adval.rate_applied)
            if pref.preferential_rate is not None:
                pref_pct = Decimal(pref.preferential_rate)
            else:
                pref_pct = base_pct * (Decimal(100) - Decimal(pref.liberation_pct)) / Decimal(100)
            pref_result = compute_item(rules, item, on, injected=full_injected,
                                       overrides={"AD_VALOREM": pref_pct})
            pref_result.data_version = version_number
            resolved.preference = PreferenceScenario(
                agreement_code=ag.code, agreement_name=ag.name,
                liberation_pct=Decimal(pref.liberation_pct), preferential_adval_pct=pref_pct,
                requires_certificate=pref.requires_certificate,
                verified=pref.verification_status == "VERIFIED",
                result=pref_result, savings=result.total_taxes - pref_result.total_taxes,
            )
    return resolved


async def resolve_items(
    session: AsyncSession, items: list[TaxItemInput], on: date
) -> list[ResolvedItem]:
    """Resuelve varios ítems cargando reglas y versión una sola vez (para cotizaciones)."""
    rules = await _active_rules(session)
    ver = await active_version(session)
    vn = ver.number if ver else None
    prefs_cache = await _preferences(session)
    ice_cache = await _ice_measures(session)
    band_cache = await _price_bands(session)
    remedy_cache = await _trade_remedies(session)
    out: list[ResolvedItem] = []
    for it in items:
        out.append(await resolve_item(session, it, on, rules=rules, version_number=vn,
                                      prefs_cache=prefs_cache, ice_cache=ice_cache,
                                      band_cache=band_cache, remedy_cache=remedy_cache))
    return out
