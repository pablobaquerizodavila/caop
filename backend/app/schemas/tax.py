"""Schemas del Tax Rule Engine y del simulador."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaxRuleCreate(BaseModel):
    tax_type: str
    hs_code: str | None = None
    origin_country: str | None = None
    commercial_agreement: str | None = None
    calculation_method: str = "AD_VALOREM_PCT"
    percentage: Decimal | None = None
    specific_rate: Decimal | None = None
    base_formula: str = "CIF"
    depends_on: list[str] = []
    exception: dict | None = None
    legal_source: str | None = None
    effective_from: date
    effective_to: date | None = None
    version: int = 1
    status: str = "ACTIVE"
    notes: str | None = None


class TaxRuleRead(TaxRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    last_verified_at: datetime | None = None


class TaxSimItem(BaseModel):
    description: str | None = None
    hs_code: str | None = None
    origin_country: str | None = None
    commercial_agreement: str | None = None
    quantity: Decimal = Decimal(1)
    invoice_value: Decimal = Field(..., ge=0)
    freight: Decimal = Decimal(0)
    insurance: Decimal = Decimal(0)


class TaxSimRequest(BaseModel):
    calculation_date: date | None = None
    currency: str = "USD"
    items: list[TaxSimItem]


class TaxComponentOut(BaseModel):
    tax_type: str
    base_amount: float
    rate_applied: float | None
    amount: float
    sequence: int
    legal_source: str | None
    verified: bool


class TaxItemOut(BaseModel):
    description: str | None
    hs_code: str | None
    cif_value: float
    components: list[TaxComponentOut]
    total_taxes: float


class TaxSimResponse(BaseModel):
    calculation_date: date
    currency: str
    items: list[TaxItemOut]
    total_cif: float
    total_taxes: float
    disclaimer: str
