"""Schemas del módulo de almacenaje (bodega / depósito temporal)."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class WarehouseCreate(BaseModel):
    warehouse_name: str | None = None
    reference: str | None = None
    entry_date: date | None = None
    free_days: int | None = None
    rate_type: str = "PER_DAY"  # PER_DAY / PER_KG_DAY / FLAT
    daily_rate: float = 0
    chargeable_weight_kg: float | None = None
    currency: str = "USD"
    status: str = "IN_WAREHOUSE"


class WarehouseUpdate(BaseModel):
    warehouse_name: str | None = None
    reference: str | None = None
    entry_date: date | None = None
    free_days: int | None = None
    rate_type: str | None = None
    daily_rate: float | None = None
    chargeable_weight_kg: float | None = None
    withdrawal_date: date | None = None
    status: str | None = None
    currency: str | None = None


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    warehouse_name: str | None
    reference: str | None
    entry_date: date | None
    free_days: int | None
    rate_type: str
    daily_rate: float
    chargeable_weight_kg: float | None
    withdrawal_date: date | None
    status: str
    currency: str
    # Calculados
    last_free_day: date | None = None
    days_to_last_free_day: int | None = None
    days_overdue: int = 0
    estimated_storage: float = 0
    alarm: str = "OK"


class WarehouseSummary(BaseModel):
    items: list[WarehouseRead]
    money_at_risk: float
    max_alarm: str


class AtRiskStorage(BaseModel):
    case_id: uuid.UUID
    case_number: str
    reference: str | None
    warehouse_name: str | None
    alarm: str
    days_to_last_free_day: int | None
    estimated_storage: float
