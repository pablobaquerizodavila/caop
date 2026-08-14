"""S36: cobranza — pagos y vencimiento de la liquidación

Revision ID: 0017_payments
Revises: 0016_electronic_invoice
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_payments"
down_revision: str | None = "0016_electronic_invoice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("settlement", sa.Column("due_date", sa.Date(), nullable=True))
    op.create_table(
        "payment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlement.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), server_default="0"),
        sa.Column("paid_at", sa.Date(), nullable=False),
        sa.Column("method", sa.String(16), nullable=False, server_default="TRANSFER"),
        sa.Column("reference", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payment_settlement", "payment", ["settlement_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_settlement", table_name="payment")
    op.drop_table("payment")
    op.drop_column("settlement", "due_date")
