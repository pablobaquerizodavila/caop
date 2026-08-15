"""Endpoints de Requisitos, Expedientes (CustomsCase) y Checklist."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.session import get_session
from app.models.checklist import ChecklistItem, Requirement
from app.models.quote import Quote
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.schemas.case import (
    CaseEventCreate,
    CaseEventRead,
    ChecklistItemRead,
    ChecklistItemUpdate,
    CustomsCaseDetail,
    CustomsCaseRead,
    RequirementCreate,
    RequirementRead,
    ShipmentRead,
)
from app.services.checklist import recompute_readiness
from app.services.requirement_seed import seed_requirement_defaults

router = APIRouter(tags=["cases"])


# ---------- Requisitos ----------
@router.post("/requirements", response_model=RequirementRead, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate, session: AsyncSession = Depends(get_session)
) -> Requirement:
    req = Requirement(**payload.model_dump())
    session.add(req)
    await session.flush()
    await session.refresh(req)
    return req


@router.get("/requirements", response_model=list[RequirementRead])
async def list_requirements(session: AsyncSession = Depends(get_session)) -> list[Requirement]:
    return list(await session.scalars(select(Requirement).order_by(Requirement.doc_type)))


@router.post("/requirements/seed-defaults")
async def seed_requirements(session: AsyncSession = Depends(get_session)) -> dict:
    created = await seed_requirement_defaults(session)
    return {"created": created}


# ---------- Shipments ----------
@router.get("/shipments", response_model=list[ShipmentRead])
async def list_shipments(
    session: AsyncSession = Depends(get_session),
    customer_id: uuid.UUID | None = Query(None),
) -> list[Shipment]:
    stmt = select(Shipment).order_by(Shipment.created_at.desc())
    if customer_id:
        stmt = stmt.where(Shipment.customer_id == customer_id)
    return list(await session.scalars(stmt))


# ---------- Expedientes ----------
async def _load_case(session: AsyncSession, case_id: uuid.UUID) -> CustomsCase:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    return case


async def _source_quote_map(session: AsyncSession, case_ids: list[uuid.UUID]) -> dict:
    """case_id -> (quote_id, quote_number) de la cotización de origen."""
    if not case_ids:
        return {}
    rows = await session.execute(
        select(CustomsCase.id, Shipment.source_quote_id, Quote.quote_number)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .join(Quote, Shipment.source_quote_id == Quote.id, isouter=True)
        .where(CustomsCase.id.in_(case_ids))
    )
    return {cid: (qid, qnum) for cid, qid, qnum in rows.all()}


async def _detail(session: AsyncSession, case: CustomsCase) -> CustomsCaseDetail:
    checklist = list(
        await session.scalars(
            select(ChecklistItem).where(ChecklistItem.customs_case_id == case.id)
        )
    )
    events = list(
        await session.scalars(
            select(CaseEvent).where(CaseEvent.customs_case_id == case.id).order_by(CaseEvent.timestamp)
        )
    )
    slas = list(
        await session.scalars(
            select(SLAInstance).where(
                SLAInstance.entity_type == "CUSTOMS_CASE", SLAInstance.entity_id == case.id
            )
        )
    )
    detail = CustomsCaseDetail.model_validate(case)
    detail.checklist = [ChecklistItemRead.model_validate(i) for i in checklist]
    detail.events = [CaseEventRead.model_validate(e) for e in events]
    detail.sla = slas  # type: ignore[assignment]
    mapping = await _source_quote_map(session, [case.id])
    if case.id in mapping:
        detail.source_quote_id, detail.source_quote_number = mapping[case.id]
    return detail


@router.get("/cases", response_model=list[CustomsCaseRead])
async def list_cases(
    session: AsyncSession = Depends(get_session),
    state: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[CustomsCase]:
    stmt = select(CustomsCase).order_by(CustomsCase.created_at.desc())
    if state:
        stmt = stmt.where(CustomsCase.current_state == state)
    cases = list(await session.scalars(stmt.limit(limit)))
    mapping = await _source_quote_map(session, [c.id for c in cases])
    out = []
    for c in cases:
        r = CustomsCaseRead.model_validate(c)
        if c.id in mapping:
            r.source_quote_id, r.source_quote_number = mapping[c.id]
        out.append(r)
    return out


@router.get("/cases/{case_id}", response_model=CustomsCaseDetail)
async def get_case(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CustomsCaseDetail:
    case = await _load_case(session, case_id)
    return await _detail(session, case)


@router.get("/cases/{case_id}/checklist", response_model=list[ChecklistItemRead])
async def get_checklist(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ChecklistItem]:
    await _load_case(session, case_id)
    return list(
        await session.scalars(
            select(ChecklistItem).where(ChecklistItem.customs_case_id == case_id)
        )
    )


@router.patch("/cases/{case_id}/checklist/{item_id}", response_model=CustomsCaseDetail)
async def update_checklist_item(
    case_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ChecklistItemUpdate,
    session: AsyncSession = Depends(get_session),
) -> CustomsCaseDetail:
    case = await _load_case(session, case_id)
    item = await session.get(ChecklistItem, item_id)
    if item is None or item.customs_case_id != case_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem de checklist no encontrado")
    if payload.status is not None:
        item.status = payload.status
    if payload.document_id is not None:
        item.document_id = payload.document_id
        if payload.status is None:
            item.status = "COMPLETE"
    await session.flush()
    await recompute_readiness(session, case)
    session.add(
        CaseEvent(
            customs_case_id=case.id,
            event_type="CHECKLIST_UPDATED",
            event_source="USER",
            normalized_payload={"doc_type": item.doc_type, "status": item.status},
        )
    )
    await session.flush()
    return await _detail(session, case)


@router.post("/cases/{case_id}/events", response_model=CaseEventRead, status_code=201)
async def add_event(
    case_id: uuid.UUID, payload: CaseEventCreate, session: AsyncSession = Depends(get_session)
) -> CaseEvent:
    await _load_case(session, case_id)
    event = CaseEvent(customs_case_id=case_id, **payload.model_dump())
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


# ---------- Reconciliación tributaria (estimado vs. liquidación SENAE) ----------
class ReconciliationInput(BaseModel):
    actual: dict[str, float]  # tax_type -> monto liquidado real
    reason: str | None = None


@router.get("/cases/{case_id}/reconciliation")
async def get_case_reconciliation(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    from app.services.reconciliation import get_reconciliation
    case = await _load_case(session, case_id)
    return await get_reconciliation(session, case)


@router.put("/cases/{case_id}/reconciliation")
async def set_case_reconciliation(
    case_id: uuid.UUID,
    payload: ReconciliationInput,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    from app.services.reconciliation import set_actual
    case = await _load_case(session, case_id)
    return await set_actual(
        session, case, payload.actual, payload.reason,
        principal.username or principal.subject,
    )


@router.get("/reconciliations/summary")
async def reconciliation_summary(session: AsyncSession = Depends(get_session)) -> dict:
    from app.services.reconciliation import summary
    return await summary(session)
