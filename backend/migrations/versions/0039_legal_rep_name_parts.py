"""S68: nombre del representante legal desglosado

Revision ID: 0039_legal_rep_name_parts
Revises: 0038_customer_names_dispatch
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_legal_rep_name_parts"
down_revision: str | None = "0038_customer_names_dispatch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("legal_rep_first_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("legal_rep_middle_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("legal_rep_last_name", sa.String(80), nullable=True))
    op.add_column("customer", sa.Column("legal_rep_second_last_name", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("customer", "legal_rep_second_last_name")
    op.drop_column("customer", "legal_rep_last_name")
    op.drop_column("customer", "legal_rep_middle_name")
    op.drop_column("customer", "legal_rep_first_name")
