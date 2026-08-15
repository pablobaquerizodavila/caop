"""Schemas del comprobante de retención."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RetentionLineIn(BaseModel):
    tax_type: str  # 1=Renta, 2=IVA
    codigo_retencion: str
    base_imponible: float
    percentage: float


class RetentionLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tax_type: str
    codigo_retencion: str
    base_imponible: float
    percentage: float
    value: float


class RetentionCreate(BaseModel):
    supplier_id: uuid.UUID | None = None
    subject_name: str
    subject_id: str
    subject_id_type: str = "04"
    period: str  # MM/AAAA
    doc_sustento_type: str = "01"
    doc_sustento_number: str  # 001-001-000000001
    doc_sustento_date: date
    lines: list[RetentionLineIn]


class RetentionAuthorize(BaseModel):
    scenario: str = "AUTHORIZE"


class RetentionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject_name: str
    subject_id: str
    subject_id_type: str
    period: str
    doc_sustento_number: str
    doc_sustento_date: date
    estab: str
    pto_emi: str
    secuencial: str
    access_key: str
    issue_date: date
    status: str
    signed: bool
    authorization_number: str | None
    authorized_at: datetime | None
    is_simulated: bool
    total_retained: float
    error: str | None
    lines: list[RetentionLineRead] = []
