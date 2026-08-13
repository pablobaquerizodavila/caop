"""S3: quote, quote_item, cost_line, quote_status_history

Revision ID: 0004_quotes
Revises: 0003_tax_rule
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_quotes"
down_revision: str | None = "0003_tax_rule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(18, 4)


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "quote",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_number", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=True),
        sa.Column("transport_mode", sa.String(16), nullable=True),
        sa.Column("load_type", sa.String(16), nullable=True),
        sa.Column("incoterm", sa.String(3), nullable=True),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("exchange_rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("exchange_rate_date", sa.Date(), nullable=True),
        sa.Column("calculation_date", sa.Date(), nullable=False),
        sa.Column("expected_import_date", sa.Date(), nullable=True),
        sa.Column("total_units", MONEY, server_default="0"),
        sa.Column("total_cif", MONEY, server_default="0"),
        sa.Column("total_taxes", MONEY, server_default="0"),
        sa.Column("customer_price_total", MONEY, server_default="0"),
        sa.Column("internal_cost_total", MONEY, server_default="0"),
        sa.Column("margin_amount", MONEY, server_default="0"),
        sa.Column("margin_pct", sa.Numeric(9, 4), server_default="0"),
        sa.Column("landed_cost_total", MONEY, server_default="0"),
        sa.Column("landed_cost_per_unit", sa.Numeric(18, 6), server_default="0"),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("pdf_object_key", sa.String(512), nullable=True),
        sa.Column("disclaimer_version", sa.String(16), server_default="v1"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_quote_number", "quote", ["quote_number"])

    op.create_table(
        "quote_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quote.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hs_code", sa.String(12), nullable=True),
        sa.Column("hs_status", sa.String(16), server_default="PRELIMINARY"),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("commercial_agreement", sa.String(64), nullable=True),
        sa.Column("quantity", MONEY, server_default="1"),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 6), server_default="0"),
        sa.Column("line_value", MONEY, server_default="0"),
        sa.Column("weight", MONEY, nullable=True),
        sa.Column("freight_alloc", MONEY, server_default="0"),
        sa.Column("insurance_alloc", MONEY, server_default="0"),
        sa.Column("cif_value", MONEY, server_default="0"),
        sa.Column("taxes_total", MONEY, server_default="0"),
        sa.Column("tax_breakdown", postgresql.JSONB(), nullable=True),
        *_ts(),
    )

    op.create_table(
        "cost_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quote.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("estimated_amount", MONEY, server_default="0"),
        sa.Column("contingency_pct", sa.Numeric(9, 4), server_default="0"),
        sa.Column("quoted_amount", MONEY, server_default="0"),
        sa.Column("confidence", sa.String(16), server_default="MEDIUM"),
        sa.Column("is_included", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )

    op.create_table(
        "quote_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quote.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("channel", sa.String(16), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("quote_status_history")
    op.drop_table("cost_line")
    op.drop_table("quote_item")
    op.drop_index("ix_quote_number", table_name="quote")
    op.drop_table("quote")
