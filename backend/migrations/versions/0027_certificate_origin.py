"""S50 2B-2: certificados de origen + escenario preferencial por ítem

Revision ID: 0027_certificate_origin
Revises: 0026_trade_preferences
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_certificate_origin"
down_revision: str | None = "0026_trade_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "certificate_of_origin",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("quote_id", UUID, sa.ForeignKey("quote.id", ondelete="CASCADE"), nullable=True),
        sa.Column("customs_case_id", UUID, sa.ForeignKey("customs_case.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agreement_id", UUID, sa.ForeignKey("trade_agreement.id"), nullable=True),
        sa.Column("cert_type", sa.String(32), nullable=False, server_default="ORIGEN"),
        sa.Column("number", sa.String(64), nullable=True),
        sa.Column("issuing_country", sa.String(2), nullable=True),
        sa.Column("organism", sa.String(128), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("evidence_object_key", sa.String(512), nullable=True),
        sa.Column("validation_status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_certificate_origin_quote", "certificate_of_origin", ["quote_id"])
    op.create_index("ix_certificate_origin_status", "certificate_of_origin", ["validation_status"])

    op.add_column("quote_item", sa.Column("preference", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_item", "preference")
    op.drop_index("ix_certificate_origin_status", table_name="certificate_of_origin")
    op.drop_index("ix_certificate_origin_quote", table_name="certificate_of_origin")
    op.drop_table("certificate_of_origin")
