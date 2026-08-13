"""S1: customer, contact, consent_record, supplier, document, document_version, document_extraction

Revision ID: 0002_customers_documents
Revises: 0001_initial
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_customers_documents"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=True),
        sa.Column("ruc", sa.String(13), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("trade_name", sa.String(255), nullable=True),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("billing_data", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="LEAD"),
        sa.Column("notification_prefs", postgresql.JSONB(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_customer_ruc", "customer", ["ruc"])

    op.create_table(
        "contact",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_ts(),
    )

    op.create_table(
        "consent_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contact.id"), nullable=True),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("legal_basis", sa.String(64), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
    )

    op.create_table(
        "supplier",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("aliases", postgresql.JSONB(), nullable=True),
        *_ts(),
    )

    op.create_table(
        "document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doc_type", sa.String(64), nullable=False, server_default="UNCLASSIFIED"),
        sa.Column("source", sa.String(32), nullable=False, server_default="PORTAL"),
        *_ts(),
    )
    op.create_index("ix_document_customer", "document", ["customer_id"])

    op.create_table(
        "document_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint("document_id", "version", name="uq_document_version"),
    )

    op.create_table(
        "document_extraction",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("extracted_value", sa.String(2048), nullable=True),
        sa.Column("verified_value", sa.String(2048), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        *_ts(),
    )


def downgrade() -> None:
    op.drop_table("document_extraction")
    op.drop_table("document_version")
    op.drop_index("ix_document_customer", table_name="document")
    op.drop_table("document")
    op.drop_table("supplier")
    op.drop_table("consent_record")
    op.drop_table("contact")
    op.drop_index("ix_customer_ruc", table_name="customer")
    op.drop_table("customer")
