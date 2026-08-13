"""Endpoints del Tax Rule Engine y del simulador de tributos."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.tax import TaxRule
from app.schemas.tax import (
    TaxComponentOut,
    TaxItemOut,
    TaxRuleCreate,
    TaxRuleRead,
    TaxSimRequest,
    TaxSimResponse,
)
from app.services.tax_engine import TaxItemInput, compute_items
from app.services.tax_seed import seed_ecuador_defaults

router = APIRouter(prefix="/tax", tags=["tax"])

DISCLAIMER = (
    "Los tributos presentados son una estimación basada en la información disponible y en "
    "la normativa configurada como vigente al momento del cálculo. La liquidación definitiva "
    "será la determinada por las autoridades correspondientes según las condiciones reales de "
    "la importación."
)


@router.post("/rules", response_model=TaxRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: TaxRuleCreate, session: AsyncSession = Depends(get_session)
) -> TaxRule:
    rule = TaxRule(**payload.model_dump())
    session.add(rule)
    await session.flush()
    await session.refresh(rule)
    return rule


@router.get("/rules", response_model=list[TaxRuleRead])
async def list_rules(
    session: AsyncSession = Depends(get_session),
    tax_type: str | None = Query(None),
    hs_code: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[TaxRule]:
    stmt = select(TaxRule).order_by(TaxRule.tax_type, TaxRule.version.desc())
    if tax_type:
        stmt = stmt.where(TaxRule.tax_type == tax_type)
    if hs_code:
        stmt = stmt.where(TaxRule.hs_code == hs_code)
    result = await session.scalars(stmt.limit(limit).offset(offset))
    return list(result)


@router.post("/rules/seed-ecuador-defaults")
async def seed_defaults(session: AsyncSession = Depends(get_session)) -> dict:
    created = await seed_ecuador_defaults(session)
    return {
        "created": created,
        "note": "Reglas generales sembradas SIN verificar contra fuente oficial. "
        "Verifícalas (SENAE/COMEX/SRI) y actualiza last_verified_at.",
    }


@router.post("/simulate", response_model=TaxSimResponse)
async def simulate(
    payload: TaxSimRequest, session: AsyncSession = Depends(get_session)
) -> TaxSimResponse:
    on = payload.calculation_date or date.today()
    rules = list(await session.scalars(select(TaxRule).where(TaxRule.status == "ACTIVE")))

    inputs = [
        TaxItemInput(
            invoice_value=it.invoice_value,
            freight=it.freight,
            insurance=it.insurance,
            quantity=it.quantity,
            hs_code=it.hs_code,
            origin_country=it.origin_country,
            commercial_agreement=it.commercial_agreement,
            description=it.description,
        )
        for it in payload.items
    ]
    results = compute_items(rules, inputs, on)

    items_out: list[TaxItemOut] = []
    total_cif = 0.0
    total_taxes = 0.0
    for r in results:
        comps = [
            TaxComponentOut(
                tax_type=c.tax_type,
                base_amount=float(c.base_amount),
                rate_applied=(float(c.rate_applied) if c.rate_applied is not None else None),
                amount=float(c.amount),
                sequence=c.sequence,
                legal_source=c.legal_source,
                verified=c.verified,
            )
            for c in r.components
        ]
        item_taxes = float(r.total_taxes)
        items_out.append(
            TaxItemOut(
                description=r.description,
                hs_code=r.hs_code,
                cif_value=float(r.cif_value),
                components=comps,
                total_taxes=item_taxes,
            )
        )
        total_cif += float(r.cif_value)
        total_taxes += item_taxes

    return TaxSimResponse(
        calculation_date=on,
        currency=payload.currency,
        items=items_out,
        total_cif=round(total_cif, 2),
        total_taxes=round(total_taxes, 2),
        disclaimer=DISCLAIMER,
    )
