"""API del maestro arancelario: consulta, autocompletar, cálculo, ingesta y publicación."""

import hashlib
import tempfile
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_session
from app.models.tariff import TariffCode, TariffImport, TariffVersion
from app.models.tax import TaxRule
from app.models.tariff import LegalInstrument
from app.models.trade import (
    ControlAuthority,
    ControlDocument,
    Country,
    IceMeasure,
    PriceBandMeasure,
    PriceBandPeriod,
    TariffPreference,
    TariffRestriction,
    TariffTier,
    TradeAgreement,
    TradeRemedy,
)
from app.schemas.tariff import (
    IceMeasureCreate,
    IceMeasureOut,
    PreferenceScenarioOut,
    PriceBandMeasureCreate,
    PriceBandMeasureOut,
    PriceBandPeriodCreate,
    PriceBandPeriodOut,
    ControlAuthorityCreate,
    ControlAuthorityOut,
    ControlDocumentCreate,
    ControlDocumentOut,
    LegalInstrumentCreate,
    LegalInstrumentOut,
    RestrictionOut,
    SyncLogOut,
    SyncStatusOut,
    TariffChangeOut,
    TariffRestrictionCreate,
    TariffRestrictionOut,
    TariffTierCreate,
    TariffTierOut,
    TradeRemedyCreate,
    TradeRemedyOut,
    TariffCalcComponent,
    TariffCalcItemOut,
    TariffCalcRequest,
    TariffCalcResponse,
    TariffCodeDetail,
    TariffCodeOut,
    TariffHistoryEntry,
    TariffPreferenceCreate,
    TariffPreferenceOut,
    TariffPreferenceUpdate,
    TariffTaxOut,
    TariffVersionOut,
    TradeAgreementCreate,
    TradeAgreementOut,
)
from app.services.tariff_ingest import (
    active_version,
    changes_for_version,
    import_arancel,
    import_arancel_from_url,
    publish_version,
)
from app.services.tariff_resolver import resolve_item
from app.services.control_seed import seed_control_catalog
from app.services.tariff_bulk import PLANTILLAS, bulk_import
from app.services.tariff_sync import recent_logs, run_sync
from app.services.tax_engine import TaxItemInput
from app.services.trade_agreement_seed import seed_agreements, seed_countries

router = APIRouter(prefix="/tariff", tags=["tariff"])

DISCLAIMER = (
    "Los tributos presentados son una estimación basada en la versión arancelaria vigente "
    "en el sistema. Si la estimación está marcada como incompleta, falta información "
    "arancelaria verificada para una o más subpartidas. La liquidación definitiva la "
    "determina la autoridad aduanera según las condiciones reales de la importación."
)


def _norm(hs: str) -> str:
    return hs.replace(".", "").replace(" ", "").strip()


@router.get("/codes", response_model=list[TariffCodeOut])
async def search_codes(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(None, description="Texto de descripción o prefijo de código"),
    only_national: bool = Query(True, description="Solo subpartidas de 10 dígitos"),
    limit: int = Query(25, ge=1, le=100),
) -> list[TariffCode]:
    stmt = select(TariffCode).where(TariffCode.status == "ACTIVE")
    if only_national:
        stmt = stmt.where(TariffCode.level == 10)
    if q:
        digits = _norm(q)
        if digits.isdigit() and len(digits) >= 2:
            stmt = stmt.where(TariffCode.code_normalized.startswith(digits))
        else:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    TariffCode.description.ilike(like),
                    TariffCode.full_description.ilike(like),
                )
            )
    stmt = stmt.order_by(TariffCode.code_normalized).limit(limit)
    return list(await session.scalars(stmt))


async def _general_rate(session: AsyncSession, tax_type: str, on: date) -> TaxRule | None:
    rules = await session.scalars(
        select(TaxRule).where(
            TaxRule.tax_type == tax_type,
            TaxRule.status == "ACTIVE",
            TaxRule.hs_code.is_(None),
        )
    )
    best = None
    for r in rules:
        if r.effective_from <= on and (r.effective_to is None or on <= r.effective_to):
            if best is None or r.version > best.version:
                best = r
    return best


