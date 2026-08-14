"""S19: transporte en shipment + tabla container

Revision ID: 0009_ocean_containers
Revises: 0008_customs_declaration
Create Date: 2026-08-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_ocean_containers"
down_revision: str | None = "0008_customs_declaration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLS = [
    ("load_type", sa.String(8)),
    ("carrier", sa.String(128)),
    ("mbl_number", sa.String(64)),
    ("hbl_number", sa.String(64)),
    ("mawb_number", sa.String(64)),
    ("hawb_number", sa.String(64)),
    ("vessel", sa.String(128)),
    ("voyage", sa.String(32)),
    ("flight_number", sa.String(32)),
    ("pol", sa.String(64)),
    ("pod", sa.String(64)),
    ("etd", sa.Date()),
    ("eta", sa.Date()),
    ("ata", sa.Date()),
]


def upgrade() -> None:
    for name, col_type in _COLS:
        op.add_column("shipment", sa.Column(name, col_type, nullable=True))

    op.create_table(
        "container",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False),
        sa.Column("container_number", sa.String(16), nullable=False),
        sa.Column("iso_type", sa.String(8), nullable=True),
        sa.Column("size", sa.String(8), nullable=True),
        sa.Column("seal", sa.String(32), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="IN_TRANSIT"),
        sa.Column("arrival_date", sa.Date(), nullable=True),
        sa.Column("free_days", sa.Integer(), nullable=True),
        sa.Column("daily_rate", sa.Numeric(18, 2), server_default="0"),
        sa.Column("gate_out_date", sa.Date(), nullable=True),
        sa.Column("empty_return_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_container_shipment", "container", ["shipment_id"])


def downgrade() -> None:
    op.drop_index("ix_container_shipment", table_name="container")
    op.drop_table("container")
    for name, _ in _COLS:
        op.drop_column("shipment", name)
