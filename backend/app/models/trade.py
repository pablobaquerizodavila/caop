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


class PriceBandMeasure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Producto sujeto al Sistema Andino de Franja de Precios (SAFP, CAN Decisión 371).

    Marca la subpartida (marcador o vinculado). El derecho variable/rebaja concreto vive
    en PriceBandPeriod (dato quincenal publicado por la CAN). Si una subpartida no tiene
    PriceBandMeasure => NO sujeta a SAFP.
    """

    __tablename__ = "price_band_measure"

    hs_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # normalizado
    product: Mapped[str] = mapped_column(String(128), nullable=False)  # p. ej. "Aceite crudo de palma"
    is_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PriceBandPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Periodo (quincenal) del SAFP: franja publicada y derecho variable resultante.

    Se almacena el derecho variable YA PUBLICADO por la CAN/SENAE (ad valorem o específico;
    puede ser negativo = rebaja) para no reconstruir la fórmula. La franja (piso/techo/precio
    de referencia) se guarda como contexto/trazabilidad.
    """

    __tablename__ = "price_band_period"

    measure_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("price_band_measure.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    reference_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    floor_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)   # piso
    ceiling_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)  # techo
    variable_method: Mapped[str] = mapped_column(String(16), nullable=False, default="AD_VALOREM")  # AD_VALOREM/SPECIFIC
    variable_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)  # % o por unidad (± )
    specific_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNVERIFIED")


class TariffTier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tarifa condicional / por tramos (p. ej. vehículos: Ad-Valorem por cilindraje, ICE por
    rango de precio). El tramo se elige según un atributo del ítem (CC, valor unitario, peso).

    `tiers` es una lista ordenada de {min, max, adval_pct, specific_rate}. Se elige el primer
    tramo donde min <= valor < max (min/max nulos = sin límite). applies_to indica qué tributo
    determina: AD_VALOREM (reemplaza el arancel base) o ICE.
    """

    __tablename__ = "tariff_tier"

    hs_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # normalizado
    applies_to: Mapped[str] = mapped_column(String(16), nullable=False, default="AD_VALOREM")  # AD_VALOREM/ICE
    attribute: Mapped[str] = mapped_column(String(24), nullable=False, default="CC")  # CC/UNIT_VALUE/WEIGHT/QUANTITY
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tiers: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    specific_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    base_type: Mapped[str] = mapped_column(String(16), nullable=False, default="EX_ADUANA")  # para ICE

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNVERIFIED")
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TradeRemedy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Medida de defensa comercial: antidumping, salvaguardia o derecho compensatorio.

    Derecho adicional (por resolución COMEX) sobre una subpartida, normalmente por país de
    origen (antidumping) o general (salvaguardia). Ad valorem sobre CIF o específico por
    unidad. Temporal (effective_from/to). Si no hay medida => no aplica.
    """

    __tablename__ = "trade_remedy"

    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # ANTIDUMPING/SAFEGUARD/COMPENSATORY
    hs_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # normalizado
    origin_country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)  # None = todo origen
    exporter: Mapped[str | None] = mapped_column(String(255), nullable=True)  # productor/exportador específico
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="AD_VALOREM")  # AD_VALOREM/SPECIFIC
    ad_valorem_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    specific_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    specific_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNVERIFIED")
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IceMeasure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ICE (Impuesto a los Consumos Especiales) por subpartida. 3 metodologías (LRTI):
    específico (tarifa por unidad), ad valorem (% sobre base ex-aduana) o mixto.
    Si una subpartida no tiene IceMeasure => NO sujeta a ICE (0, no 'faltante')."""

    __tablename__ = "ice_measure"

    hs_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # normalizado
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="AD_VALOREM")  # AD_VALOREM/SPECIFIC/MIXED
    ad_valorem_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    specific_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    # Unidad de la tarifa específica. UNIDAD => aplicable con la cantidad del ítem;
    # otras (LITRO_ALCOHOL_PURO, GRAMO_AZUCAR, ...) requieren datos que el ítem no trae.
    specific_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    base_type: Mapped[str] = mapped_column(String(16), nullable=False, default="EX_ADUANA")  # EX_ADUANA/PVP/REFERENCIA
    reference_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNVERIFIED")
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
