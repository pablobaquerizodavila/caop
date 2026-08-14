"""Embarque, expediente aduanero y eventos del expediente (timeline)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
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

    # Datos de transporte (marítimo/aéreo)
    load_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FCL/LCL/AIR
    carrier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mbl_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hbl_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mawb_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hawb_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vessel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voyage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pol: Mapped[str | None] = mapped_column(String(64), nullable=True)  # puerto/aeropuerto origen
    pod: Mapped[str | None] = mapped_column(String(64), nullable=True)  # destino
    etd: Mapped[date | None] = mapped_column(Date, nullable=True)
    eta: Mapped[date | None] = mapped_column(Date, nullable=True)
    ata: Mapped[date | None] = mapped_column(Date, nullable=True)

    customs_case: Mapped["CustomsCase"] = relationship(
        back_populates="shipment", uselist=False, lazy="selectin"
    )
    containers: Mapped[list["Container"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", lazy="selectin"
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

    # Track & Trace: token público (capability URL) para seguimiento del cliente.
    tracking_token: Mapped[str | None] = mapped_column(
        String(48), nullable=True, unique=True, index=True
    )
    tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shipment: Mapped[Shipment] = relationship(back_populates="customs_case")


class Container(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Contenedor (FCL) para el cálculo de demurrage/detention."""

    __tablename__ = "container"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False
    )
    container_number: Mapped[str] = mapped_column(String(16), nullable=False)
    iso_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 20GP/40HC...
    size: Mapped[str | None] = mapped_column(String(8), nullable=True)
    seal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="IN_TRANSIT")
    # IN_TRANSIT / AT_PORT / GATE_OUT / EMPTY_RETURNED

    arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    free_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    gate_out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    empty_return_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    shipment: Mapped["Shipment"] = relationship(back_populates="containers")


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
