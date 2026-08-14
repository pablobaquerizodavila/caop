"""Comprobante electrónico del SRI (factura) generado desde una liquidación.

Se genera contra la estructura oficial del SRI con clave de acceso válida (módulo 11).
La firma XAdES-BES y la autorización real requieren el certificado .p12 y los web
services del SRI: hoy operan en modo SIMULADOR (conector enchufable). No se transmite
al SRI hasta conectar el adapter real.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ElectronicInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "electronic_invoice"

    settlement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("settlement.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    customs_case_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    document_type: Mapped[str] = mapped_column(String(2), nullable=False, default="01")  # factura
    ambiente: Mapped[str] = mapped_column(String(1), nullable=False, default="1")  # 1=pruebas
    emission_type: Mapped[str] = mapped_column(String(1), nullable=False, default="1")  # 1=normal
    estab: Mapped[str] = mapped_column(String(3), nullable=False, default="001")
    pto_emi: Mapped[str] = mapped_column(String(3), nullable=False, default="001")
    secuencial: Mapped[str] = mapped_column(String(9), nullable=False)
    access_key: Mapped[str] = mapped_column(String(49), nullable=False, unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)

    # DRAFT / SIGNED / AUTHORIZED / REJECTED
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authorization_number: Mapped[str | None] = mapped_column(String(49), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
