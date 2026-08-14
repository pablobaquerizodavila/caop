"""Portal del cliente: resuelve el cliente por la identidad autenticada y expone
sólo SUS datos (expedientes, cotizaciones, liquidaciones), en modo lectura.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.models.customer import Customer
from app.models.quote import Quote
from app.models.shipment import CustomsCase, Shipment
from app.services import tracking


async def resolve_customer(session: AsyncSession, principal: Principal) -> Customer | None:
    """Vincula la cuenta autenticada con un Customer por email (case-insensitive)."""
    if not principal.email:
        return None
    return await session.scalar(
        select(Customer).where(func.lower(Customer.email) == principal.email.lower())
    )


async def count_cases(session: AsyncSession, customer_id) -> int:
    return int(
        await session.scalar(
            select(func.count(CustomsCase.id))
            .select_from(CustomsCase)
            .join(Shipment, CustomsCase.shipment_id == Shipment.id)
            .where(Shipment.customer_id == customer_id)
        )
        or 0
    )


async def count_quotes(session: AsyncSession, customer_id) -> int:
    return int(
        await session.scalar(
            select(func.count(Quote.id)).where(Quote.customer_id == customer_id)
        )
        or 0
    )


async def list_cases(session: AsyncSession, customer_id) -> list[dict]:
    rows = await session.execute(
        select(CustomsCase, Shipment.transport_mode, Shipment.origin_country)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .where(Shipment.customer_id == customer_id)
        .order_by(CustomsCase.created_at.desc())
    )
    out: list[dict] = []
    for case, mode, origin in rows.all():
        out.append({
            "id": case.id,
            "case_number": case.case_number,
            "status_label": tracking._STATUS_LABEL.get(case.current_state, case.current_state),
            "status_sem": tracking._STATUS_SEM.get(case.current_state, "warn"),
            "transport_mode": mode,
            "origin_country": origin,
            "created_at": case.created_at,
        })
    return out


async def list_quotes(session: AsyncSession, customer_id) -> list[Quote]:
    return list(
        await session.scalars(
            select(Quote).where(Quote.customer_id == customer_id).order_by(Quote.created_at.desc())
        )
    )


async def owned_case(session: AsyncSession, customer_id, case_id) -> CustomsCase | None:
    """Devuelve el expediente sólo si pertenece al cliente (evita fuga de datos)."""
    case = await session.get(CustomsCase, case_id)
    if case is None:
        return None
    shipment = await session.get(Shipment, case.shipment_id)
    if shipment is None or shipment.customer_id != customer_id:
        return None
    return case
