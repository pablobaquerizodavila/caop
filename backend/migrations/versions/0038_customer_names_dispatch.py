"""S65: nombre desglosado + dirección de despacho del cliente

Revision ID: 0038_customer_names_dispatch
Revises: 0037_customer_address_fields
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_customer_names_dispatch"
down_revision: str | None = "0037_customer_address_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("first_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("middle_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("last_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("second_last_name", sa.String(80), nullable=True))
    op.add_column(
        "customer",
        sa.Column("dispatch_same_as_address", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("customer", sa.Column("dispatch_country", sa.String(64), nullable=True))
    op.add_column("customer", sa.Column("dispatch_province", sa.String(64), nullable=True))
    op.add_column("customer", sa.Column("dispatch_city", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("dispatch_address", sa.String(512), nullable=True))
    op.alter_column("customer", "dispatch_same_as_address", server_default=None)


def downgrade() -> None:
    op.drop_column("customer", "dispatch_address")
    op.drop_column("customer", "dispatch_city")
    op.drop_column("customer", "dispatch_province")
    op.drop_column("customer", "dispatch_country")
    op.drop_column("customer", "dispatch_same_as_address")
    op.drop_column("customer", "second_last_name")
    op.drop_column("customer", "last_name")
    op.drop_column("customer", "middle_name")
    op.drop_column("customer", "first_name")