@router.get("/codes/{hs_code}", response_model=TariffCodeDetail)
async def code_detail(
    hs_code: str,
    session: AsyncSession = Depends(get_session),
    on: date | None = Query(None, alias="date"),
) -> TariffCodeDetail:
    on = on or date.today()
    norm = _norm(hs_code)
    code = await session.scalar(
        select(TariffCode).where(
            TariffCode.code_normalized == norm, TariffCode.status == "ACTIVE"
        )
    )
    if code is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Subpartida {hs_code} no está en el maestro vigente")

    taxes: list[TariffTaxOut] = []
    warnings: list[str] = []
    # AD_VALOREM: de la regla ligada al código
    adval = await session.scalar(
        select(TaxRule).where(
            TaxRule.tax_type == "AD_VALOREM",
            TaxRule.status == "ACTIVE",
            TaxRule.hs_code == code.code,
        )
    )
    if adval is not None:
        taxes.append(TariffTaxOut(
            tax_type="AD_VALOREM", percentage=adval.percentage,
            verified=adval.verification_status == "VERIFIED", legal_source=adval.legal_source,
        ))
    else:
        warnings.append("TARIFF_DATA_NOT_FOUND: sin arancel Ad-Valorem vigente para esta subpartida")
    for t in ("FODINFA", "IVA"):
        r = await _general_rate(session, t, on)
        if r is not None:
            taxes.append(TariffTaxOut(
                tax_type=t, percentage=r.percentage,
                verified=r.verification_status == "VERIFIED", legal_source=r.legal_source,
            ))
        else:
            warnings.append(f"Falta la regla general de {t}")

    # Jerarquía: cadena de ancestros (por parent_code) e hijos directos.
    ancestors: list[TariffCode] = []
    parent_norm = code.parent_code
    seen: set[str] = set()
    while parent_norm and parent_norm not in seen:
        seen.add(parent_norm)
        p = await session.scalar(
            select(TariffCode).where(
                TariffCode.code_normalized == parent_norm, TariffCode.status == "ACTIVE"
            )
        )
        if p is None:
            break
        ancestors.append(p)
        parent_norm = p.parent_code
    ancestors.reverse()
    children = list(await session.scalars(
        select(TariffCode).where(
            TariffCode.parent_code == code.code_normalized, TariffCode.status == "ACTIVE"
        ).order_by(TariffCode.code_normalized).limit(60)
    ))

    # Restricciones / control previo cuyo prefijo cubre esta subpartida.
    restrictions: list[RestrictionOut] = []
    all_restr = await session.scalars(
        select(TariffRestriction).where(TariffRestriction.status == "ACTIVE")
    )
    authorities = {a.id: a for a in await session.scalars(select(ControlAuthority))}
    documents = {d.id: d for d in await session.scalars(select(ControlDocument))}
    for r in all_restr:
        if r.hs_prefix and not norm.startswith(r.hs_prefix):
            continue
        if not (r.effective_from <= on and (r.effective_to is None or on <= r.effective_to)):
            continue
        doc = documents.get(r.control_document_id)
        auth = authorities.get(r.authority_id) or (authorities.get(doc.authority_id) if doc else None)
        restrictions.append(RestrictionOut(
            kind=r.kind, document=(doc.name if doc else None),
            authority=(auth.name if auth else None), requirement=r.requirement,
            blocking=r.blocking, legal=None,
        ))

    detail = TariffCodeDetail.model_validate(code)
    detail.taxes = taxes
    detail.warnings = warnings
    detail.ancestors = [TariffCodeOut.model_validate(a) for a in ancestors]
    detail.children = [TariffCodeOut.model_validate(c) for c in children]
    detail.restrictions = restrictions
    return detail


