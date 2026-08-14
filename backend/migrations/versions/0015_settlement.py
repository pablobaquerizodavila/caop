"""S27: liquidación al cliente (settlement + settlement_line)

Revision ID: 0015_settlement
Revises: 0014_warehouse_tariff
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_settlement"
down_revision: str | None = "0014_warehouse_tariff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settlement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customs_case_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("settlement_number", sa.String(32), nullable=False, unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("iva_rate", sa.Numeric(5, 2), server_default="15.00"),
        sa.Column("subtotal_fees", sa.Numeric(18, 2), server_default="0"),
        sa.Column("subtotal_disbursements", sa.Numeric(18, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), server_default="0"),
        sa.Column("total", sa.Numeric(18, 2), server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_object_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_settlement_number", "settlement", ["settlement_number"], unique=True)
    op.create_index("ix_settlement_case", "settlement", ["customs_case_id"])

    op.create_table(
        "settlement_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "settlement_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("settlement.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False, server_default="DISBURSEMENT"),
        sa.Column("category", sa.String(24), nullable=False, server_default="OTRO"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), server_default="0"),
        sa.Column("taxable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_settlement_line_settlement", "settlement_line", ["settlement_id"])


def downgrade() -> None:
    op.drop_index("ix_settlement_line_settlement", table_name="settlement_line")
    op.drop_table("settlement_line")
    op.drop_index("ix_settlement_case", table_name="settlement")
    op.drop_index("ix_settlement_number", table_name="settlement")
    op.drop_table("settlement")
