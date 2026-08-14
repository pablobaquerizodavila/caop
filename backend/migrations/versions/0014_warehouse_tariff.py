"""S25: tarifario de almacenaje por depósito (warehouse_tariff)

Revision ID: 0014_warehouse_tariff
Revises: 0013_vue_rules
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_warehouse_tariff"
down_revision: str | None = "0013_vue_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_tariff",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("warehouse_name", sa.String(128), nullable=False),
        sa.Column("transport_mode", sa.String(16), nullable=True),
        sa.Column("free_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_type", sa.String(12), nullable=False, server_default="PER_DAY"),
        sa.Column("daily_rate", sa.Numeric(18, 2), server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("warehouse_tariff")
