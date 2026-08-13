"""S2: tax_rule (motor de reglas tributarias versionadas)

Revision ID: 0003_tax_rule
Revises: 0002_customers_documents
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_tax_rule"
down_revision: str | None = "0002_customers_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tax_rule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tax_type", sa.String(32), nullable=False),
        sa.Column("hs_code", sa.String(12), nullable=True),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("commercial_agreement", sa.String(64), nullable=True),
        sa.Column("calculation_method", sa.String(24), nullable=False, server_default="AD_VALOREM_PCT"),
        sa.Column("percentage", sa.Numeric(9, 4), nullable=True),
        sa.Column("specific_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("base_formula", sa.String(128), nullable=False, server_default="CIF"),
        sa.Column("depends_on", postgresql.JSONB(), nullable=True),
        sa.Column("exception", postgresql.JSONB(), nullable=True),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tax_rule_tax_type", "tax_rule", ["tax_type"])
    op.create_index("ix_tax_rule_hs_code", "tax_rule", ["hs_code"])


def downgrade() -> None:
    op.drop_index("ix_tax_rule_hs_code", table_name="tax_rule")
    op.drop_index("ix_tax_rule_tax_type", table_name="tax_rule")
    op.drop_table("tax_rule")
