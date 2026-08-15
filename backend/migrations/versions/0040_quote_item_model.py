"""S71: campo modelo en el ítem de cotización

Revision ID: 0040_quote_item_model
Revises: 0039_legal_rep_name_parts
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_quote_item_model"
down_revision: str | None = "0039_legal_rep_name_parts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("quote_item", sa.Column("model", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_item", "model")
