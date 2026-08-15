"""S61: cliente con tipo (natural/empresa) + representante legal

Revision ID: 0036_customer_legal_rep
Revises: 0035_tariff_change
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_customer_legal_rep"
down_revision: str | None = "0035_tariff_change"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer",
        sa.Column("entity_type", sa.String(16), nullable=False, server_default="NATURAL"),
    )
    op.add_column("customer", sa.Column("legal_rep_name", sa.String(255), nullable=True))
    op.add_column("customer", sa.Column("legal_rep_id", sa.String(20), nullable=True))
    # Quita el server_default tras rellenar filas existentes: el default queda en la app.
    op.alter_column("customer", "entity_type", server_default=None)


def downgrade() -> None:
    op.drop_column("customer", "legal_rep_id")
    op.drop_column("customer", "legal_rep_name")
    op.drop_column("customer", "entity_type")
