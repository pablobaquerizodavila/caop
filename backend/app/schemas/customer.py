"""Schemas de Cliente, Contacto y Consentimiento."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.services.ruc import RUCValidationError, validate_ruc

ENTITY_TYPES = {"NATURAL", "COMPANY"}


class ContactBase(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    role: str | None = None
    is_primary: bool = False


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID


class CustomerBase(BaseModel):
    ruc: str
    legal_name: str
    trade_name: str | None = None
    entity_type: str = "NATURAL"
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    second_last_name: str | None = None
    country: str = "Ecuador"
    province: str | None = None
    city: str | None = None
    address: str | None = None
    dispatch_same_as_address: bool = True
    dispatch_country: str | None = None
    dispatch_province: str | None = None
    dispatch_city: str | None = None
    dispatch_address: str | None = None
    legal_rep_name: str | None = None
    legal_rep_id: str | None = None
    email: EmailStr | None = None
    billing_data: dict | None = None
    notification_prefs: dict | None = None

    @field_validator("ruc")
    @classmethod
    def _validate_ruc(cls, v: str) -> str:
        try:
            return validate_ruc(v)
        except RUCValidationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("entity_type")
    @classmethod
    def _validate_entity_type(cls, v: str) -> str:
        v = (v or "NATURAL").upper()
        if v not in ENTITY_TYPES:
            raise ValueError(f"entity_type inválido: {v}. Use uno de {sorted(ENTITY_TYPES)}")
        return v

    @model_validator(mode="after")
    def _require_legal_rep_for_company(self) -> "CustomerBase":
        if self.entity_type == "COMPANY" and not (self.legal_rep_name or "").strip():
            raise ValueError("Una empresa requiere el nombre del representante legal")
        return self

    @model_validator(mode="after")
    def _sync_dispatch_address(self) -> "CustomerBase":
        # Si la dirección de despacho es la misma que la física, se copia.
        if self.dispatch_same_as_address:
            self.dispatch_country = self.country
            self.dispatch_province = self.province
            self.dispatch_city = self.city
            self.dispatch_address = self.address
        return self


class CustomerCreate(CustomerBase):
    status: str = "LEAD"
    contacts: list[ContactCreate] = []


class CustomerUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    entity_type: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    second_last_name: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    dispatch_same_as_address: bool | None = None
    dispatch_country: str | None = None
    dispatch_province: str | None = None
    dispatch_city: str | None = None
    dispatch_address: str | None = None
    legal_rep_name: str | None = None
    legal_rep_id: str | None = None
    email: EmailStr | None = None
    billing_data: dict | None = None
    notification_prefs: dict | None = None
    status: str | None = None

    @field_validator("entity_type")
    @classmethod
    def _validate_entity_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.upper()
        if v not in ENTITY_TYPES:
            raise ValueError(f"entity_type inválido: {v}")
        return v


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    contacts: list[ContactRead] = []
    created_at: datetime


class ConsentCreate(BaseModel):
    contact_id: uuid.UUID | None = None
    purpose: str
    legal_basis: str
    granted_at: datetime | None = None
    evidence: dict | None = None
    notes: str | None = None


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID
    contact_id: uuid.UUID | None
    purpose: str
    legal_basis: str
    granted_at: datetime | None
    revoked_at: datetime | None
    evidence: dict | None
