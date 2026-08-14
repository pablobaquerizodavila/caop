"""S23: almacenaje en bodega / depósito temporal (warehouse_storage)

Revision ID: 0012_warehouse_storage
Revises: 0011_vue_permits
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_warehouse_storage"
down_revision: str | None = "0011_vue_permits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_storage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "shipment_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("warehouse_name", sa.String(128), nullable=True),
        sa.Column("reference", sa.String(64), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("free_days", sa.Integer(), nullable=True),
        sa.Column("rate_type", sa.String(12), nullable=False, server_default="PER_DAY"),
        sa.Column("daily_rate", sa.Numeric(18, 2), server_default="0"),
        sa.Column("chargeable_weight_kg", sa.Numeric(12, 2), nullable=True),
        sa.Column("withdrawal_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="IN_WAREHOUSE"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouse_storage_shipment", "warehouse_storage", ["shipment_id"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_storage_shipment", table_name="warehouse_storage")
    op.drop_table("warehouse_storage")
