"""S47: privilegios por rol editables (role_privilege)

Revision ID: 0023_role_privilege
Revises: 0022_waybill
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_role_privilege"
down_revision: str | None = "0022_waybill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_privilege",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_name", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_write", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_sign", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_audit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_role_privilege_role_name", "role_privilege", ["role_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_role_privilege_role_name", table_name="role_privilege")
    op.drop_table("role_privilege")
