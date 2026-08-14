"""S9: business_calendar, sla_policy

Revision ID: 0007_sla_config
Revises: 0006_notifications
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_sla_config"
down_revision: str | None = "0006_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "business_calendar",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
        sa.Column("timezone", sa.String(48), nullable=False, server_default="America/Guayaquil"),
        sa.Column("working_hours", postgresql.JSONB(), nullable=False),
        sa.Column("holidays", postgresql.JSONB(), nullable=True),
        *_ts(),
    )
    op.create_table(
        "sla_policy",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("milestone", sa.String(48), nullable=False, unique=True),
        sa.Column("business_minutes", sa.Integer(), nullable=False),
        sa.Column("calendar_name", sa.String(32), nullable=False, server_default="INTERNO"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="NORMAL"),
        *_ts(),
    )


def downgrade() -> None:
    op.drop_table("sla_policy")
    op.drop_table("business_calendar")
