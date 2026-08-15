"""S63: dirección estructurada del cliente (país/provincia/ciudad)

Revision ID: 0037_customer_address_fields
Revises: 0036_customer_legal_rep
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_customer_address_fields"
down_revision: str | None = "0036_customer_legal_rep"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer",
        sa.Column("country", sa.String(64), nullable=False, server_default="Ecuador"),
    )
    op.add_column("customer", sa.Column("province", sa.String(64), nullable=True))
    op.add_column("customer", sa.Column("city", sa.String(80), nullable=True))
    op.alter_column("customer", "country", server_default=None)


def downgrade() -> None:
    op.drop_column("customer", "city")
    op.drop_column("customer", "province")
    op.drop_column("customer", "country")
