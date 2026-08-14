"""VUE — Documentos de control previo (permisos/autorizaciones) por expediente.

Modela las autorizaciones previas a la importación gestionadas por la Ventanilla
Única (INEN, ARCSA, Agrocalidad, MPCEIP, MSP, ...). La interacción con la VUE real
se hace mediante un conector enchufable; hoy opera contra un SIMULADOR etiquetado.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VuePermit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vue_permit"

    customs_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False
    )
    entity: Mapped[str] = mapped_column(String(32), nullable=False)  # INEN/ARCSA/AGROCALIDAD/...
    document_code: Mapped[str] = mapped_column(String(48), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permit_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # REQUIRED / REQUESTED / APPROVED / REJECTED / EXEMPT / EXPIRED
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="REQUIRED")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    error_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def is_satisfied(self, today: date) -> bool:
        """Un control previo satisface el despacho si está APROBADO/EXENTO y vigente."""
        if self.status == "EXEMPT":
            return True
        if self.status == "APPROVED":
            return self.valid_until is None or self.valid_until >= today
        return False
