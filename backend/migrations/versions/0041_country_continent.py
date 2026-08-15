"""S73: continente en el catálogo de países

Revision ID: 0041_country_continent
Revises: 0040_quote_item_model
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_country_continent"
down_revision: str | None = "0040_quote_item_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("country", sa.Column("continent", sa.String(24), nullable=True))
    op.create_index("ix_country_continent", "country", ["continent"])


def downgrade() -> None:
    op.drop_index("ix_country_continent", table_name="country")
    op.drop_column("country", "continent")
