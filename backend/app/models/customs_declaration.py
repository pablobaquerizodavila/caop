"""Declaración Aduanera de Importación (DAI) y su ciclo con SENAE.

IMPORTANTE: mientras no exista integración oficial, esta DAI se procesa contra un
SIMULADOR (is_simulated=True). Los estados son PLACEHOLDERS INTERNOS, no estados
literales de ECUAPASS. Se guarda el mensaje enviado (raw_sent) y la respuesta
(raw_response) para trazabilidad.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class CustomsDeclaration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customs_declaration"

    customs_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    declaration_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    regime: Mapped[str] = mapped_column(String(8), nullable=False, default="10")

    # Estado interno (placeholder). READY_FOR_SIGNATURE, SIGNED, TRANSMITTED, ACCEPTED,
    # REJECTED, LIQUIDATED, PAID, AFORO_ASSIGNED, OBSERVED, OBSERVATION_RESOLVED, RELEASED.
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="READY_FOR_SIGNATURE")
    aforo_channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # AUTOMATICO / DOCUMENTAL / FISICO / NO_INTRUSIVO

    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)  # usuario/sub
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transmitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_sent: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    # Historial de respuestas/mensajes (lista) para la trazabilidad.
    exchanges: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)

    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
