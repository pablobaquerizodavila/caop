"""S54: medidas de defensa comercial (antidumping/salvaguardia/compensatorio)

Revision ID: 0031_trade_remedy
Revises: 0030_price_band
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031_trade_remedy"
down_revision: str | None = "0030_price_band"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_remedy",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("exporter", sa.String(255), nullable=True),
        sa.Column("product", sa.String(255), nullable=True),
        sa.Column("method", sa.String(16), nullable=False, server_default="AD_VALOREM"),
        sa.Column("ad_valorem_pct", sa.Numeric(9, 4), nullable=True),
        sa.Column("specific_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("specific_unit", sa.String(32), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trade_remedy_kind", "trade_remedy", ["kind"])
    op.create_index("ix_trade_remedy_prefix", "trade_remedy", ["hs_prefix"])
    op.create_index("ix_trade_remedy_origin", "trade_remedy", ["origin_country"])
    op.create_index("ix_trade_remedy_status", "trade_remedy", ["status"])


def downgrade() -> None:
    for idx in ("ix_trade_remedy_status", "ix_trade_remedy_origin",
                "ix_trade_remedy_prefix", "ix_trade_remedy_kind"):
        op.drop_index(idx, table_name="trade_remedy")
    op.drop_table("trade_remedy")
