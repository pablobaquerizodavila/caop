"""Nota de débito electrónica del SRI (codDoc 05): cargos adicionales sobre una factura.

Estructura oficial (infoNotaDebito con motivos). Firma y autorización usan el mismo
conector SRI enchufable (hoy simulador); no hay transmisión real.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DebitNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "debit_note"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("electronic_invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    customs_case_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    document_type: Mapped[str] = mapped_column(String(2), nullable=False, default="05")
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

    motivo: Mapped[str] = mapped_column(String(300), nullable=False, default="Cargo adicional")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
