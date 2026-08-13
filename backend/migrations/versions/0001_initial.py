"""Initial schema: organization, role, app_user, user_roles, audit_event

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("ruc", sa.String(13), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Guayaquil"),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "role",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "app_user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organization.id"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("keycloak_sub", sa.String(255), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("app_user.id"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("role.id"), primary_key=True),
    )

    op.create_table(
        "audit_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("service", sa.String(64), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("entity", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("session", sa.String(128), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_event_entity", "audit_event", ["entity", "entity_id"])
    op.create_index("ix_audit_event_correlation", "audit_event", ["correlation_id"])


def downgrade() -> None:
    op.drop_table("audit_event")
    op.drop_table("user_roles")
    op.drop_table("app_user")
    op.drop_table("role")
    op.drop_table("organization")
