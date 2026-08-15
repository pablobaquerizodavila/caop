"""Búsqueda global sobre expedientes, cotizaciones, clientes y proveedores."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.customer import Customer
from app.models.quote import Quote
from app.models.shipment import CustomsCase
from app.models.supplier import Supplier

router = APIRouter(prefix="/search", tags=["search"])

LIMIT = 10


@router.get("")
async def global_search(
    q: str = Query("", min_length=0), session: AsyncSession = Depends(get_session)
) -> dict:
    term = q.strip()
    if len(term) < 2:
        return {"query": term, "cases": [], "quotes": [], "customers": [], "suppliers": []}
    like = f"%{term}%"

    case_rows = await session.scalars(
        select(CustomsCase).where(CustomsCase.case_number.ilike(like))
        .order_by(CustomsCase.created_at.desc()).limit(LIMIT)
    )
    cases = [
        {"id": str(c.id), "label": c.case_number, "sub": c.current_state}
        for c in case_rows
    ]

    quote_rows = await session.scalars(
        select(Quote).where(Quote.quote_number.ilike(like))
        .order_by(Quote.created_at.desc()).limit(LIMIT)
    )
    quotes = [
        {"id": str(x.id), "label": f"{x.quote_number} v{x.version}", "sub": x.status}
        for x in quote_rows
    ]

    cust_rows = await session.scalars(
        select(Customer).where(
            or_(
                Customer.ruc.ilike(like),
                Customer.legal_name.ilike(like),
                Customer.trade_name.ilike(like),
            )
        ).order_by(Customer.created_at.desc()).limit(LIMIT)
    )
    customers = [
        {"id": str(x.id), "label": x.trade_name or x.legal_name, "sub": x.ruc}
        for x in cust_rows
    ]

    sup_rows = await session.scalars(
        select(Supplier).where(Supplier.name.ilike(like)).order_by(Supplier.name).limit(LIMIT)
    )
    suppliers = [{"id": str(x.id), "label": x.name, "sub": x.country or ""} for x in sup_rows]

    return {
        "query": term,
        "cases": cases, "quotes": quotes, "customers": customers, "suppliers": suppliers,
        "total": len(cases) + len(quotes) + len(customers) + len(suppliers),
    }
