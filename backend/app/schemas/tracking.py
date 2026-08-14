"""Schemas del portal público de Track & Trace (vista del cliente importador).

Exponen SOLO información apta para el cliente: hitos, transporte y contenedores.
Nunca costos, márgenes, notas internas ni motivos técnicos de rechazo.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class TrackMilestone(BaseModel):
    key: str
    label: str
    status: str  # done / current / pending
    at: datetime | None = None
    detail: str | None = None


class TrackContainer(BaseModel):
    number: str
    status_label: str
    last_free_day: date | None = None
    days_to_last_free_day: int | None = None
    alarm: str  # OK / WARN / AT_RISK / CRITICAL
    alarm_label: str


class TrackTransport(BaseModel):
    mode: str | None = None  # Marítimo / Aéreo
    origin: str | None = None
    destination: str | None = None
    carrier: str | None = None
    vessel_or_flight: str | None = None
    etd: date | None = None
    eta: date | None = None
    ata: date | None = None


class TrackView(BaseModel):
    reference: str
    customer_name: str
    status_label: str
    status_sem: str  # ok / warn / risk / crit
    progress_pct: int
    next_step: str | None = None
    attention: str | None = None  # aviso neutral para el cliente (sin jerga interna)
    transport: TrackTransport
    milestones: list[TrackMilestone]
    containers: list[TrackContainer]
    last_update: datetime | None = None


class TrackingLink(BaseModel):
    token: str
    url: str
    enabled: bool


class TrackingToggle(BaseModel):
    enabled: bool


class TrackingSend(BaseModel):
    channel: str = "EMAIL"  # EMAIL / WHATSAPP
    to: str | None = None  # si se omite, se usa el email/contacto del cliente


class TrackingSendResult(BaseModel):
    status: str
    to: str
    error: str | None = None
