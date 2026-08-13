"""Instancias de SLA por hito (versión inicial: tiempo calendario)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SLAInstance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sla_instance"

    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)  # CUSTOMS_CASE...
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    milestone: Mapped[str] = mapped_column(String(48), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    owner: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ON_TIME")
    # ON_TIME / AT_RISK / CRITICAL / BREACHED / MET
    breach_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
