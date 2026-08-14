"""S20: Track & Trace — token público de seguimiento en customs_case

Revision ID: 0010_tracking
Revises: 0009_ocean_containers
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_tracking"
down_revision: str | None = "0009_ocean_containers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customs_case", sa.Column("tracking_token", sa.String(48), nullable=True))
    op.add_column(
        "customs_case",
        sa.Column("tracking_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_customs_case_tracking_token",
        "customs_case",
        ["tracking_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_customs_case_tracking_token", table_name="customs_case")
    op.drop_column("customs_case", "tracking_enabled")
    op.drop_column("customs_case", "tracking_token")
