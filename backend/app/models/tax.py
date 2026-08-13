"""Reglas tributarias versionadas (Tax Rule Engine).

Los porcentajes NUNCA se codifican en el código: viven aquí, versionados por
fecha de vigencia y con su fuente legal. El motor (services/tax_engine.py)
resuelve las reglas aplicables a una fecha y las calcula en cadena.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class TaxRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tax_rule"

    tax_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # AD_VALOREM, FODINFA, ICE, IVA, SAFEGUARD, ANTIDUMPING, COMPENSATORY
    hs_code: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    commercial_agreement: Mapped[str | None] = mapped_column(String(64), nullable=True)

    calculation_method: Mapped[str] = mapped_column(
        String(24), nullable=False, default="AD_VALOREM_PCT"
    )  # AD_VALOREM_PCT | SPECIFIC | MIXED
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    specific_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    # Base sobre la que se aplica; tokens sumados: CIF y/o tax_types previos.
    # Ej: "CIF"  o  "CIF+AD_VALOREM+FODINFA+ICE+SAFEGUARD"
    base_formula: Mapped[str] = mapped_column(String(128), nullable=False, default="CIF")
    depends_on: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    exception: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
