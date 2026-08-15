"""S41: nota de débito electrónica (debit_note)

Revision ID: 0020_debit_note
Revises: 0019_reminder
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_debit_note"
down_revision: str | None = "0019_reminder"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debit_note",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("electronic_invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(2), nullable=False, server_default="05"),
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
        sa.Column("motivo", sa.String(300), nullable=False, server_default="Cargo adicional"),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), server_default="0"),
        sa.Column("total", sa.Numeric(18, 2), server_default="0"),
        sa.Column("xml", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_debit_note_access_key", "debit_note", ["access_key"], unique=True)
    op.create_index("ix_debit_note_invoice", "debit_note", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_debit_note_invoice", table_name="debit_note")
    op.drop_index("ix_debit_note_access_key", table_name="debit_note")
    op.drop_table("debit_note")
