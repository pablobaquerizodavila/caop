"""Reconciliación tributaria: estimado del motor (cotización) vs. liquidación real (SENAE).

Permite medir la precisión del motor arancelario. El estimado se toma de la cotización
de origen del expediente; la liquidación real la ingresa el operador (de ECUAPASS) o,
en el futuro, una integración oficial. Se guarda la diferencia por componente y total.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(18, 4)


class TaxReconciliation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tax_reconciliation"

    customs_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    # Montos por componente (tax_type -> monto). Estimado del motor y real de SENAE.
    estimated: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    actual: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    estimated_total: Mapped[Decimal] = mapped_column(MONEY, default=0)
    actual_total: Mapped[Decimal] = mapped_column(MONEY, default=0)
    difference: Mapped[Decimal] = mapped_column(MONEY, default=0)         # actual - estimado
    difference_pct: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
