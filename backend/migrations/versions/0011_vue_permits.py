"""S22: VUE — documentos de control previo (vue_permit)

Revision ID: 0011_vue_permits
Revises: 0010_tracking
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_vue_permits"
down_revision: str | None = "0010_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vue_permit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customs_case_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("document_code", sa.String(48), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("permit_number", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="REQUIRED"),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("external_ref", sa.String(64), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("error_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vue_permit_case", "vue_permit", ["customs_case_id"])


def downgrade() -> None:
    op.drop_index("ix_vue_permit_case", table_name="vue_permit")
    op.drop_table("vue_permit")
