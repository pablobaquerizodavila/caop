"""Embarque, expediente aduanero y eventos del expediente (timeline)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class Shipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shipment"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id"), nullable=False
    )
    source_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quote.id"), nullable=True, unique=True
    )
    transport_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # OCEAN/AIR
    incoterm: Mapped[str | None] = mapped_column(String(3), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")

    customs_case: Mapped["CustomsCase"] = relationship(
        back_populates="shipment", uselist=False, lazy="selectin"
    )


class CustomsCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customs_case"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False
    )
    case_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    customs_regime: Mapped[str] = mapped_column(String(8), nullable=False, default="10")
    current_state: Mapped[str] = mapped_column(String(32), nullable=False, default="CASE_CREATED")
    next_expected_event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    responsible_actor: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    customs_readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    blocker: Mapped[str | None] = mapped_column(Text, nullable=True)

    shipment: Mapped[Shipment] = relationship(back_populates="customs_case")


class CaseEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_event"

    customs_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    event_source: Mapped[str] = mapped_column(String(24), nullable=False, default="SYSTEM")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
