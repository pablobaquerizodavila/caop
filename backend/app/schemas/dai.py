"""Schemas de la Declaración Aduanera (DAI) y su simulación."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeclarationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customs_case_id: uuid.UUID
    declaration_number: str
    regime: str
    status: str
    aforo_channel: str | None
    signed: bool
    signed_by: str | None
    signed_at: datetime | None
    transmitted_at: datetime | None
    external_ref: str | None
    error_code: str | None
    error_description: str | None
    is_simulated: bool
    raw_sent: dict | None
    raw_response: dict | None
    exchanges: list | None


class TransmitRequest(BaseModel):
    scenario: str = "ACCEPT"  # ACCEPT | REJECT | UNAVAILABLE


class AdvanceRequest(BaseModel):
    aforo_channel: str | None = None  # AUTOMATICO | DOCUMENTAL | FISICO | NO_INTRUSIVO
    observation: bool = False
