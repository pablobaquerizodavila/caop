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


class DocumentExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field_name: str
    extracted_value: str | None
    verified_value: str | None
    confidence_score: float | None
    source_page: int | None
    model_version: str | None


class DocumentExtractionUpdate(BaseModel):
    """Revisión humana: fija el valor verificado (human-by-exception)."""
    verified_value: str | None = None


class ExtractedFieldPreview(BaseModel):
    field_name: str
    value: str | None
    confidence: float


class LineItemPreview(BaseModel):
    """Ítem de proforma/factura leído del documento, para prellenar la cotización."""
    description: str | None = None
    hs_code: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    confidence: float = 0.0


class ExtractionPreview(BaseModel):
    """Extracción efímera (sin persistir) para prellenar formularios (p. ej. cotización)."""
    model_version: str
    fields: list[ExtractedFieldPreview]
    line_items: list[LineItemPreview] = []


class RucExtractionPreview(BaseModel):
    """Datos leídos de un certificado de RUC del SRI (sin persistir), para prellenar
    el formulario de cliente."""
    ruc: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    entity_type: str | None = None
    confidence: float = 0.0
    model_version: str


class CaseExtractionDoc(BaseModel):
    """Datos extraídos de un documento de un expediente (para revisión en el caso)."""
    document_id: uuid.UUID
    version: int
    doc_type: str
    filename: str
    model_version: str | None = None
    fields: list[DocumentExtractionRead] = []
