"""Schemas de notificaciones y plantillas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationSendRequest(BaseModel):
    channel: str  # EMAIL / WHATSAPP
    template_code: str
    to: str
    context: dict = {}
    customer_id: uuid.UUID | None = None
    customs_case_id: uuid.UUID | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    channel: str
    template_code: str | None
    template_version: int | None
    to_address: str
    subject: str | None
    body: str | None
    status: str
    error: str | None
    customer_id: uuid.UUID | None
    customs_case_id: uuid.UUID | None
    created_at: datetime


class TemplateCreate(BaseModel):
    code: str
    version: int = 1
    channel: str
    subject_template: str | None = None
    body_template: str
    active: bool = True


class TemplateUpdate(BaseModel):
    subject_template: str | None = None
    body_template: str | None = None
    active: bool | None = None


class TemplateRead(TemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
