"""Privilegios por rol, editables desde la base de datos.

El RBAC consulta esta tabla para decidir capacidades. Si un rol no está en la tabla,
se usa un fallback en código. SUPER_ADMIN siempre tiene poder total (no editable).
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RolePrivilege(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_privilege"

    role_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)   # accede a la API operativa
    can_write: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # escritura
    can_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # configuración
    can_sign: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)   # firmar DAI
    can_audit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # auditoría
