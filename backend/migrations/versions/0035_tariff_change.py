"""S58 (#10): cambios tipados entre versiones arancelarias

Revision ID: 0035_tariff_change
Revises: 0034_tariff_sync_log
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035_tariff_change"
down_revision: str | None = "0034_tariff_sync_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tariff_change",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tariff_version_id", UUID, sa.ForeignKey("tariff_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", sa.String(24), nullable=False),
        sa.Column("hs_code", sa.String(16), nullable=True),
        sa.Column("code_normalized", sa.String(12), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_change_version", "tariff_change", ["tariff_version_id"])
    op.create_index("ix_tariff_change_type", "tariff_change", ["change_type"])
    op.create_index("ix_tariff_change_norm", "tariff_change", ["code_normalized"])


def downgrade() -> None:
    op.drop_index("ix_tariff_change_norm", table_name="tariff_change")
    op.drop_index("ix_tariff_change_type", table_name="tariff_change")
    op.drop_index("ix_tariff_change_version", table_name="tariff_change")
    op.drop_table("tariff_change")
