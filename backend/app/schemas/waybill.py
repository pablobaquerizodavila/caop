"""Schemas de la guía de remisión."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class WaybillItemIn(BaseModel):
    description: str
    quantity: float = 1


class WaybillItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    quantity: float


class WaybillCreate(BaseModel):
    customs_case_id: uuid.UUID | None = None
    transporter_name: str
    transporter_id: str
    transporter_id_type: str = "04"
    placa: str
    dir_partida: str = "S/N"
    fecha_ini_transporte: date
    fecha_fin_transporte: date
    dest_name: str
    dest_id: str
    dest_address: str = "S/N"
    motivo_traslado: str = "Entrega de mercancía importada"
    num_doc_sustento: str | None = None
    fecha_doc_sustento: date | None = None
    items: list[WaybillItemIn]


class WaybillAuthorize(BaseModel):
    scenario: str = "AUTHORIZE"


class WaybillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    transporter_name: str
    transporter_id: str
    placa: str
    fecha_ini_transporte: date
    fecha_fin_transporte: date
    dest_name: str
    dest_id: str
    motivo_traslado: str
    estab: str
    pto_emi: str
    secuencial: str
    access_key: str
    issue_date: date
    status: str
    signed: bool
    authorization_number: str | None
    authorized_at: datetime | None
    is_simulated: bool
    error: str | None
    items: list[WaybillItemRead] = []
