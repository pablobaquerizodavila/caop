"""Maestro arancelario: nomenclatura, fuentes oficiales, normas y versiones.

Esta capa alimenta al Tax Engine existente (no lo reemplaza). El arancel se ingiere
de fuentes oficiales (hoy: PDF del Arancel del Ecuador vía ArancelPdfAdapter), se
publica como una `TariffVersion` y cada subpartida vigente vive en `TariffCode`.
El Ad-Valorem por subpartida se materializa como filas `TaxRule` ligadas al maestro.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class OfficialSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fuente oficial de información arancelaria (SENAE, COMEX, Registro Oficial, SRI)."""

    __tablename__ = "official_source"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # SENAE/COMEX/REGISTRO_OFICIAL/SRI/MANUAL
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    adapter: Mapped[str | None] = mapped_column(String(64), nullable=True)  # nombre del TariffSourceAdapter
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LegalInstrument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Norma estructurada (resolución COMEX, decreto, Registro Oficial) con trazabilidad."""

    __tablename__ = "legal_instrument"

    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # RESOLUCION_COMEX/DECRETO/...
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    organism: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    registro_oficial: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doc_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # evidencia en MinIO
    doc_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("kind", "number", name="uq_legal_instrument_kind_number"),)


class TariffVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versión publicada del maestro/reglas arancelarias. Permite reproducibilidad y reversión."""

    __tablename__ = "tariff_version"

    number: Mapped[str] = mapped_column(String(48), nullable=False, unique=True, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("official_source.id"), nullable=True
    )
    legal_instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("legal_instrument.id"), nullable=True
    )
    # DETECTED/STAGED/VALIDATION_FAILED/PENDING_APPROVAL/APPROVED/SCHEDULED/ACTIVE/SUPERSEDED/REJECTED
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="STAGED", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    codes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TariffCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Nodo de la nomenclatura arancelaria (jerárquico). La subpartida nacional tiene 10 dígitos."""

    __tablename__ = "tariff_code"

    code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # con puntos: 0105.11.00.10
    code_normalized: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # solo dígitos
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # nº de dígitos: 2/4/6/8/10
    description: Mapped[str] = mapped_column(Text, nullable=False)  # descripción propia (de su fila)
    full_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # con contexto de ancestros
    parent_code: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)  # normalized del padre
    physical_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)  # UF: u, Kg, ...
    complementary_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    supplementary_code: Mapped[str | None] = mapped_column(String(16), nullable=True)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("official_source.id"), nullable=True
    )
    legal_instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("legal_instrument.id"), nullable=True
    )
    tariff_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tariff_version.id"), nullable=True, index=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Ad-Valorem del arancel (%) tal como viene del maestro; el TaxRule es la fuente de cálculo.
    ad_valorem: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)


class TariffChange(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cambio detectado al comparar una versión nueva (staged) contra la activa (#10).

    Tipos: NEW_CODE, REMOVED_CODE, RATE_CHANGED, DESCRIPTION_CHANGED. Se genera al ingerir
    una versión nueva para revisión ANTES de publicar (nunca cambia producción por sí solo).
    """

    __tablename__ = "tariff_change"

    tariff_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tariff_version.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    change_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    hs_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    code_normalized: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class TariffSyncLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bitácora de sincronización con fuentes oficiales (vigilante de resoluciones).

    Registra cada corrida: qué fuente, cuántas referencias se hallaron, cuántas son
    nuevas (no vistas), errores. Nunca escribe producción: solo detecta y notifica.
    """

    __tablename__ = "tariff_sync_log"

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("official_source.id"), nullable=True
    )
    source_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OK", index=True)  # OK/FAILED/NO_SOURCE
    found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detected: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)  # refs nuevas detectadas
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TariffImport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Lote de ingesta: evidencia y trazabilidad de una sincronización/carga."""

    __tablename__ = "tariff_import"

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("official_source.id"), nullable=True
    )
    tariff_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tariff_version.id"), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # evidencia en MinIO
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # FETCHED/PARSED/VALIDATED/STAGED/PUBLISHED/FAILED
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="FETCHED", index=True)
    records_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
