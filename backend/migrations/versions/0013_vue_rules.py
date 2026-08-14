"""S24: reglas HS -> control previo (vue_rule)

Revision ID: 0013_vue_rules
Revises: 0012_warehouse_storage
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_vue_rules"
down_revision: str | None = "0012_warehouse_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vue_rule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("document_code", sa.String(48), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vue_rule_hs_prefix", "vue_rule", ["hs_prefix"])


def downgrade() -> None:
    op.drop_index("ix_vue_rule_hs_prefix", table_name="vue_rule")
    op.drop_table("vue_rule")
