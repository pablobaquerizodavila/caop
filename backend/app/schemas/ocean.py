"""Schemas del módulo Ocean/Air: transporte y contenedores/demurrage."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class TransportUpdate(BaseModel):
    load_type: str | None = None
    carrier: str | None = None
    mbl_number: str | None = None
    hbl_number: str | None = None
    mawb_number: str | None = None
    hawb_number: str | None = None
    vessel: str | None = None
    voyage: str | None = None
    flight_number: str | None = None
    pol: str | None = None
    pod: str | None = None
    etd: date | None = None
    eta: date | None = None
    ata: date | None = None


class TransportRead(TransportUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    transport_mode: str | None = None
    incoterm: str | None = None
    origin_country: str | None = None


class ContainerCreate(BaseModel):
    container_number: str
    iso_type: str | None = None
    size: str | None = None
    seal: str | None = None
    status: str = "IN_TRANSIT"
    arrival_date: date | None = None
    free_days: int | None = None
    daily_rate: float = 0


class ContainerUpdate(BaseModel):
    status: str | None = None
    arrival_date: date | None = None
    free_days: int | None = None
    daily_rate: float | None = None
    gate_out_date: date | None = None
    empty_return_date: date | None = None


class ContainerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    container_number: str
    iso_type: str | None
    size: str | None
    seal: str | None
    status: str
    arrival_date: date | None
    free_days: int | None
    daily_rate: float
    gate_out_date: date | None
    empty_return_date: date | None
    # Calculados
    last_free_day: date | None = None
    days_to_last_free_day: int | None = None
    days_overdue: int = 0
    estimated_demurrage: float = 0
    alarm: str = "OK"


class DemurrageSummary(BaseModel):
    containers: list[ContainerRead]
    money_at_risk: float
    max_alarm: str


class AtRiskContainer(BaseModel):
    case_id: uuid.UUID
    case_number: str
    container_number: str
    alarm: str
    days_to_last_free_day: int | None
    estimated_demurrage: float
