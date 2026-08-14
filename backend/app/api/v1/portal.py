"""Portal del cliente (rol CUSTOMER u otros): sólo datos del cliente vinculado."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.session import get_session
from app.models.customer import Customer
from app.schemas.portal import (
    PortalCaseDetail,
    PortalCaseSummary,
    PortalCustomer,
    PortalProfile,
    PortalQuote,
)
from app.schemas.settlement import SettlementRead
from app.services import portal, settlement_service, tracking

router = APIRouter(prefix="/portal", tags=["portal"])


async def _customer(
    session: AsyncSession, principal: Principal
) -> Customer:
    customer = await portal.resolve_customer(session, principal)
    if customer is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No hay un cliente vinculado a su cuenta. Contacte a su ejecutivo.",
        )
    return customer


@router.get("/me", response_model=PortalProfile)
async def me(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> PortalProfile:
    customer = await portal.resolve_customer(session, principal)
    if customer is None:
        return PortalProfile(linked=False)
    return PortalProfile(
        linked=True,
        customer=PortalCustomer.model_validate(customer, from_attributes=True),
        cases=await portal.count_cases(session, customer.id),
        quotes=await portal.count_quotes(session, customer.id),
    )


@router.get("/cases", response_model=list[PortalCaseSummary])
async def my_cases(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> list[PortalCaseSummary]:
    customer = await _customer(session, principal)
    return [PortalCaseSummary(**c) for c in await portal.list_cases(session, customer.id)]


@router.get("/cases/{case_id}", response_model=PortalCaseDetail)
async def my_case(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> PortalCaseDetail:
    customer = await _customer(session, principal)
    case = await portal.owned_case(session, customer.id, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    track = await tracking.build_view(session, case)
    stl = await settlement_service.get_for_case(session, case.id)
    # El cliente sólo ve la liquidación una vez emitida.
    settlement = (
        SettlementRead.model_validate(stl, from_attributes=True)
        if stl and stl.status == "ISSUED"
        else None
    )
    return PortalCaseDetail(track=track, settlement=settlement)


@router.get("/quotes", response_model=list[PortalQuote])
async def my_quotes(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> list[PortalQuote]:
    customer = await _customer(session, principal)
    quotes = await portal.list_quotes(session, customer.id)
    return [
        PortalQuote(
            id=q.id, quote_number=q.quote_number, version=q.version, status=q.status,
            currency=q.currency, customer_price_total=float(q.customer_price_total or 0),
            landed_cost_total=float(q.landed_cost_total or 0), valid_until=q.valid_until,
            created_at=q.created_at,
        )
        for q in quotes
    ]
