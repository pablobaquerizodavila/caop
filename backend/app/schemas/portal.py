"""Schemas del portal del cliente (vista del importador, sólo lectura).

Nunca exponen costo interno ni margen: sólo lo que el cliente puede ver.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.settlement import SettlementRead
from app.schemas.tracking import TrackView


class PortalCustomer(BaseModel):
    id: uuid.UUID
    ruc: str
    legal_name: str
    trade_name: str | None = None
    email: str | None = None


class PortalProfile(BaseModel):
    linked: bool
    customer: PortalCustomer | None = None
    cases: int = 0
    quotes: int = 0


class PortalCaseSummary(BaseModel):
    id: uuid.UUID
    case_number: str
    status_label: str
    status_sem: str
    transport_mode: str | None = None
    origin_country: str | None = None
    created_at: datetime | None = None


class PortalQuote(BaseModel):
    id: uuid.UUID
    quote_number: str
    version: int
    status: str
    currency: str
    customer_price_total: float
    landed_cost_total: float
    valid_until: date | None = None
    created_at: datetime | None = None


class PortalCaseDetail(BaseModel):
    track: TrackView
    settlement: SettlementRead | None = None
