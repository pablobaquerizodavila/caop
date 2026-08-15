"""S57 (#9): bitácora de sincronización con fuentes oficiales (vigilante)

Revision ID: 0034_tariff_sync_log
Revises: 0033_restrictions_control
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_tariff_sync_log"
down_revision: str | None = "0033_restrictions_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tariff_sync_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_id", UUID, sa.ForeignKey("official_source.id"), nullable=True),
        sa.Column("source_code", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="OK"),
        sa.Column("found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_sync_log_status", "tariff_sync_log", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tariff_sync_log_status", table_name="tariff_sync_log")
    op.drop_table("tariff_sync_log")
