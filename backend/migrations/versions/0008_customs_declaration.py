"""S16: customs_declaration (DAI + simulador SENAE)

Revision ID: 0008_customs_declaration
Revises: 0007_sla_config
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_customs_declaration"
down_revision: str | None = "0007_sla_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customs_declaration",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("declaration_number", sa.String(32), nullable=False, unique=True),
        sa.Column("regime", sa.String(8), nullable=False, server_default="10"),
        sa.Column("status", sa.String(32), nullable=False, server_default="READY_FOR_SIGNATURE"),
        sa.Column("aforo_channel", sa.String(16), nullable=True),
        sa.Column("signed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("signed_by", sa.String(128), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transmitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_ref", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(32), nullable=True),
        sa.Column("error_description", sa.Text(), nullable=True),
        sa.Column("raw_sent", postgresql.JSONB(), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.Column("exchanges", postgresql.JSONB(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("customs_declaration")
