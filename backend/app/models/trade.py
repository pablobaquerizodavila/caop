"""Preferencias arancelarias: países, acuerdos comerciales y preferencias por subpartida.

Alimenta al resolvedor para el escenario 'con preferencia': un arancel Ad-Valorem
reducido cuando el país de origen es miembro de un acuerdo vigente, la mercancía
está cubierta y se cumple el requisito de origen (certificado). El escenario 'sin
preferencia' siempre se calcula con el arancel general.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class Country(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "country"

    iso2: Mapped[str] = mapped_column(String(2), nullable=False, unique=True, index=True)
    iso3: Mapped[str | None] = mapped_column(String(3), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TradeAgreement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trade_agreement"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="FTA")  # CUSTOMS_UNION/FTA/PARTIAL
    members: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)  # lista de ISO2
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TariffPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Preferencia arancelaria. Si hs_prefix es NULL/vacío aplica a todo el acuerdo;
    si origin_country es NULL aplica a todos los miembros del acuerdo."""

    __tablename__ = "tariff_preference"

    agreement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("trade_agreement.id", ondelete="CASCADE"), nullable=False
    )
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    hs_prefix: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)  # normalizado
    liberation_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal(100))
    preferential_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)  # override %
    requires_certificate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNVERIFIED")
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CertificateOfOrigin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Certificado/prueba de origen. Habilita el escenario preferencial 'aplicable'
    (frente a 'potencial') cuando está VALIDADO y vigente."""

    __tablename__ = "certificate_of_origin"

    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quote.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customs_case_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=True
    )
    agreement_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("trade_agreement.id"), nullable=True
    )
    cert_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ORIGEN")
    number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issuing_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    organism: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # PENDING / VALID / REJECTED
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def is_valid_on(self, on: date) -> bool:
        return self.validation_status == "VALID" and (self.valid_until is None or self.valid_until >= on)
