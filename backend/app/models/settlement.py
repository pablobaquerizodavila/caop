"""Liquidación de gastos / estado de cuenta al cliente por expediente.

Es el documento con el que el agente cobra al importador: honorarios (ingreso del
agente, gravados con IVA) + desembolsos reembolsables (tributos, flete, seguro,
almacenaje, demurrage, gastos portuarios). NO es facturación electrónica del SRI.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(18, 2)


class Settlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settlement"

    customs_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False
    )
    settlement_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")  # DRAFT/ISSUED
    iva_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("15.00"))

    subtotal_fees: Mapped[Decimal] = mapped_column(MONEY, default=0)
    subtotal_disbursements: Mapped[Decimal] = mapped_column(MONEY, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)
    total: Mapped[Decimal] = mapped_column(MONEY, default=0)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    lines: Mapped[list["SettlementLine"]] = relationship(
        back_populates="settlement", cascade="all, delete-orphan",
        order_by="SettlementLine.sort_no", lazy="selectin",
    )


class SettlementLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settlement_line"

    settlement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("settlement.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="DISBURSEMENT")
    # FEE (honorario, ingreso) / DISBURSEMENT (reembolsable)
    category: Mapped[str] = mapped_column(String(24), nullable=False, default="OTRO")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(MONEY, default=0)
    taxable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    settlement: Mapped[Settlement] = relationship(back_populates="lines")
