"""S43: comprobante de retención (retention_voucher + retention_line)

Revision ID: 0021_retention
Revises: 0020_debit_note
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_retention"
down_revision: str | None = "0020_debit_note"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retention_voucher",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("subject_name", sa.String(255), nullable=False),
        sa.Column("subject_id", sa.String(20), nullable=False),
        sa.Column("subject_id_type", sa.String(2), nullable=False, server_default="04"),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("doc_sustento_type", sa.String(2), nullable=False, server_default="01"),
        sa.Column("doc_sustento_number", sa.String(20), nullable=False),
        sa.Column("doc_sustento_date", sa.Date(), nullable=False),
        sa.Column("document_type", sa.String(2), nullable=False, server_default="07"),
        sa.Column("ambiente", sa.String(1), nullable=False, server_default="1"),
        sa.Column("emission_type", sa.String(1), nullable=False, server_default="1"),
        sa.Column("estab", sa.String(3), nullable=False, server_default="001"),
        sa.Column("pto_emi", sa.String(3), nullable=False, server_default="001"),
        sa.Column("secuencial", sa.String(9), nullable=False),
        sa.Column("access_key", sa.String(49), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("signed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authorization_number", sa.String(49), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("total_retained", sa.Numeric(18, 2), server_default="0"),
        sa.Column("xml", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_retention_voucher_access_key", "retention_voucher", ["access_key"], unique=True)

    op.create_table(
        "retention_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retention_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("retention_voucher.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tax_type", sa.String(1), nullable=False),
        sa.Column("codigo_retencion", sa.String(5), nullable=False),
        sa.Column("base_imponible", sa.Numeric(18, 2), server_default="0"),
        sa.Column("percentage", sa.Numeric(6, 2), server_default="0"),
        sa.Column("value", sa.Numeric(18, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_retention_line_voucher", "retention_line", ["retention_id"])


def downgrade() -> None:
    op.drop_index("ix_retention_line_voucher", table_name="retention_line")
    op.drop_table("retention_line")
    op.drop_index("ix_retention_voucher_access_key", table_name="retention_voucher")
    op.drop_table("retention_voucher")
