"""Schemas de facturación electrónica (SRI)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EinvoiceAuthorizeRequest(BaseModel):
    scenario: str = "AUTHORIZE"  # AUTHORIZE / REJECT / UNAVAILABLE (simulador)


class CreditNoteCreate(BaseModel):
    amount: float | None = None  # si se omite, es nota de crédito total
    motivo: str = "Corrección"


class CreditNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    invoice_id: uuid.UUID
    document_type: str
    ambiente: str
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
    motivo: str
    subtotal: float
    tax_amount: float
    total: float
    error: str | None


class EinvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    settlement_id: uuid.UUID
    document_type: str
    ambiente: str
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
    subtotal: float
    tax_amount: float
    total: float
    error: str | None
