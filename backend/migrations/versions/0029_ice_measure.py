"""S52 Fase 2C: ICE (Impuesto a los Consumos Especiales) por subpartida

Revision ID: 0029_ice_measure
Revises: 0028_reconciliation
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029_ice_measure"
down_revision: str | None = "0028_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ice_measure",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_prefix", sa.String(12), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("method", sa.String(16), nullable=False, server_default="AD_VALOREM"),
        sa.Column("ad_valorem_pct", sa.Numeric(9, 4), nullable=True),
        sa.Column("specific_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("specific_unit", sa.String(32), nullable=True),
        sa.Column("base_type", sa.String(16), nullable=False, server_default="EX_ADUANA"),
        sa.Column("reference_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ice_measure_prefix", "ice_measure", ["hs_prefix"])
    op.create_index("ix_ice_measure_status", "ice_measure", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ice_measure_status", table_name="ice_measure")
    op.drop_index("ix_ice_measure_prefix", table_name="ice_measure")
    op.drop_table("ice_measure")
