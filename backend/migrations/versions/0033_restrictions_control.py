"""S56 (#5): restricciones y control previo vinculadas al maestro

Revision ID: 0033_restrictions_control
Revises: 0032_tariff_tier
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033_restrictions_control"
down_revision: str | None = "0032_tariff_tier"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "control_authority",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_control_authority_code", "control_authority", ["code"], unique=True)

    op.create_table(
        "control_document",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("authority_id", UUID, sa.ForeignKey("control_authority.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_control_document_code", "control_document", ["code"])

    op.create_table(
        "tariff_restriction",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default="CONTROL_PREVIO"),
        sa.Column("control_document_id", UUID, sa.ForeignKey("control_document.id"), nullable=True),
        sa.Column("authority_id", UUID, sa.ForeignKey("control_authority.id"), nullable=True),
        sa.Column("legal_instrument_id", UUID, sa.ForeignKey("legal_instrument.id"), nullable=True),
        sa.Column("requirement", sa.Text(), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_restriction_prefix", "tariff_restriction", ["hs_prefix"])
    op.create_index("ix_tariff_restriction_status", "tariff_restriction", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tariff_restriction_status", table_name="tariff_restriction")
    op.drop_index("ix_tariff_restriction_prefix", table_name="tariff_restriction")
    op.drop_table("tariff_restriction")
    op.drop_index("ix_control_document_code", table_name="control_document")
    op.drop_table("control_document")
    op.drop_index("ix_control_authority_code", table_name="control_authority")
    op.drop_table("control_authority")
