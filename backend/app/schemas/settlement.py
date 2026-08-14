"""Schemas de liquidación al cliente."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SettlementLineCreate(BaseModel):
    kind: str = "DISBURSEMENT"  # FEE / DISBURSEMENT
    category: str = "OTRO"
    description: str | None = None
    amount: float = 0
    taxable: bool = False
    sort_no: int = 0


class SettlementLineUpdate(BaseModel):
    kind: str | None = None
    category: str | None = None
    description: str | None = None
    amount: float | None = None
    taxable: bool | None = None
    sort_no: int | None = None


class SettlementLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    category: str
    description: str | None
    amount: float
    taxable: bool
    sort_no: int


class SettlementUpdate(BaseModel):
    currency: str | None = None
    iva_rate: float | None = None
    notes: str | None = None
    due_date: date | None = None


class PaymentCreate(BaseModel):
    amount: float
    paid_at: date
    method: str = "TRANSFER"
    reference: str | None = None
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    amount: float
    paid_at: date
    method: str
    reference: str | None
    notes: str | None


class PaymentsView(BaseModel):
    payments: list[PaymentRead]
    total: float
    paid: float
    balance: float
    status: str  # PENDING / PARTIAL / PAID


class SettlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    settlement_number: str
    currency: str
    status: str
    iva_rate: float
    subtotal_fees: float
    subtotal_disbursements: float
    tax_amount: float
    total: float
    notes: str | None
    issued_at: datetime | None
    due_date: date | None = None
    lines: list[SettlementLineRead] = []
