"""Calendario laboral y políticas de SLA (configurables)."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessCalendar(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_calendar"

    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(48), nullable=False, default="America/Guayaquil")
    working_hours: Mapped[dict] = mapped_column(JSONVariant, nullable=False)  # {"mon":[["08:00","17:00"]]}
    holidays: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)  # ["2026-01-01", ...]


class SLAPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sla_policy"

    milestone: Mapped[str] = mapped_column(String(48), nullable=False, unique=True)
    business_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calendar_name: Mapped[str] = mapped_column(String(32), nullable=False, default="INTERNO")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
