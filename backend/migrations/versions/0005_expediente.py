"""S4/S5: shipment, customs_case, case_event, requirement, checklist_item, sla_instance

Revision ID: 0005_expediente
Revises: 0004_quotes
Create Date: 2026-08-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_expediente"
down_revision: str | None = "0004_quotes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "shipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("source_quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quote.id"), nullable=True, unique=True),
        sa.Column("transport_mode", sa.String(16), nullable=True),
        sa.Column("incoterm", sa.String(3), nullable=True),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        *_ts(),
    )

    op.create_table(
        "customs_case",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_number", sa.String(32), nullable=False, unique=True),
        sa.Column("customs_regime", sa.String(8), nullable=False, server_default="10"),
        sa.Column("current_state", sa.String(32), nullable=False, server_default="CASE_CREATED"),
        sa.Column("next_expected_event", sa.String(64), nullable=True),
        sa.Column("responsible_actor", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_level", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("customs_readiness_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("blocker", sa.Text(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_customs_case_number", "customs_case", ["case_number"])

    op.create_table(
        "case_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("event_source", sa.String(24), nullable=False, server_default="SYSTEM"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("normalized_payload", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_table(
        "requirement",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("category", sa.String(24), nullable=False, server_default="SUPPORT"),
        sa.Column("applies_when", postgresql.JSONB(), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        *_ts(),
    )

    op.create_table(
        "checklist_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirement.id"), nullable=True),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("category", sa.String(24), nullable=False, server_default="SUPPORT"),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(16), nullable=False, server_default="MISSING"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
    )

    op.create_table(
        "sla_instance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(24), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone", sa.String(48), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("owner", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ON_TIME"),
        sa.Column("breach_reason", sa.String(255), nullable=True),
        *_ts(),
    )


def downgrade() -> None:
    op.drop_table("sla_instance")
    op.drop_table("checklist_item")
    op.drop_table("requirement")
    op.drop_table("case_event")
    op.drop_index("ix_customs_case_number", table_name="customs_case")
    op.drop_table("customs_case")
    op.drop_table("shipment")
