"""S51: reconciliación tributaria (estimado vs. liquidación SENAE)

Revision ID: 0028_reconciliation
Revises: 0027_certificate_origin
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_reconciliation"
down_revision: str | None = "0027_certificate_origin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tax_reconciliation",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("customs_case_id", UUID, sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estimated", postgresql.JSONB(), nullable=True),
        sa.Column("actual", postgresql.JSONB(), nullable=True),
        sa.Column("estimated_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("actual_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("difference", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("difference_pct", sa.Numeric(9, 4), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.String(128), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tax_reconciliation_case", "tax_reconciliation", ["customs_case_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tax_reconciliation_case", table_name="tax_reconciliation")
    op.drop_table("tax_reconciliation")
