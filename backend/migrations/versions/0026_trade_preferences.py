"""S50 Fase 2B: preferencias arancelarias (país, acuerdo, preferencia)

Revision ID: 0026_trade_preferences
Revises: 0025_widen_hs_code
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_trade_preferences"
down_revision: str | None = "0025_widen_hs_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "country",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("iso2", sa.String(2), nullable=False),
        sa.Column("iso3", sa.String(3), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_country_iso2", "country", ["iso2"], unique=True)

    op.create_table(
        "trade_agreement",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default="FTA"),
        sa.Column("members", postgresql.JSONB(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trade_agreement_code", "trade_agreement", ["code"], unique=True)
    op.create_index("ix_trade_agreement_status", "trade_agreement", ["status"])

    op.create_table(
        "tariff_preference",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("agreement_id", UUID, sa.ForeignKey("trade_agreement.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("hs_prefix", sa.String(12), nullable=True),
        sa.Column("liberation_pct", sa.Numeric(6, 3), nullable=False, server_default="100"),
        sa.Column("preferential_rate", sa.Numeric(9, 4), nullable=True),
        sa.Column("requires_certificate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
        sa.Column("legal_source", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_preference_origin", "tariff_preference", ["origin_country"])
    op.create_index("ix_tariff_preference_prefix", "tariff_preference", ["hs_prefix"])
    op.create_index("ix_tariff_preference_status", "tariff_preference", ["status"])


def downgrade() -> None:
    op.drop_table("tariff_preference")
    op.drop_index("ix_trade_agreement_status", table_name="trade_agreement")
    op.drop_index("ix_trade_agreement_code", table_name="trade_agreement")
    op.drop_table("trade_agreement")
    op.drop_index("ix_country_iso2", table_name="country")
    op.drop_table("country")
