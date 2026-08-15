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


class RestrictionOut(BaseModel):
    tax_type: str = "RESTRICTION"  # placeholder para UI uniforme
    kind: str
    document: str | None = None
    authority: str | None = None
    requirement: str | None = None
    blocking: bool = True
    legal: str | None = None


class TariffCodeDetail(TariffCodeOut):
    taxes: list[TariffTaxOut] = []
    warnings: list[str] = []
    ancestors: list[TariffCodeOut] = []
    children: list[TariffCodeOut] = []
    restrictions: list[RestrictionOut] = []


# --- Base legal (#6) ---
class LegalInstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    number: str
    organism: str | None = None
    issued_at: date | None = None
    published_at: date | None = None
    effective_from: date | None = None
    registro_oficial: str | None = None
    supplement: str | None = None
    url: str | None = None


class LegalInstrumentCreate(BaseModel):
    kind: str
    number: str
    organism: str | None = None
    issued_at: date | None = None
    published_at: date | None = None
    effective_from: date | None = None
    registro_oficial: str | None = None
    supplement: str | None = None
    url: str | None = None
    notes: str | None = None


# --- Control previo / restricciones (#5) ---
class ControlAuthorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    kind: str | None = None


class ControlAuthorityCreate(BaseModel):
    code: str
    name: str
    kind: str | None = None


class ControlDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    authority_id: uuid.UUID | None = None
    description: str | None = None


class ControlDocumentCreate(BaseModel):
    code: str
    name: str
    authority_id: uuid.UUID | None = None
    description: str | None = None


class TariffRestrictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hs_prefix: str
    kind: str
    control_document_id: uuid.UUID | None = None
    authority_id: uuid.UUID | None = None
    legal_instrument_id: uuid.UUID | None = None
    requirement: str | None = None
    blocking: bool
    effective_from: date
    effective_to: date | None = None
    status: str
    verification_status: str


class TariffRestrictionCreate(BaseModel):
    hs_prefix: str
    kind: str = "CONTROL_PREVIO"
    control_document_id: uuid.UUID | None = None
    authority_id: uuid.UUID | None = None
    legal_instrument_id: uuid.UUID | None = None
    requirement: str | None = None
    blocking: bool = True
    effective_from: date
    effective_to: date | None = None
    notes: str | None = None


class TariffHistoryEntry(BaseModel):
    version: str | None
    status: str
    verification_status: str
    ad_valorem: Decimal | None
    effective_from: date
    effective_to: date | None
    legal_source: str | None


class TariffCalcItem(BaseModel):
    hs_code: str | None = None
    origin_country: str | None = None
    commercial_agreement: str | None = None
    quantity: Decimal = Decimal(1)
    invoice_value: Decimal = Field(..., ge=0)
    freight: Decimal = Decimal(0)
    insurance: Decimal = Decimal(0)
    description: str | None = None
    attributes: dict = {}  # tarifas condicionales, p. ej. {"CC": 2000}


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


class PreferenceScenarioOut(BaseModel):
    agreement_code: str
    agreement_name: str
    liberation_pct: float
    preferential_adval_pct: float
    requires_certificate: bool
    verified: bool
    total_taxes: float
    savings: float


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
    preference: PreferenceScenarioOut | None = None


# --- Acuerdos y preferencias (administración) ---
class TradeAgreementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    kind: str
    members: list[str] | None = None
    effective_from: date | None = None
    status: str


class TradeAgreementCreate(BaseModel):
    code: str
    name: str
    kind: str = "FTA"
    members: list[str] = []
    effective_from: date | None = None


class TariffPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agreement_id: uuid.UUID
    origin_country: str | None = None
    hs_prefix: str | None = None
    liberation_pct: Decimal
    preferential_rate: Decimal | None = None
    requires_certificate: bool
    effective_from: date
    effective_to: date | None = None
    status: str
    verification_status: str
    legal_source: str | None = None


