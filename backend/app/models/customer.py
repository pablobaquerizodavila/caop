"""Cliente, contactos y registro de consentimiento (LOPDP)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=True
    )
    ruc: Mapped[str] = mapped_column(String(13), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # NATURAL (persona natural) | COMPANY (sociedad/empresa)
    entity_type: Mapped[str] = mapped_column(String(16), default="NATURAL", nullable=False)
    # Nombre desglosado (persona natural).
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    second_last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Dirección física estructurada.
    country: Mapped[str] = mapped_column(String(64), default="Ecuador", nullable=False)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)  # calle, número, referencia
    # Dirección física de despacho (puede coincidir con la fiscal).
    dispatch_same_as_address: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dispatch_country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dispatch_province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dispatch_city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dispatch_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Representante legal (solo aplica a empresas).
    legal_rep_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legal_rep_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_data: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="LEAD", nullable=False)
    notification_prefs: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contact"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)  # E.164 para WhatsApp
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship(back_populates="contacts")


class ConsentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Consentimiento / base legal de tratamiento (LOPDP)."""

    __tablename__ = "consent_record"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contact.id"), nullable=True
    )
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(64), nullable=False)  # consentimiento/contrato...
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
