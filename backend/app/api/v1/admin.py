"""Administración (solo SUPER_ADMIN): privilegios por rol y usuarios (Keycloak)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.role_privilege import RolePrivilege
from app.schemas.admin import (
    PasswordReset,
    RolePrivilegeCreate,
    RolePrivilegeRead,
    RolePrivilegeUpdate,
    UserCreate,
    UserRead,
    UserRolesUpdate,
    UserUpdate,
)
from app.services.keycloak_admin import KeycloakAdmin, KeycloakError, get_kc_admin
from app.services.role_seed import seed_role_privileges

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Privilegios por rol ----------
@router.get("/roles", response_model=list[RolePrivilegeRead])
async def list_roles(session: AsyncSession = Depends(get_session)) -> list[RolePrivilege]:
    return list(await session.scalars(select(RolePrivilege).order_by(RolePrivilege.role_name)))


@router.post("/roles/seed-defaults")
async def seed_roles(session: AsyncSession = Depends(get_session)) -> dict:
    return {"created": await seed_role_privileges(session)}


@router.post("/roles", response_model=RolePrivilegeRead, status_code=201)
async def create_role(
    payload: RolePrivilegeCreate, session: AsyncSession = Depends(get_session)
) -> RolePrivilege:
    exists = await session.scalar(
        select(RolePrivilege).where(RolePrivilege.role_name == payload.role_name)
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese rol ya tiene privilegios definidos")
    rp = RolePrivilege(**payload.model_dump())
    session.add(rp)
    await session.flush()
    return rp


@router.patch("/roles/{role_id}", response_model=RolePrivilegeRead)
async def update_role(
    role_id: uuid.UUID, payload: RolePrivilegeUpdate, session: AsyncSession = Depends(get_session)
) -> RolePrivilege:
    rp = await session.get(RolePrivilege, role_id)
    if rp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")
    if rp.role_name == "SUPER_ADMIN":
        raise HTTPException(status.HTTP_409_CONFLICT, "SUPER_ADMIN tiene poder total y no es editable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rp, field, value)
    await session.flush()
    return rp


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> None:
    rp = await session.get(RolePrivilege, role_id)
    if rp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rol no encontrado")
    if rp.role_name == "SUPER_ADMIN":
        raise HTTPException(status.HTTP_409_CONFLICT, "No se puede eliminar SUPER_ADMIN")
    await session.delete(rp)
    await session.flush()


# ---------- Usuarios (Keycloak) ----------
def _kc_error(exc: KeycloakError) -> HTTPException:
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"Keycloak: {exc}")


@router.get("/realm-roles", response_model=list[str])
async def realm_roles(kc: KeycloakAdmin = Depends(get_kc_admin)) -> list[str]:
    try:
        return await kc.list_realm_roles()
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.get("/users", response_model=list[UserRead])
async def list_users(
    search: str | None = Query(None), kc: KeycloakAdmin = Depends(get_kc_admin)
) -> list[dict]:
    try:
        return await kc.list_users(search)
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate, kc: KeycloakAdmin = Depends(get_kc_admin)) -> dict:
    try:
        user_id = await kc.create_user(payload.model_dump())
        return {
            "id": user_id, "username": payload.username, "email": payload.email,
            "first_name": payload.first_name, "last_name": payload.last_name,
            "enabled": True, "roles": payload.roles,
        }
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.patch("/users/{user_id}", status_code=204)
async def update_user(
    user_id: str, payload: UserUpdate, kc: KeycloakAdmin = Depends(get_kc_admin)
) -> None:
    try:
        await kc.update_user(user_id, payload.model_dump(exclude_unset=True))
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, kc: KeycloakAdmin = Depends(get_kc_admin)) -> None:
    try:
        await kc.delete_user(user_id)
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.post("/users/{user_id}/roles", status_code=204)
async def set_user_roles(
    user_id: str, payload: UserRolesUpdate, kc: KeycloakAdmin = Depends(get_kc_admin)
) -> None:
    try:
        await kc.set_user_roles(user_id, payload.roles)
    except KeycloakError as exc:
        raise _kc_error(exc) from exc


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: str, payload: PasswordReset, kc: KeycloakAdmin = Depends(get_kc_admin)
) -> None:
    try:
        await kc.reset_password(user_id, payload.password, payload.temporary)
    except KeycloakError as exc:
        raise _kc_error(exc) from exc
