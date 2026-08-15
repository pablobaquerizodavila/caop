"""S55: tarifas condicionales/por tramos (vehículos cap.87 y variables) + quote_item.attributes

Revision ID: 0032_tariff_tier
Revises: 0031_trade_remedy
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_tariff_tier"
down_revision: str | None = "0031_trade_remedy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tariff_tier",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("applies_to", sa.String(16), nullable=False, server_default="AD_VALOREM"),
        sa.Column("attribute", sa.String(24), nullable=False, server_default="CC"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("tiers", postgresql.JSONB(), nullable=False),
        sa.Column("specific_unit", sa.String(32), nullable=True),
        sa.Column("base_type", sa.String(16), nullable=False, server_default="EX_ADUANA"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_tier_prefix", "tariff_tier", ["hs_prefix"])
    op.create_index("ix_tariff_tier_status", "tariff_tier", ["status"])

    op.add_column("quote_item", sa.Column("attributes", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_item", "attributes")
    op.drop_index("ix_tariff_tier_status", table_name="tariff_tier")
    op.drop_index("ix_tariff_tier_prefix", table_name="tariff_tier")
    op.drop_table("tariff_tier")
