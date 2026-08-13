"""Rol y tabla de asociación usuario-rol (espejo de Keycloak para joins/reportes)."""

import uuid

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("app_user.id"), primary_key=True),
    Column("role_id", PG_UUID(as_uuid=True), ForeignKey("role.id"), primary_key=True),
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
