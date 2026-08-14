"""Schemas de expediente: shipment, customs case, checklist, requisitos, SLA, eventos."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RequirementCreate(BaseModel):
    doc_type: str
    category: str = "SUPPORT"
    applies_when: dict | None = None
    blocking: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    status: str = "ACTIVE"


class RequirementRead(RequirementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    doc_type: str
    category: str
    blocking: bool
    status: str
    document_id: uuid.UUID | None
    due_at: datetime | None


class ChecklistItemUpdate(BaseModel):
    status: str | None = None
    document_id: uuid.UUID | None = None


class CaseEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_type: str
    event_source: str
    timestamp: datetime
    normalized_payload: dict | None


class CaseEventCreate(BaseModel):
    event_type: str
    event_source: str = "USER"
    location: str | None = None
    normalized_payload: dict | None = None


class SLAInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    milestone: str
    start_time: datetime
    deadline: datetime | None
    status: str
    escalation_level: int


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    source_quote_id: uuid.UUID | None
    transport_mode: str | None
    incoterm: str | None
    origin_country: str | None
    status: str


class CustomsCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    shipment_id: uuid.UUID
    case_number: str
    customs_regime: str
    current_state: str
    next_expected_event: str | None
    risk_level: str
    customs_readiness_score: Decimal
    blocker: str | None
    # Correlación con la cotización de origen.
    source_quote_id: uuid.UUID | None = None
    source_quote_number: str | None = None


class CustomsCaseDetail(CustomsCaseRead):
    checklist: list[ChecklistItemRead] = []
    events: list[CaseEventRead] = []
    sla: list[SLAInstanceRead] = []
