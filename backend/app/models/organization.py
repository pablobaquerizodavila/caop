"""Organización (empresa agente de aduana). Raíz del multi-tenant ligero."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization"

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ruc: Mapped[str | None] = mapped_column(String(13), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Guayaquil")
    default_currency: Mapped[str] = mapped_column(String(3), default="USD")
