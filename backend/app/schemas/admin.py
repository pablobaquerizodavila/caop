"""Schemas de administración: privilegios por rol y usuarios."""

import uuid

from pydantic import BaseModel, ConfigDict


class RolePrivilegeCreate(BaseModel):
    role_name: str
    description: str | None = None
    is_staff: bool = True
    can_write: bool = False
    can_admin: bool = False
    can_sign: bool = False
    can_audit: bool = False


class RolePrivilegeUpdate(BaseModel):
    description: str | None = None
    is_staff: bool | None = None
    can_write: bool | None = None
    can_admin: bool | None = None
    can_sign: bool | None = None
    can_audit: bool | None = None


class RolePrivilegeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role_name: str
    description: str | None
    is_staff: bool
    can_write: bool
    can_admin: bool
    can_sign: bool
    can_audit: bool


# --- Usuarios (Keycloak) ---
class UserRead(BaseModel):
    id: str
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool = True
    roles: list[str] = []


class UserCreate(BaseModel):
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str
    temporary: bool = True
    roles: list[str] = []


class UserUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool | None = None


class UserRolesUpdate(BaseModel):
    roles: list[str]


class PasswordReset(BaseModel):
    password: str
    temporary: bool = True
