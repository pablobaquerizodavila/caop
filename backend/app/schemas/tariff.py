"""Schemas del maestro arancelario (API /tariff/*)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TariffCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    code_normalized: str
    level: int
    description: str
    full_description: str | None = None
    parent_code: str | None = None
    physical_unit: str | None = None
    ad_valorem: Decimal | None = None
    status: str
    effective_from: date
    effective_to: date | None = None


class TariffTaxOut(BaseModel):
    tax_type: str
    percentage: Decimal | None = None
    verified: bool
    legal_source: str | None = None


class TariffCodeDetail(TariffCodeOut):
    taxes: list[TariffTaxOut] = []
    warnings: list[str] = []


class TariffCalcItem(BaseModel):
    hs_code: str | None = None
    origin_country: str | None = None
    commercial_agreement: str | None = None
    quantity: Decimal = Decimal(1)
    invoice_value: Decimal = Field(..., ge=0)
    freight: Decimal = Decimal(0)
    insurance: Decimal = Decimal(0)
    description: str | None = None


class TariffCalcRequest(BaseModel):
    calculation_date: date | None = None
    currency: str = "USD"
    items: list[TariffCalcItem]


class TariffCalcComponent(BaseModel):
    tax_type: str
    base_amount: float
    rate_applied: float | None
    amount: float
    verified: bool


class TariffCalcItemOut(BaseModel):
    description: str | None
    hs_code: str | None
    hs_validation: str
    cif_value: float
    components: list[TariffCalcComponent]
    total_taxes: float
    complete: bool
    warnings: list[str]
    missing_information: list[str]


class TariffCalcResponse(BaseModel):
    calculation_date: date
    currency: str
    data_version: str | None
    items: list[TariffCalcItemOut]
    total_cif: float
    total_taxes: float
    complete: bool
    disclaimer: str


class TariffVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    number: str
    status: str
    codes_count: int
    rules_count: int
    published_at: datetime | None = None
    created_at: datetime


class SyncStatusOut(BaseModel):
    active_version: TariffVersionOut | None
    total_codes: int
    total_active_rules: int
    last_import_at: datetime | None
    last_import_status: str | None
