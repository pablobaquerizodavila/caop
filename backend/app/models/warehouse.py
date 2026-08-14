"""Almacenaje en bodega / depósito temporal (carga aérea y consolidada).

Equivalente al demurrage pero para permanencia en bodega: días libres de
almacenaje y costo por permanencia. El costo se estima según el tipo de tarifa
(por día, por kg-día o monto fijo). Es un estimador configurable, no una tarifa
oficial: verificar contra el depósito temporal correspondiente.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WarehouseStorage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouse_storage"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)  # guía/lote
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # ingreso a bodega
    free_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Tipo de tarifa: PER_DAY (por día) / PER_KG_DAY (por kg-día) / FLAT (monto único)
    rate_type: Mapped[str] = mapped_column(String(12), nullable=False, default="PER_DAY")
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    chargeable_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    withdrawal_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # retiro de bodega
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="IN_WAREHOUSE")
    # IN_WAREHOUSE / WITHDRAWN
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    shipment = relationship("Shipment")
