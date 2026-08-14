"""Schemas del motor de SLA."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SlaInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    milestone: str
    start_time: datetime
    deadline: datetime | None
    status: str
    escalation_level: int
    severity: str
    breach_reason: str | None
