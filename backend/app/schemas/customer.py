"""Schemas de Cliente, Contacto y Consentimiento."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.services.ruc import RUCValidationError, validate_ruc


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
    address: str | None = None
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


class CustomerCreate(CustomerBase):
    status: str = "LEAD"
    contacts: list[ContactCreate] = []


class CustomerUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    address: str | None = None
    email: EmailStr | None = None
    billing_data: dict | None = None
    notification_prefs: dict | None = None
    status: str | None = None


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
