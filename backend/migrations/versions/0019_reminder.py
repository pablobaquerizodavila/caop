"""S40: recordatorio de cobro — last_reminder_at en la liquidación

Revision ID: 0019_reminder
Revises: 0018_credit_note
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_reminder"
down_revision: str | None = "0018_credit_note"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("settlement", sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("settlement", "last_reminder_at")
