"""Schemas de VUE — documentos de control previo."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class VuePermitCreate(BaseModel):
    entity: str
    document_code: str
    description: str | None = None
    blocking: bool = True
    permit_number: str | None = None
    notes: str | None = None


class VuePermitUpdate(BaseModel):
    status: str | None = None
    permit_number: str | None = None
    issued_at: date | None = None
    valid_until: date | None = None
    blocking: bool | None = None
    notes: str | None = None


class VuePermitRequest(BaseModel):
    scenario: str = "APPROVE"  # APPROVE / REJECT / PENDING / UNAVAILABLE (simulador)


class VuePermitExempt(BaseModel):
    reason: str | None = None


class VuePermitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity: str
    document_code: str
    description: str | None
    permit_number: str | None
    status: str
    blocking: bool
    external_ref: str | None
    issued_at: date | None
    valid_until: date | None
    error_description: str | None
    notes: str | None
    satisfied: bool = False


class VueCatalogEntry(BaseModel):
    entity: str
    document_code: str
    description: str
