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
from app.models.trade import IceMeasure, TariffPreference, TradeAgreement
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


def _compute_ice(measure: IceMeasure, item: TaxItemInput, adval_amt: Decimal, fodinfa_amt: Decimal):
    """ICE por metodología (LRTI). Devuelve (TaxComponent|None, warning|None).

    AD_VALOREM: base ex-aduana (CIF+Ad-Valorem+FODINFA). SPECIFIC (unidad): tarifa×cantidad.
    Otras bases (PVP/referencia) o unidades especiales (alcohol/azúcar) → información insuficiente.
    """
    method = (measure.method or "AD_VALOREM").upper()
    ad = sp = Decimal(0)
    insufficient = False
    rate = None
    base = item.cif + adval_amt + fodinfa_amt
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
) -> ResolvedItem:
    if rules is None:
        rules = await _active_rules(session)
    if version_number is None:
        ver = await active_version(session)
        version_number = ver.number if ver else None
    tc = await _lookup_code(session, item.hs_code)

    base_injected = list(injected or [])
    # Preliminar: obtiene Ad-Valorem/FODINFA (base ex-aduana para el ICE).
    prelim = compute_item(rules, item, on, injected=base_injected)
    adval_amt = next((c.amount for c in prelim.components if c.tax_type == "AD_VALOREM"), Decimal(0))
    fodinfa_amt = next((c.amount for c in prelim.components if c.tax_type == "FODINFA"), Decimal(0))

    ice_warn = None
    full_injected = list(base_injected)
    if item.hs_code:
        measures = ice_cache if ice_cache is not None else await _ice_measures(session)
        ice_msr = _best_ice(measures, _normalize(item.hs_code), on)
        if ice_msr is not None:
            ice_comp, ice_warn = _compute_ice(ice_msr, item, adval_amt, fodinfa_amt)
            if ice_comp is not None:
                full_injected.append(ice_comp)

    result = compute_item(rules, item, on, injected=full_injected) if full_injected else prelim
    injected_types = {c.tax_type for c in full_injected}
    hs_validation = _finalize(result, item, tc, version_number, injected_types)
    if ice_warn:
        result.warnings.append(ice_warn)
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
    out: list[ResolvedItem] = []
    for it in items:
        out.append(await resolve_item(session, it, on, rules=rules, version_number=vn,
                                      prefs_cache=prefs_cache, ice_cache=ice_cache))
    return out
