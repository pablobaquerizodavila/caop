"""S48 Fase 1: maestro arancelario (nomenclatura, fuentes, normas, versiones)

Revision ID: 0024_tariff_master
Revises: 0023_role_privilege
Create Date: 2026-08-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_tariff_master"
down_revision: str | None = "0023_role_privilege"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "official_source",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("adapter", sa.String(64), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_official_source_code", "official_source", ["code"], unique=True)

    op.create_table(
        "legal_instrument",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("number", sa.String(64), nullable=False),
        sa.Column("organism", sa.String(128), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("registro_oficial", sa.String(64), nullable=True),
        sa.Column("supplement", sa.String(64), nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("doc_object_key", sa.String(512), nullable=True),
        sa.Column("doc_hash", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kind", "number", name="uq_legal_instrument_kind_number"),
    )

    op.create_table(
        "tariff_version",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("number", sa.String(48), nullable=False),
        sa.Column("source_id", UUID, sa.ForeignKey("official_source.id"), nullable=True),
        sa.Column("legal_instrument_id", UUID, sa.ForeignKey("legal_instrument.id"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="STAGED"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("codes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rules_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_hash", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_version_number", "tariff_version", ["number"], unique=True)
    op.create_index("ix_tariff_version_status", "tariff_version", ["status"])

    op.create_table(
        "tariff_code",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("code_normalized", sa.String(12), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("full_description", sa.Text(), nullable=True),
        sa.Column("parent_code", sa.String(12), nullable=True),
        sa.Column("physical_unit", sa.String(24), nullable=True),
        sa.Column("complementary_code", sa.String(16), nullable=True),
        sa.Column("supplementary_code", sa.String(16), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("source_id", UUID, sa.ForeignKey("official_source.id"), nullable=True),
        sa.Column("legal_instrument_id", UUID, sa.ForeignKey("legal_instrument.id"), nullable=True),
        sa.Column("tariff_version_id", UUID, sa.ForeignKey("tariff_version.id"), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ad_valorem", sa.Numeric(9, 4), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_code_code", "tariff_code", ["code"])
    op.create_index("ix_tariff_code_code_normalized", "tariff_code", ["code_normalized"])
    op.create_index("ix_tariff_code_parent_code", "tariff_code", ["parent_code"])
    op.create_index("ix_tariff_code_status", "tariff_code", ["status"])
    op.create_index("ix_tariff_code_version", "tariff_code", ["tariff_version_id"])

    op.create_table(
        "tariff_import",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("source_id", UUID, sa.ForeignKey("official_source.id"), nullable=True),
        sa.Column("tariff_version_id", UUID, sa.ForeignKey("tariff_version.id"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("raw_object_key", sa.String(512), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("parser", sa.String(64), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="FETCHED"),
        sa.Column("records_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_valid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tariff_import_status", "tariff_import", ["status"])

    # --- Extensiones aditivas a tax_rule ---
    op.add_column("tax_rule", sa.Column(
        "verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"))
    op.add_column("tax_rule", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tax_rule", sa.Column("verified_by", sa.String(128), nullable=True))
    op.add_column("tax_rule", sa.Column("tariff_code_id", UUID, sa.ForeignKey("tariff_code.id"), nullable=True))
    op.add_column("tax_rule", sa.Column("official_source_id", UUID, sa.ForeignKey("official_source.id"), nullable=True))
    op.add_column("tax_rule", sa.Column("tariff_version_id", UUID, sa.ForeignKey("tariff_version.id"), nullable=True))
    op.create_index("ix_tax_rule_verification_status", "tax_rule", ["verification_status"])
    op.create_index("ix_tax_rule_tariff_code_id", "tax_rule", ["tariff_code_id"])
    op.create_index("ix_tax_rule_tariff_version_id", "tax_rule", ["tariff_version_id"])

    # Reclasificar reglas existentes sin verificación como UNVERIFIED (defecto crítico corregido).
    op.execute(
        "UPDATE tax_rule SET verification_status='VERIFIED' WHERE last_verified_at IS NOT NULL"
    )

    # --- Extensiones aditivas a quote_item ---
    op.add_column("quote_item", sa.Column(
        "hs_validation", sa.String(16), nullable=False, server_default="UNKNOWN"))
    op.add_column("quote_item", sa.Column("tariff_code_id", UUID, sa.ForeignKey("tariff_code.id"), nullable=True))
    op.add_column("quote_item", sa.Column(
        "tax_complete", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("quote_item", sa.Column("tax_warnings", postgresql.JSONB(), nullable=True))
    op.add_column("quote_item", sa.Column("tax_data_version", sa.String(48), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_item", "tax_data_version")
    op.drop_column("quote_item", "tax_warnings")
    op.drop_column("quote_item", "tax_complete")
    op.drop_column("quote_item", "tariff_code_id")
    op.drop_column("quote_item", "hs_validation")

    op.drop_index("ix_tax_rule_tariff_version_id", table_name="tax_rule")
    op.drop_index("ix_tax_rule_tariff_code_id", table_name="tax_rule")
    op.drop_index("ix_tax_rule_verification_status", table_name="tax_rule")
    for col in ("tariff_version_id", "official_source_id", "tariff_code_id",
                "verified_by", "verified_at", "verification_status"):
        op.drop_column("tax_rule", col)

    op.drop_index("ix_tariff_import_status", table_name="tariff_import")
    op.drop_table("tariff_import")
    for idx in ("ix_tariff_code_version", "ix_tariff_code_status", "ix_tariff_code_parent_code",
                "ix_tariff_code_code_normalized", "ix_tariff_code_code"):
        op.drop_index(idx, table_name="tariff_code")
    op.drop_table("tariff_code")
    op.drop_index("ix_tariff_version_status", table_name="tariff_version")
    op.drop_index("ix_tariff_version_number", table_name="tariff_version")
    op.drop_table("tariff_version")
    op.drop_table("legal_instrument")
    op.drop_index("ix_official_source_code", table_name="official_source")
    op.drop_table("official_source")
