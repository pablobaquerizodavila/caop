"""S48 Fase 1: ensanchar hs_code a 16 (subpartida con puntos = 13 caracteres)

Revision ID: 0025_widen_hs_code
Revises: 0024_tariff_master
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_widen_hs_code"
down_revision: str | None = "0024_tariff_master"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # "dddd.dd.dd.dd" (subpartida nacional con puntos) = 13 caracteres > 12.
    op.alter_column("tax_rule", "hs_code", type_=sa.String(16), existing_type=sa.String(12))
    op.alter_column("quote_item", "hs_code", type_=sa.String(16), existing_type=sa.String(12))


def downgrade() -> None:
    op.alter_column("quote_item", "hs_code", type_=sa.String(12), existing_type=sa.String(16))
    op.alter_column("tax_rule", "hs_code", type_=sa.String(12), existing_type=sa.String(16))
