"""Schemas de certificados de origen."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class CertificateCreate(BaseModel):
    cert_type: str = "ORIGEN"
    number: str | None = None
    issuing_country: str | None = None
    organism: str | None = None
    agreement_id: uuid.UUID | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    notes: str | None = None


class CertificateValidate(BaseModel):
    validation_status: str  # VALID / REJECTED / PENDING
    notes: str | None = None


class CertificateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    quote_id: uuid.UUID | None
    agreement_id: uuid.UUID | None
    cert_type: str
    number: str | None
    issuing_country: str | None
    organism: str | None
    issue_date: date | None
    valid_until: date | None
    validation_status: str
    notes: str | None