@router.get("/codes/{hs_code}/history", response_model=list[TariffHistoryEntry])
async def code_history(
    hs_code: str, session: AsyncSession = Depends(get_session)
) -> list[TariffHistoryEntry]:
    """Historial de Ad-Valorem de la subpartida a través de versiones (todas las vigencias)."""
    # Buscar el code (dotted) desde cualquier versión para conocer su forma con puntos.
    norm = _norm(hs_code)
    any_code = await session.scalar(
        select(TariffCode).where(TariffCode.code_normalized == norm).limit(1)
    )
    dotted = any_code.code if any_code else hs_code
    rules = list(await session.scalars(
        select(TaxRule).where(
            TaxRule.tax_type == "AD_VALOREM", TaxRule.hs_code == dotted
        ).order_by(TaxRule.effective_from.desc())
    ))
    ver_ids = {r.tariff_version_id for r in rules if r.tariff_version_id}
    versions = {}
    if ver_ids:
        for v in await session.scalars(select(TariffVersion).where(TariffVersion.id.in_(ver_ids))):
            versions[v.id] = v.number
    return [
        TariffHistoryEntry(
            version=versions.get(r.tariff_version_id),
            status=r.status, verification_status=r.verification_status,
            ad_valorem=r.percentage, effective_from=r.effective_from,
            effective_to=r.effective_to, legal_source=r.legal_source,
        )
        for r in rules
    ]


@router.post("/calculate", response_model=TariffCalcResponse)
async def calculate(
    payload: TariffCalcRequest, session: AsyncSession = Depends(get_session)
) -> TariffCalcResponse:
    on = payload.calculation_date or date.today()
    items_out: list[TariffCalcItemOut] = []
    total_cif = 0.0
    total_taxes = 0.0
    all_complete = True
    data_version = None
    for it in payload.items:
        ri = await resolve_item(
            session,
            TaxItemInput(
                invoice_value=it.invoice_value, freight=it.freight, insurance=it.insurance,
                quantity=it.quantity, hs_code=it.hs_code, origin_country=it.origin_country,
                commercial_agreement=it.commercial_agreement, description=it.description,
                attributes=it.attributes or {},
            ),
            on,
        )
        res = ri.result
        data_version = res.data_version
        comps = [
            TariffCalcComponent(
                tax_type=c.tax_type, base_amount=float(c.base_amount),
                rate_applied=(float(c.rate_applied) if c.rate_applied is not None else None),
                amount=float(c.amount), verified=c.verified,
            )
            for c in res.components
        ]
        pref_out = None
        if ri.preference is not None:
            p = ri.preference
            pref_out = PreferenceScenarioOut(
                agreement_code=p.agreement_code, agreement_name=p.agreement_name,
                liberation_pct=float(p.liberation_pct),
                preferential_adval_pct=float(p.preferential_adval_pct),
                requires_certificate=p.requires_certificate, verified=p.verified,
                total_taxes=float(p.result.total_taxes), savings=float(p.savings),
            )
        items_out.append(TariffCalcItemOut(
            description=res.description, hs_code=res.hs_code, hs_validation=ri.hs_validation,
            cif_value=float(res.cif_value), components=comps, total_taxes=float(res.total_taxes),
            complete=res.complete, warnings=res.warnings, missing_information=res.missing_information,
            preference=pref_out,
        ))
        total_cif += float(res.cif_value)
        total_taxes += float(res.total_taxes)
        all_complete = all_complete and res.complete

    return TariffCalcResponse(
        calculation_date=on, currency=payload.currency, data_version=data_version,
        items=items_out, total_cif=round(total_cif, 2), total_taxes=round(total_taxes, 2),
        complete=all_complete, disclaimer=DISCLAIMER,
    )


