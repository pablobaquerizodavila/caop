"""Tarifario de almacenaje por depósito temporal (catálogo configurable).

Es data comercial del operador (no una fuente oficial): se usa para autocompletar
el registro de almacenaje de un embarque. Cada fila = tarifa de un depósito.
"""

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WarehouseTariff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouse_tariff"

    warehouse_name: Mapped[str] = mapped_column(String(128), nullable=False)
    transport_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # OCEAN/AIR/None
    free_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rate_type: Mapped[str] = mapped_column(String(12), nullable=False, default="PER_DAY")
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
