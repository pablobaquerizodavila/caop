"""Endpoints Ocean/Air: transporte, contenedores y demurrage."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.schemas.ocean import (
    AtRiskContainer,
    ContainerCreate,
    ContainerRead,
    ContainerUpdate,
    DemurrageSummary,
    TransportRead,
    TransportUpdate,
)
from app.services.demurrage import compute

router = APIRouter(tags=["ocean"])

ALARM_ORDER = {"OK": 0, "WARN": 1, "AT_RISK": 2, "CRITICAL": 3}


async def _shipment_for_case(session: AsyncSession, case_id: uuid.UUID) -> Shipment:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    shipment = await session.get(Shipment, case.shipment_id)
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Embarque no encontrado")
    return shipment


def _container_read(c: Container, today: date) -> ContainerRead:
    r = ContainerRead.model_validate(c)
    d = compute(c, today)
    r.last_free_day = d.last_free_day
    r.days_to_last_free_day = d.days_to_last_free_day
    r.days_overdue = d.days_overdue
    r.estimated_demurrage = float(d.estimated_demurrage)
    r.alarm = d.alarm
    return r


@router.patch("/cases/{case_id}/transport", response_model=TransportRead)
async def update_transport(
    case_id: uuid.UUID, payload: TransportUpdate, session: AsyncSession = Depends(get_session)
) -> Shipment:
    shipment = await _shipment_for_case(session, case_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)
    await session.flush()
    return shipment


@router.get("/cases/{case_id}/transport", response_model=TransportRead)
async def get_transport(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Shipment:
    return await _shipment_for_case(session, case_id)


@router.post("/cases/{case_id}/containers", response_model=ContainerRead, status_code=201)
async def add_container(
    case_id: uuid.UUID, payload: ContainerCreate, session: AsyncSession = Depends(get_session)
) -> ContainerRead:
    shipment = await _shipment_for_case(session, case_id)
    container = Container(shipment_id=shipment.id, **payload.model_dump())
    session.add(container)
    session.add(
        CaseEvent(
            customs_case_id=case_id, event_type="CONTAINER_ADDED", event_source="USER",
            normalized_payload={"container": payload.container_number},
        )
    )
    await session.flush()
    return _container_read(container, date.today())


@router.get("/cases/{case_id}/containers", response_model=list[ContainerRead])
async def list_containers(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ContainerRead]:
    shipment = await _shipment_for_case(session, case_id)
    today = date.today()
    rows = await session.scalars(
        select(Container).where(Container.shipment_id == shipment.id).order_by(Container.container_number)
    )
    return [_container_read(c, today) for c in rows]


@router.patch("/containers/{container_id}", response_model=ContainerRead)
async def update_container(
    container_id: uuid.UUID, payload: ContainerUpdate, session: AsyncSession = Depends(get_session)
) -> ContainerRead:
    container = await session.get(Container, container_id)
    if container is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(container, field, value)
    await session.flush()
    return _container_read(container, date.today())


@router.get("/cases/{case_id}/demurrage", response_model=DemurrageSummary)
async def demurrage_summary(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> DemurrageSummary:
    shipment = await _shipment_for_case(session, case_id)
    today = date.today()
    rows = list(
        await session.scalars(select(Container).where(Container.shipment_id == shipment.id))
    )
    reads = [_container_read(c, today) for c in rows]
    money = sum((r.estimated_demurrage for r in reads if r.status != "EMPTY_RETURNED"), 0.0)
    max_alarm = "OK"
    for r in reads:
        if ALARM_ORDER[r.alarm] > ALARM_ORDER[max_alarm]:
            max_alarm = r.alarm
    return DemurrageSummary(containers=reads, money_at_risk=round(money, 2), max_alarm=max_alarm)


@router.get("/ocean/demurrage-at-risk", response_model=list[AtRiskContainer])
async def demurrage_at_risk(session: AsyncSession = Depends(get_session)) -> list[AtRiskContainer]:
    """Contenedores en riesgo de demurrage en toda la operación (para la Torre de Control)."""
    today = date.today()
    rows = await session.execute(
        select(Container, CustomsCase.id, CustomsCase.case_number)
        .join(Shipment, Container.shipment_id == Shipment.id)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
    )
    out: list[AtRiskContainer] = []
    for container, case_id, case_number in rows.all():
        d = compute(container, today)
        if d.at_risk:
            out.append(
                AtRiskContainer(
                    case_id=case_id, case_number=case_number,
                    container_number=container.container_number, alarm=d.alarm,
                    days_to_last_free_day=d.days_to_last_free_day,
                    estimated_demurrage=float(d.estimated_demurrage),
                )
            )
    out.sort(key=lambda a: ALARM_ORDER[a.alarm], reverse=True)
    return out
