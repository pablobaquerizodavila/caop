"""Schemas de Cotización. Vista INTERNA (con margen) y PÚBLICA (sin rentabilidad)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Entrada ----------
class QuoteItemCreate(BaseModel):
    description: str | None = None
    model: str | None = None
    hs_code: str | None = None
    hs_status: str = "PRELIMINARY"
    origin_country: str | None = None
    commercial_agreement: str | None = None
    quantity: Decimal = Decimal(1)
    unit: str | None = None
    unit_price: Decimal = Decimal(0)
    line_value: Decimal | None = None  # si falta => unit_price * quantity
    weight: Decimal | None = None
    freight_alloc: Decimal | None = None
    insurance_alloc: Decimal | None = None
    attributes: dict | None = None  # tarifas condicionales, p. ej. {"CC": 2000}


class CostLineCreate(BaseModel):
    category: str
    description: str | None = None
    estimated_amount: Decimal = Decimal(0)
    contingency_pct: Decimal = Decimal(0)
    quoted_amount: Decimal | None = None  # si falta => estimated * (1 + contingency%)
    confidence: str = "MEDIUM"
    is_included: bool = True


class QuoteCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    transport_mode: str | None = None
    load_type: str | None = None
    incoterm: str | None = None
    origin_country: str | None = None
    currency: str = "USD"
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    calculation_date: date | None = None
    expected_import_date: date | None = None
    valid_until: date | None = None
    notes: str | None = None
    # Flete/seguro a nivel cabecera para prorratear por valor de línea (opcional):
    total_freight: Decimal | None = None
    total_insurance: Decimal | None = None
    items: list[QuoteItemCreate] = Field(default_factory=list)
    cost_lines: list[CostLineCreate] = Field(default_factory=list)


class StatusUpdate(BaseModel):
    status: str
    channel: str | None = None
    meta: dict | None = None


class LinkCustomer(BaseModel):
    customer_id: uuid.UUID


class LinkResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID | None


# ---------- Salida ----------
class QuoteItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    line_no: int
    description: str | None
    model: str | None = None
    hs_code: str | None
    hs_status: str
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    line_value: Decimal
    freight_alloc: Decimal | None = None
    insurance_alloc: Decimal | None = None
    cif_value: Decimal
    taxes_total: Decimal
    tax_breakdown: list | None
    hs_validation: str = "UNKNOWN"
    tax_complete: bool = True
    tax_warnings: list | None = None
    tax_data_version: str | None = None
    preference: dict | None = None
    origin_country: str | None = None


class CostLineReadInternal(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: str
    description: str | None
    estimated_amount: Decimal
    contingency_pct: Decimal
    quoted_amount: Decimal
    confidence: str
    is_included: bool


class CostLineReadPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: str
    description: str | None
    quoted_amount: Decimal
    confidence: str
    is_included: bool


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    channel: str | None
    occurred_at: datetime


class _QuoteCommon(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    quote_number: str
    version: int
    status: str
    customer_id: uuid.UUID | None
    transport_mode: str | None
    load_type: str | None
    incoterm: str | None
    origin_country: str | None
    currency: str
    calculation_date: date
    expected_import_date: date | None
    total_units: Decimal
    total_cif: Decimal
    total_taxes: Decimal
    customer_price_total: Decimal
    landed_cost_total: Decimal
    landed_cost_per_unit: Decimal
    confidence: Decimal | None
    valid_until: date | None
    # Correlación con el expediente (si la cotización ya se convirtió).
    case_id: uuid.UUID | None = None
    case_number: str | None = None
    items: list[QuoteItemRead]


class QuoteReadInternal(_QuoteCommon):
    internal_cost_total: Decimal
    margin_amount: Decimal
    margin_pct: Decimal
    cost_lines: list[CostLineReadInternal]
    status_history: list[StatusHistoryRead]


class QuoteReadPublic(_QuoteCommon):
    cost_lines: list[CostLineReadPublic]
    disclaimer: str = ""
