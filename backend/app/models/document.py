"""Documentos con versionado e integridad (SHA-256)."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customer.id"), nullable=True
    )
    # FKs a expediente/cotización se agregan en sprints posteriores (S3+).
    customs_case_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, default="UNCLASSIFIED")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="PORTAL")

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version",
        lazy="selectin",
    )

    @property
    def latest_version(self) -> "DocumentVersion | None":
        return self.versions[-1] if self.versions else None


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_version"
    __table_args__ = (UniqueConstraint("document_id", "version", name="uq_document_version"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    document: Mapped[Document] = relationship(back_populates="versions")


class DocumentExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Datos extraídos por OCR/IA (se poblará en S2/S3). Definido aquí para el ERD."""

    __tablename__ = "document_extraction"

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_version.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_value: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    verified_value: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
