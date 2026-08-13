"""Schemas de Documento y versiones."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: int
    sha256: str
    size: int
    content_type: str | None
    filename: str
    issued_date: date | None
    expiry_date: date | None
    created_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID | None
    doc_type: str
    source: str
    versions: list[DocumentVersionRead] = []


class PresignedUrl(BaseModel):
    url: str
    expires_seconds: int
