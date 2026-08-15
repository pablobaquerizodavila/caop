"""Guía de remisión electrónica del SRI (codDoc 06): sustenta el traslado de mercancía.

Estructura oficial (infoGuiaRemision + destinatarios con detalles). Firma y
autorización usan el mismo conector SRI enchufable (hoy simulador); sin transmisión real.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WaybillGuide(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "waybill_guide"

    customs_case_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    # Transportista
    transporter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    transporter_id: Mapped[str] = mapped_column(String(20), nullable=False)
    transporter_id_type: Mapped[str] = mapped_column(String(2), nullable=False, default="04")
    placa: Mapped[str] = mapped_column(String(20), nullable=False)
    dir_partida: Mapped[str] = mapped_column(String(300), nullable=False, default="S/N")
    fecha_ini_transporte: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_transporte: Mapped[date] = mapped_column(Date, nullable=False)

    # Destinatario
    dest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dest_id: Mapped[str] = mapped_column(String(20), nullable=False)
    dest_address: Mapped[str] = mapped_column(String(300), nullable=False, default="S/N")
    motivo_traslado: Mapped[str] = mapped_column(String(300), nullable=False, default="Entrega de mercancía importada")
    num_doc_sustento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_doc_sustento: Mapped[date | None] = mapped_column(Date, nullable=True)

    document_type: Mapped[str] = mapped_column(String(2), nullable=False, default="06")
    ambiente: Mapped[str] = mapped_column(String(1), nullable=False, default="1")
    emission_type: Mapped[str] = mapped_column(String(1), nullable=False, default="1")
    estab: Mapped[str] = mapped_column(String(3), nullable=False, default="001")
    pto_emi: Mapped[str] = mapped_column(String(3), nullable=False, default="001")
    secuencial: Mapped[str] = mapped_column(String(9), nullable=False)
    access_key: Mapped[str] = mapped_column(String(49), nullable=False, unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authorization_number: Mapped[str | None] = mapped_column(String(49), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["WaybillItem"]] = relationship(
        back_populates="guide", cascade="all, delete-orphan", lazy="selectin",
    )


class WaybillItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "waybill_item"

    guide_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("waybill_guide.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=1)

    guide: Mapped[WaybillGuide] = relationship(back_populates="items")
