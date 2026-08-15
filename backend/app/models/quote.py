"""Cotización, ítems, rubros de costo e historial de estados.

La cotización es una SIMULACIÓN FINANCIERA DE IMPORTACIÓN: consume el Tax Engine
por ítem y calcula el landed cost. Separa el precio al cliente del costo interno
y el margen (el cliente NUNCA ve la rentabilidad interna: ver schemas público).
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import (
    DateTime as SADateTime,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(18, 4)


class Quote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quote"

    quote_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id"), nullable=True
    )

    transport_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # OCEAN/AIR
    load_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # FCL/LCL/AIR
    incoterm: Mapped[str | None] = mapped_column(String(3), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_import_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Totales calculados
    total_units: Mapped[Decimal] = mapped_column(MONEY, default=0)
    total_cif: Mapped[Decimal] = mapped_column(MONEY, default=0)
    total_taxes: Mapped[Decimal] = mapped_column(MONEY, default=0)
    customer_price_total: Mapped[Decimal] = mapped_column(MONEY, default=0)  # servicios cobrados
    internal_cost_total: Mapped[Decimal] = mapped_column(MONEY, default=0)  # interno (oculto)
    margin_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)  # interno (oculto)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)  # interno (oculto)
    landed_cost_total: Mapped[Decimal] = mapped_column(MONEY, default=0)
    landed_cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)

    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    pdf_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    disclaimer_version: Mapped[str] = mapped_column(String(16), default="v1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan",
        order_by="QuoteItem.line_no", lazy="selectin",
    )
    cost_lines: Mapped[list["CostLine"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", lazy="selectin",
    )
    status_history: Mapped[list["QuoteStatusHistory"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan",
        order_by="QuoteStatusHistory.occurred_at", lazy="selectin",
    )


class QuoteItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quote_item"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quote.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hs_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hs_status: Mapped[str] = mapped_column(String(16), default="PRELIMINARY")  # VALIDATED/PRELIMINARY
    # S48: validación contra el maestro arancelario (no rompe el campo de texto libre)
    hs_validation: Mapped[str] = mapped_column(String(16), default="UNKNOWN")  # UNKNOWN/VALID/NOT_FOUND
    tariff_code_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tariff_code.id"), nullable=True
    )
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    commercial_agreement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(MONEY, default=1)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    line_value: Mapped[Decimal] = mapped_column(MONEY, default=0)  # valor mercancía (FOB)
    weight: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    freight_alloc: Mapped[Decimal] = mapped_column(MONEY, default=0)
    insurance_alloc: Mapped[Decimal] = mapped_column(MONEY, default=0)
    cif_value: Mapped[Decimal] = mapped_column(MONEY, default=0)
    taxes_total: Mapped[Decimal] = mapped_column(MONEY, default=0)
    tax_breakdown: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    # S48: señalización de estimación tributaria (faltante ≠ 0%) + versión arancelaria usada
    tax_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_warnings: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    tax_data_version: Mapped[str | None] = mapped_column(String(48), nullable=True)
    # S50 2B-2: escenario preferencial por ítem (acuerdo, %pref, tributos, ahorro, certificado)
    preference: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    # S55 #3/#4: atributos para tarifas condicionales/por tramos (p. ej. {"CC": 2000})
    attributes: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    quote: Mapped[Quote] = relationship(back_populates="items")


class CostLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cost_line"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quote.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(24), nullable=False)  # FEE/FREIGHT/PORT/...
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estimated_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)  # costo interno
    contingency_pct: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    quoted_amount: Mapped[Decimal] = mapped_column(MONEY, default=0)  # precio al cliente
    confidence: Mapped[str] = mapped_column(String(16), default="MEDIUM")  # HIGH/MEDIUM/LOW
    is_included: Mapped[bool] = mapped_column(Boolean, default=True)

    quote: Mapped[Quote] = relationship(back_populates="cost_lines")


class QuoteStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quote_status_history"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quote.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occurred_at: Mapped[object] = mapped_column(
        SADateTime(timezone=True), server_default=func.now(), nullable=False
    )
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    quote: Mapped[Quote] = relationship(back_populates="status_history")