@router.get("/sync-status", response_model=SyncStatusOut)
async def sync_status(session: AsyncSession = Depends(get_session)) -> SyncStatusOut:
    ver = await active_version(session)
    total_codes = await session.scalar(
        select(func.count()).select_from(TariffCode).where(TariffCode.status == "ACTIVE")
    )
    total_rules = await session.scalar(
        select(func.count()).select_from(TaxRule).where(
            TaxRule.status == "ACTIVE", TaxRule.tax_type == "AD_VALOREM"
        )
    )
    last_imp = await session.scalar(
        select(TariffImport).order_by(TariffImport.created_at.desc()).limit(1)
    )
    return SyncStatusOut(
        active_version=TariffVersionOut.model_validate(ver) if ver else None,
        total_codes=total_codes or 0,
        total_active_rules=total_rules or 0,
        last_import_at=last_imp.created_at if last_imp else None,
        last_import_status=last_imp.status if last_imp else None,
    )


@router.get("/versions", response_model=list[TariffVersionOut])
async def list_versions(session: AsyncSession = Depends(get_session)) -> list[TariffVersion]:
    return list(await session.scalars(
        select(TariffVersion).order_by(TariffVersion.created_at.desc()).limit(50)
    ))


@router.post("/import", dependencies=[Depends(require_admin)])
async def import_tariff(
    version_number: str = Query(..., description="Identificador de la versión, p. ej. COMEX-002-2023"),
    effective_from: date = Query(..., description="Fecha de vigencia del arancel"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Archivo vacío")
    file_hash = hashlib.sha256(data).hexdigest()

    # Evidencia (raw) en almacenamiento de objetos (best-effort).
    raw_key = f"tariff/imports/{file_hash}.pdf"
    try:
        from app.services.storage import get_storage

        get_storage().put_object(raw_key, data, "application/pdf")
    except Exception:  # noqa: BLE001
        raw_key = None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    result = await import_arancel(
        session, version_number=version_number, effective_from=effective_from,
        path=tmp_path, filename=file.filename, file_hash=file_hash,
    )
    return {
        "import_id": str(result.import_id), "version_id": str(result.version_id),
        "version_number": result.version_number, "status": result.status,
        "codes": result.codes, "rules": result.rules, "errors": result.errors,
        "changes": result.changes, "raw_stored": bool(raw_key),
        "note": "Versión en STAGED. Revisa los cambios y publícala con POST /tariff/versions/{id}/publish.",
    }


@router.post("/import-url", dependencies=[Depends(require_admin)])
async def import_tariff_url(
    url: str = Query(..., description="URL del PDF oficial del arancel"),
    version_number: str = Query(...),
    effective_from: date = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """#8: descarga automática del arancel desde una URL y lo ingiere a versión STAGED."""
    try:
        result = await import_arancel_from_url(
            session, url=url, version_number=version_number, effective_from=effective_from
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"No se pudo descargar/parsear: {exc}") from exc
    return {
        "version_id": str(result.version_id), "version_number": result.version_number,
        "status": result.status, "codes": result.codes, "rules": result.rules,
        "errors": result.errors, "changes": result.changes,
    }


@router.get("/versions/{version_id}/changes", response_model=list[TariffChangeOut])
async def version_changes(version_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await changes_for_version(session, version_id)


@router.post("/versions/{version_id}/publish", dependencies=[Depends(require_admin)])
async def publish(version_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        return await publish_version(session, version_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# ---------- Acuerdos comerciales y preferencias ----------
@router.get("/agreements", response_model=list[TradeAgreementOut])
async def list_agreements(session: AsyncSession = Depends(get_session)) -> list[TradeAgreement]:
    return list(await session.scalars(
        select(TradeAgreement).order_by(TradeAgreement.code)
    ))


@router.post("/seed-agreements", dependencies=[Depends(require_admin)])
async def seed_ag(session: AsyncSession = Depends(get_session)) -> dict:
    countries = await seed_countries(session)
    created = await seed_agreements(session)
    return {"countries_created": countries, "agreements_created": created,
            "note": "Preferencias por subpartida deben cargarse/verificarse desde los anexos de cada acuerdo."}


@router.post("/agreements", response_model=TradeAgreementOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_agreement(
    payload: TradeAgreementCreate, session: AsyncSession = Depends(get_session)
) -> TradeAgreement:
    ag = TradeAgreement(**payload.model_dump())
    session.add(ag)
    await session.flush()
    await session.refresh(ag)
    return ag


@router.get("/preferences", response_model=list[TariffPreferenceOut])
async def list_preferences(
    session: AsyncSession = Depends(get_session),
    agreement_id: uuid.UUID | None = Query(None),
) -> list[TariffPreference]:
    stmt = select(TariffPreference).order_by(TariffPreference.created_at.desc()).limit(200)
    if agreement_id:
        stmt = stmt.where(TariffPreference.agreement_id == agreement_id)
    return list(await session.scalars(stmt))


@router.post("/preferences", response_model=TariffPreferenceOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_preference(
    payload: TariffPreferenceCreate, session: AsyncSession = Depends(get_session)
) -> TariffPreference:
    data = payload.model_dump()
    if data.get("hs_prefix"):
        data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    pref = TariffPreference(**data)
    session.add(pref)
    await session.flush()
    await session.refresh(pref)
    return pref


@router.patch("/preferences/{pref_id}", response_model=TariffPreferenceOut,
              dependencies=[Depends(require_admin)])
async def update_preference(
    pref_id: uuid.UUID, payload: TariffPreferenceUpdate, session: AsyncSession = Depends(get_session)
) -> TariffPreference:
    pref = await session.get(TariffPreference, pref_id)
    if pref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preferencia no encontrada")
    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "hs_prefix" and v:
            v = v.replace(".", "").strip()
        setattr(pref, k, v)
    await session.flush()
    return pref


@router.delete("/preferences/{pref_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_preference(pref_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    pref = await session.get(TariffPreference, pref_id)
    if pref is not None:
        await session.delete(pref)
        await session.flush()


@router.get("/countries", response_model=list[dict])
async def list_countries(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await session.scalars(select(Country).where(Country.active).order_by(Country.name))
    return [{"iso2": c.iso2, "name": c.name, "continent": c.continent} for c in rows]


@router.post("/seed-countries", dependencies=[Depends(require_admin)])
async def seed_countries_iso(session: AsyncSession = Depends(get_session)) -> dict:
    """Carga/actualiza el catálogo ISO 3166-1 completo (249) con continente."""
    from app.services.country_seed import seed_countries as _seed_iso

    return await _seed_iso(session)


@router.post("/clean-descriptions", dependencies=[Depends(require_admin)])
async def clean_descriptions(session: AsyncSession = Depends(get_session)) -> dict:
    """Limpia in situ las descripciones del arancel (encabezados, puntos, puntuación)."""
    from app.services.tariff_clean import clean_existing_descriptions

    return await clean_existing_descriptions(session)


# ---------- ICE (Impuesto a los Consumos Especiales) ----------
@router.get("/ice-measures", response_model=list[IceMeasureOut])
async def list_ice(session: AsyncSession = Depends(get_session)) -> list[IceMeasure]:
    return list(await session.scalars(
        select(IceMeasure).order_by(IceMeasure.hs_prefix).limit(500)
    ))


@router.post("/ice-measures", response_model=IceMeasureOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_ice(
    payload: IceMeasureCreate, session: AsyncSession = Depends(get_session)
) -> IceMeasure:
    data = payload.model_dump()
    data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    m = IceMeasure(**data)
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


@router.delete("/ice-measures/{measure_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_ice(measure_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    m = await session.get(IceMeasure, measure_id)
    if m is not None:
        await session.delete(m)
        await session.flush()


# ---------- SAFP (Franja Andina de Precios) ----------
@router.get("/price-bands", response_model=list[PriceBandMeasureOut])
async def list_price_bands(session: AsyncSession = Depends(get_session)) -> list[PriceBandMeasure]:
    return list(await session.scalars(
        select(PriceBandMeasure).order_by(PriceBandMeasure.product).limit(300)
    ))


@router.post("/price-bands", response_model=PriceBandMeasureOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_price_band(
    payload: PriceBandMeasureCreate, session: AsyncSession = Depends(get_session)
) -> PriceBandMeasure:
    data = payload.model_dump()
    data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    m = PriceBandMeasure(**data)
    session.add(m)
    await session.flush()
    await session.refresh(m)
    return m


@router.delete("/price-bands/{measure_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_price_band(measure_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    m = await session.get(PriceBandMeasure, measure_id)
    if m is not None:
        await session.delete(m)
        await session.flush()


@router.get("/price-bands/{measure_id}/periods", response_model=list[PriceBandPeriodOut])
async def list_band_periods(
    measure_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[PriceBandPeriod]:
    return list(await session.scalars(
        select(PriceBandPeriod).where(PriceBandPeriod.measure_id == measure_id)
        .order_by(PriceBandPeriod.period_start.desc()).limit(200)
    ))


@router.post("/price-bands/{measure_id}/periods", response_model=PriceBandPeriodOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_band_period(
    measure_id: uuid.UUID, payload: PriceBandPeriodCreate, session: AsyncSession = Depends(get_session)
) -> PriceBandPeriod:
    if await session.get(PriceBandMeasure, measure_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Franja no encontrada")
    p = PriceBandPeriod(measure_id=measure_id, **payload.model_dump())
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


@router.delete("/price-band-periods/{period_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_band_period(period_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    p = await session.get(PriceBandPeriod, period_id)
    if p is not None:
        await session.delete(p)
        await session.flush()


# ---------- Medidas de defensa comercial (antidumping/salvaguardia/compensatorio) ----------
@router.get("/trade-remedies", response_model=list[TradeRemedyOut])
async def list_trade_remedies(session: AsyncSession = Depends(get_session)) -> list[TradeRemedy]:
    return list(await session.scalars(
        select(TradeRemedy).order_by(TradeRemedy.kind, TradeRemedy.hs_prefix).limit(500)
    ))


@router.post("/trade-remedies", response_model=TradeRemedyOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_trade_remedy(
    payload: TradeRemedyCreate, session: AsyncSession = Depends(get_session)
) -> TradeRemedy:
    data = payload.model_dump()
    data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    if data.get("origin_country"):
        data["origin_country"] = data["origin_country"].upper()
    r = TradeRemedy(**data)
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r


@router.delete("/trade-remedies/{remedy_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_trade_remedy(remedy_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    r = await session.get(TradeRemedy, remedy_id)
    if r is not None:
        await session.delete(r)
        await session.flush()


# ---------- Tarifas condicionales / por tramos (vehículos y variables) ----------
@router.get("/tiers", response_model=list[TariffTierOut])
async def list_tiers(session: AsyncSession = Depends(get_session)) -> list[TariffTier]:
    return list(await session.scalars(
        select(TariffTier).order_by(TariffTier.hs_prefix).limit(300)
    ))


@router.post("/tiers", response_model=TariffTierOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_tier(
    payload: TariffTierCreate, session: AsyncSession = Depends(get_session)
) -> TariffTier:
    data = payload.model_dump()
    data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    t = TariffTier(**data)
    session.add(t)
    await session.flush()
    await session.refresh(t)
    return t


@router.delete("/tiers/{tier_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_tier(tier_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    t = await session.get(TariffTier, tier_id)
    if t is not None:
        await session.delete(t)
        await session.flush()


# ---------- #6: Base legal estructurada (normas) ----------
@router.get("/legal-instruments", response_model=list[LegalInstrumentOut])
async def list_legal(session: AsyncSession = Depends(get_session)) -> list[LegalInstrument]:
    return list(await session.scalars(
        select(LegalInstrument).order_by(LegalInstrument.created_at.desc()).limit(300)
    ))


@router.post("/legal-instruments", response_model=LegalInstrumentOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_legal(
    payload: LegalInstrumentCreate, session: AsyncSession = Depends(get_session)
) -> LegalInstrument:
    li = LegalInstrument(**payload.model_dump())
    session.add(li)
    await session.flush()
    await session.refresh(li)
    return li


@router.delete("/legal-instruments/{li_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_legal(li_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    li = await session.get(LegalInstrument, li_id)
    if li is not None:
        await session.delete(li)
        await session.flush()


# ---------- #5: Entidades, documentos y restricciones de control previo ----------
@router.get("/control-authorities", response_model=list[ControlAuthorityOut])
async def list_authorities(session: AsyncSession = Depends(get_session)) -> list[ControlAuthority]:
    return list(await session.scalars(select(ControlAuthority).order_by(ControlAuthority.code)))


@router.post("/control-authorities", response_model=ControlAuthorityOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_authority(
    payload: ControlAuthorityCreate, session: AsyncSession = Depends(get_session)
) -> ControlAuthority:
    a = ControlAuthority(**payload.model_dump())
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a


@router.get("/control-documents", response_model=list[ControlDocumentOut])
async def list_documents(session: AsyncSession = Depends(get_session)) -> list[ControlDocument]:
    return list(await session.scalars(select(ControlDocument).order_by(ControlDocument.code)))


@router.post("/control-documents", response_model=ControlDocumentOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_document(
    payload: ControlDocumentCreate, session: AsyncSession = Depends(get_session)
) -> ControlDocument:
    d = ControlDocument(**payload.model_dump())
    session.add(d)
    await session.flush()
    await session.refresh(d)
    return d


@router.get("/restrictions", response_model=list[TariffRestrictionOut])
async def list_restrictions(session: AsyncSession = Depends(get_session)) -> list[TariffRestriction]:
    return list(await session.scalars(
        select(TariffRestriction).order_by(TariffRestriction.hs_prefix).limit(500)
    ))


@router.post("/restrictions", response_model=TariffRestrictionOut, status_code=201,
             dependencies=[Depends(require_admin)])
async def create_restriction(
    payload: TariffRestrictionCreate, session: AsyncSession = Depends(get_session)
) -> TariffRestriction:
    data = payload.model_dump()
    data["hs_prefix"] = data["hs_prefix"].replace(".", "").strip()
    r = TariffRestriction(**data)
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r


@router.delete("/restrictions/{restriction_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_restriction(restriction_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    r = await session.get(TariffRestriction, restriction_id)
    if r is not None:
        await session.delete(r)
        await session.flush()


# ---------- #9: Vigilante de fuentes oficiales (resoluciones COMEX) ----------
@router.post("/sync/run", dependencies=[Depends(require_admin)])
async def sync_run(
    session: AsyncSession = Depends(get_session), source_code: str | None = Query(None)
) -> dict:
    return await run_sync(session, source_code=source_code)


@router.get("/sync/log", response_model=list[SyncLogOut])
async def sync_log(session: AsyncSession = Depends(get_session)):
    return await recent_logs(session)


@router.patch("/sources/{code}/url", dependencies=[Depends(require_admin)])
async def set_source_url(
    code: str, url: str = Query(...), session: AsyncSession = Depends(get_session)
) -> dict:
    """Configura la URL de una fuente oficial (p. ej. COMEX) para el vigilante (#5)."""
    src = await session.scalar(select(OfficialSource).where(OfficialSource.code == code.upper()))
    if src is None:
        src = OfficialSource(code=code.upper(), kind=code.upper(), name=code.upper())
        session.add(src)
    src.base_url = url
    src.active = True
    await session.flush()
    return {"code": src.code, "base_url": src.base_url}


# ---------- Sección B: catálogos y carga masiva de datos ----------
@router.post("/seed-control", dependencies=[Depends(require_admin)])
async def seed_control(session: AsyncSession = Depends(get_session)) -> dict:
    """Siembra entidades y documentos de control previo (catálogo de referencia)."""
    return await seed_control_catalog(session)


@router.get("/bulk/templates")
async def bulk_templates() -> dict:
    """Columnas esperadas por tipo para la carga masiva CSV."""
    return PLANTILLAS


@router.post("/bulk/{kind}", dependencies=[Depends(require_admin)])
async def bulk_upload(
    kind: str, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)
) -> dict:
    """Carga masiva por CSV (preferences/ice/remedies/restrictions)."""
    data = await file.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    try:
        return await bulk_import(session, kind, text)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
