"""Usuario interno (espejo del subject de Keycloak)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.role import Role, user_roles


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_user"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keycloak_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")
