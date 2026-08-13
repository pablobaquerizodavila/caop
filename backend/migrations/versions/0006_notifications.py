"""S6: notification_template, notification

Revision ID: 0006_notifications
Revises: 0005_expediente
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_notifications"
down_revision: str | None = "0005_expediente"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "notification_template",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("subject_template", sa.String(255), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )
    op.create_index("ix_notification_template_code", "notification_template", ["code"])

    op.create_table(
        "notification",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customs_case.id"), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("template_code", sa.String(48), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("to_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="QUEUED"),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        *_ts(),
    )
    op.create_index("ix_notification_customer", "notification", ["customer_id"])
    op.create_index("ix_notification_case", "notification", ["customs_case_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_case", table_name="notification")
    op.drop_index("ix_notification_customer", table_name="notification")
    op.drop_table("notification")
    op.drop_index("ix_notification_template_code", table_name="notification_template")
    op.drop_table("notification_template")
