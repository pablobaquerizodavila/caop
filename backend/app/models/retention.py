"""Comprobante de retención electrónico del SRI (codDoc 07).

Lo emite el agente de retención sobre el documento de sustento (factura recibida de
un proveedor), reteniendo Renta (1) y/o IVA (2). Firma y autorización usan el mismo
conector SRI enchufable (hoy simulador); no hay transmisión real.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(18, 2)


class RetentionVoucher(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retention_voucher"

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("supplier.id"), nullable=True
    )
    # Sujeto retenido (proveedor)
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id_type: Mapped[str] = mapped_column(String(2), nullable=False, default="04")  # 04=RUC

    period: Mapped[str] = mapped_column(String(7), nullable=False)  # MM/AAAA
    # Documento de sustento (factura recibida)
    doc_sustento_type: Mapped[str] = mapped_column(String(2), nullable=False, default="01")
    doc_sustento_number: Mapped[str] = mapped_column(String(20), nullable=False)  # 001-001-000000001
    doc_sustento_date: Mapped[date] = mapped_column(Date, nullable=False)

    document_type: Mapped[str] = mapped_column(String(2), nullable=False, default="07")
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

    total_retained: Mapped[Decimal] = mapped_column(MONEY, default=0)
    xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list["RetentionLine"]] = relationship(
        back_populates="voucher", cascade="all, delete-orphan", lazy="selectin",
    )


class RetentionLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retention_line"

    retention_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("retention_voucher.id", ondelete="CASCADE"), nullable=False
    )
    tax_type: Mapped[str] = mapped_column(String(1), nullable=False)  # 1=Renta, 2=IVA
    codigo_retencion: Mapped[str] = mapped_column(String(5), nullable=False)
    base_imponible: Mapped[Decimal] = mapped_column(MONEY, default=0)
    percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    value: Mapped[Decimal] = mapped_column(MONEY, default=0)

    voucher: Mapped[RetentionVoucher] = relationship(back_populates="lines")