class TariffPreferenceCreate(BaseModel):
    agreement_id: uuid.UUID
    origin_country: str | None = None
    hs_prefix: str | None = None
    liberation_pct: Decimal = Decimal(100)
    preferential_rate: Decimal | None = None
    requires_certificate: bool = True
    effective_from: date
    effective_to: date | None = None
    legal_source: str | None = None


class TariffTierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hs_prefix: str
    applies_to: str
    attribute: str
    description: str | None = None
    tiers: list
    specific_unit: str | None = None
    effective_from: date
    effective_to: date | None = None
    status: str
    verification_status: str
    legal_source: str | None = None


class TariffTierCreate(BaseModel):
    hs_prefix: str
    applies_to: str = "AD_VALOREM"
    attribute: str = "CC"
    description: str | None = None
    tiers: list = []
    specific_unit: str | None = None
    base_type: str = "EX_ADUANA"
    effective_from: date
    effective_to: date | None = None
    legal_source: str | None = None


class TradeRemedyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    hs_prefix: str
    origin_country: str | None = None
    exporter: str | None = None
    product: str | None = None
    method: str
    ad_valorem_pct: Decimal | None = None
    specific_rate: Decimal | None = None
    specific_unit: str | None = None
    effective_from: date
    effective_to: date | None = None
    status: str
    verification_status: str
    legal_source: str | None = None


class TradeRemedyCreate(BaseModel):
    kind: str  # ANTIDUMPING / SAFEGUARD / COMPENSATORY
    hs_prefix: str
    origin_country: str | None = None
    exporter: str | None = None
    product: str | None = None
    method: str = "AD_VALOREM"
    ad_valorem_pct: Decimal | None = None
    specific_rate: Decimal | None = None
    specific_unit: str | None = None
    effective_from: date
    effective_to: date | None = None
    legal_source: str | None = None


class PriceBandMeasureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hs_prefix: str
    product: str
    is_marker: bool
    status: str


class PriceBandMeasureCreate(BaseModel):
    hs_prefix: str
    product: str
    is_marker: bool = False


class PriceBandPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    measure_id: uuid.UUID
    period_start: date
    period_end: date
    reference_price: Decimal | None = None
    floor_price: Decimal | None = None
    ceiling_price: Decimal | None = None
    variable_method: str
    variable_value: Decimal
    specific_unit: str | None = None
    verification_status: str


class PriceBandPeriodCreate(BaseModel):
    period_start: date
    period_end: date
    reference_price: Decimal | None = None
    floor_price: Decimal | None = None
    ceiling_price: Decimal | None = None
    variable_method: str = "AD_VALOREM"
    variable_value: Decimal = Decimal(0)
    specific_unit: str | None = None
    legal_source: str | None = None


class IceMeasureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    hs_prefix: str
    description: str | None = None
    method: str
    ad_valorem_pct: Decimal | None = None
    specific_rate: Decimal | None = None
    specific_unit: str | None = None
    base_type: str
    effective_from: date
    effective_to: date | None = None
    status: str
    verification_status: str
    legal_source: str | None = None


class IceMeasureCreate(BaseModel):
    hs_prefix: str
    description: str | None = None
    method: str = "AD_VALOREM"
    ad_valorem_pct: Decimal | None = None
    specific_rate: Decimal | None = None
    specific_unit: str | None = None
    base_type: str = "EX_ADUANA"
    reference_price: Decimal | None = None
    effective_from: date
    effective_to: date | None = None
    legal_source: str | None = None


class TariffPreferenceUpdate(BaseModel):
    liberation_pct: Decimal | None = None
    preferential_rate: Decimal | None = None
    requires_certificate: bool | None = None
    hs_prefix: str | None = None
    origin_country: str | None = None
    effective_to: date | None = None
    status: str | None = None
    verification_status: str | None = None
    legal_source: str | None = None


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


class TariffChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    change_type: str
    hs_code: str | None = None
    old_value: str | None = None
    new_value: str | None = None


class SyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_code: str | None
    status: str
    found: int
    new_count: int
    detected: list | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class SyncStatusOut(BaseModel):
    active_version: TariffVersionOut | None
    total_codes: int
    total_active_rules: int
    last_import_at: datetime | None
    last_import_status: str | None
