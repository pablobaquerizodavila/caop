"""S44: guía de remisión (waybill_guide + waybill_item)

Revision ID: 0022_waybill
Revises: 0021_retention
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_waybill"
down_revision: str | None = "0021_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waybill_guide",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customs_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transporter_name", sa.String(255), nullable=False),
        sa.Column("transporter_id", sa.String(20), nullable=False),
        sa.Column("transporter_id_type", sa.String(2), nullable=False, server_default="04"),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("dir_partida", sa.String(300), nullable=False, server_default="S/N"),
        sa.Column("fecha_ini_transporte", sa.Date(), nullable=False),
        sa.Column("fecha_fin_transporte", sa.Date(), nullable=False),
        sa.Column("dest_name", sa.String(255), nullable=False),
        sa.Column("dest_id", sa.String(20), nullable=False),
        sa.Column("dest_address", sa.String(300), nullable=False, server_default="S/N"),
        sa.Column("motivo_traslado", sa.String(300), nullable=False,
                  server_default="Entrega de mercancía importada"),
        sa.Column("num_doc_sustento", sa.String(20), nullable=True),
        sa.Column("fecha_doc_sustento", sa.Date(), nullable=True),
        sa.Column("document_type", sa.String(2), nullable=False, server_default="06"),
        sa.Column("ambiente", sa.String(1), nullable=False, server_default="1"),
        sa.Column("emission_type", sa.String(1), nullable=False, server_default="1"),
        sa.Column("estab", sa.String(3), nullable=False, server_default="001"),
        sa.Column("pto_emi", sa.String(3), nullable=False, server_default="001"),
        sa.Column("secuencial", sa.String(9), nullable=False),
        sa.Column("access_key", sa.String(49), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("signed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authorization_number", sa.String(49), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("xml", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_waybill_guide_access_key", "waybill_guide", ["access_key"], unique=True)

    op.create_table(
        "waybill_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guide_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("waybill_guide.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_waybill_item_guide", "waybill_item", ["guide_id"])


def downgrade() -> None:
    op.drop_index("ix_waybill_item_guide", table_name="waybill_item")
    op.drop_table("waybill_item")
    op.drop_index("ix_waybill_guide_access_key", table_name="waybill_guide")
    op.drop_table("waybill_guide")
