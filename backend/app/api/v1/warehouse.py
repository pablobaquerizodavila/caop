"""Endpoints de almacenaje (bodega / depósito temporal) — carga aérea y consolidada."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.models.warehouse import WarehouseStorage
from app.models.warehouse_tariff import WarehouseTariff
from app.schemas.warehouse import (
    AtRiskStorage,
    WarehouseCreate,
    WarehouseRead,
    WarehouseSummary,
    WarehouseTariffCreate,
    WarehouseTariffRead,
    WarehouseTariffUpdate,
    WarehouseUpdate,
)
from app.services.warehouse import compute

router = APIRouter(tags=["warehouse"])

ALARM_ORDER = {"OK": 0, "WARN": 1, "AT_RISK": 2, "CRITICAL": 3}


async def _shipment_for_case(session: AsyncSession, case_id: uuid.UUID) -> Shipment:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    shipment = await session.get(Shipment, case.shipment_id)
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Embarque no encontrado")
    return shipment


def _read(s: WarehouseStorage, today: date) -> WarehouseRead:
    r = WarehouseRead.model_validate(s)
    d = compute(s, today)
    r.last_free_day = d.last_free_day
    r.days_to_last_free_day = d.days_to_last_free_day
    r.days_overdue = d.days_overdue
    r.estimated_storage = float(d.estimated_storage)
    r.alarm = d.alarm
    return r


@router.get("/cases/{case_id}/warehouse", response_model=WarehouseSummary)
async def list_storage(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> WarehouseSummary:
    shipment = await _shipment_for_case(session, case_id)
    today = date.today()
    rows = list(
        await session.scalars(
            select(WarehouseStorage)
            .where(WarehouseStorage.shipment_id == shipment.id)
            .order_by(WarehouseStorage.created_at)
        )
    )
    reads = [_read(s, today) for s in rows]
    money = sum((r.estimated_storage for r in reads if r.status != "WITHDRAWN"), 0.0)
    max_alarm = "OK"
    for r in reads:
        if ALARM_ORDER[r.alarm] > ALARM_ORDER[max_alarm]:
            max_alarm = r.alarm
    return WarehouseSummary(items=reads, money_at_risk=round(money, 2), max_alarm=max_alarm)


@router.post("/cases/{case_id}/warehouse", response_model=WarehouseRead, status_code=201)
async def add_storage(
    case_id: uuid.UUID, payload: WarehouseCreate, session: AsyncSession = Depends(get_session)
) -> WarehouseRead:
    shipment = await _shipment_for_case(session, case_id)
    storage = WarehouseStorage(shipment_id=shipment.id, **payload.model_dump())
    session.add(storage)
    session.add(
        CaseEvent(
            customs_case_id=case_id, event_type="WAREHOUSE_ENTRY", event_source="USER",
            normalized_payload={"warehouse": payload.warehouse_name, "reference": payload.reference},
        )
    )
    await session.flush()
    return _read(storage, date.today())


@router.patch("/warehouse/{storage_id}", response_model=WarehouseRead)
async def update_storage(
    storage_id: uuid.UUID, payload: WarehouseUpdate, session: AsyncSession = Depends(get_session)
) -> WarehouseRead:
    storage = await session.get(WarehouseStorage, storage_id)
    if storage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de almacenaje no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(storage, field, value)
    await session.flush()
    return _read(storage, date.today())


@router.delete("/warehouse/{storage_id}", status_code=204)
async def delete_storage(
    storage_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    storage = await session.get(WarehouseStorage, storage_id)
    if storage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de almacenaje no encontrado")
    await session.delete(storage)
    await session.flush()


# ---------- Tarifario por depósito ----------
@router.get("/warehouse/tariffs", response_model=list[WarehouseTariffRead])
async def list_tariffs(session: AsyncSession = Depends(get_session)) -> list[WarehouseTariff]:
    return list(
        await session.scalars(select(WarehouseTariff).order_by(WarehouseTariff.warehouse_name))
    )


@router.post("/warehouse/tariffs", response_model=WarehouseTariffRead, status_code=201)
async def create_tariff(
    payload: WarehouseTariffCreate, session: AsyncSession = Depends(get_session)
) -> WarehouseTariff:
    tariff = WarehouseTariff(**payload.model_dump())
    session.add(tariff)
    await session.flush()
    return tariff


@router.patch("/warehouse/tariffs/{tariff_id}", response_model=WarehouseTariffRead)
async def update_tariff(
    tariff_id: uuid.UUID, payload: WarehouseTariffUpdate, session: AsyncSession = Depends(get_session)
) -> WarehouseTariff:
    tariff = await session.get(WarehouseTariff, tariff_id)
    if tariff is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarifa no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tariff, field, value)
    await session.flush()
    return tariff


@router.delete("/warehouse/tariffs/{tariff_id}", status_code=204)
async def delete_tariff(
    tariff_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    tariff = await session.get(WarehouseTariff, tariff_id)
    if tariff is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarifa no encontrada")
    await session.delete(tariff)
    await session.flush()


@router.get("/warehouse/at-risk", response_model=list[AtRiskStorage])
async def storage_at_risk(session: AsyncSession = Depends(get_session)) -> list[AtRiskStorage]:
    """Almacenaje en riesgo en toda la operación (para la Torre de Control)."""
    today = date.today()
    rows = await session.execute(
        select(WarehouseStorage, CustomsCase.id, CustomsCase.case_number)
        .join(Shipment, WarehouseStorage.shipment_id == Shipment.id)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
    )
    out: list[AtRiskStorage] = []
    for storage, case_id, case_number in rows.all():
        d = compute(storage, today)
        if d.at_risk and storage.status != "WITHDRAWN":
            out.append(
                AtRiskStorage(
                    case_id=case_id, case_number=case_number,
                    reference=storage.reference, warehouse_name=storage.warehouse_name,
                    alarm=d.alarm, days_to_last_free_day=d.days_to_last_free_day,
                    estimated_storage=float(d.estimated_storage),
                )
            )
    out.sort(key=lambda a: ALARM_ORDER[a.alarm], reverse=True)
    return out
