"""S53: Sistema Andino de Franja de Precios (SAFP)

Revision ID: 0030_price_band
Revises: 0029_ice_measure
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_price_band"
down_revision: str | None = "0029_ice_measure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "price_band_measure",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("product", sa.String(128), nullable=False),
        sa.Column("is_marker", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_price_band_measure_prefix", "price_band_measure", ["hs_prefix"])
    op.create_index("ix_price_band_measure_status", "price_band_measure", ["status"])

    op.create_table(
        "price_band_period",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("measure_id", UUID, sa.ForeignKey("price_band_measure.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("reference_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("floor_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("ceiling_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("variable_method", sa.String(16), nullable=False, server_default="AD_VALOREM"),
        sa.Column("variable_value", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("specific_unit", sa.String(32), nullable=True),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_price_band_period_measure", "price_band_period", ["measure_id"])


def downgrade() -> None:
    op.drop_index("ix_price_band_period_measure", table_name="price_band_period")
    op.drop_table("price_band_period")
    op.drop_index("ix_price_band_measure_status", table_name="price_band_measure")
    op.drop_index("ix_price_band_measure_prefix", table_name="price_band_measure")
    op.drop_table("price_band_measure")
