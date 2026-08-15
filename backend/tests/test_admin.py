"""Tests de administración: privilegios editables, RBAC desde BD y usuarios (Keycloak fake)."""

import pytest

from app.core.security import Principal, get_current_principal
from app.main import app
from app.services.keycloak_admin import get_kc_admin

RUC = "1712345675001"
SUPER = lambda: Principal(subject="t", username="admin", roles=["SUPER_ADMIN"])  # noqa: E731


def _as(roles):
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="u", username="u", roles=roles
    )


class FakeKC:
    def __init__(self):
        self.users: dict = {}
        self.roles = ["SUPER_ADMIN", "OCEAN_OPERATOR", "CUSTOMER", "AUDITOR"]

    async def list_users(self, search=None):
        return list(self.users.values())

    async def create_user(self, data):
        uid = "u-" + data["username"]
        self.users[uid] = {
            "id": uid, "username": data["username"], "email": data.get("email"),
            "first_name": data.get("first_name"), "last_name": data.get("last_name"),
            "enabled": True, "roles": data.get("roles", []),
        }
        return uid

    async def update_user(self, uid, data):
        self.users[uid].update(data)

    async def delete_user(self, uid):
        self.users.pop(uid, None)

    async def get_user_roles(self, uid):
        return self.users[uid]["roles"]

    async def set_user_roles(self, uid, roles):
        self.users[uid]["roles"] = roles

    async def reset_password(self, uid, password, temporary):
        pass

    async def list_realm_roles(self):
        return self.roles


@pytest.mark.asyncio
async def test_editable_privileges_drive_rbac(client):
    # SUPER_ADMIN siembra la matriz de privilegios.
    seeded = (await client.post("/api/v1/admin/roles/seed-defaults")).json()
    assert "OCEAN_OPERATOR" in seeded["created"]

    # Con privilegio de escritura, OCEAN_OPERATOR puede escribir.
    _as(["OCEAN_OPERATOR"])
    try:
        w = await client.post("/api/v1/customers", json={"ruc": RUC, "legal_name": "X"})
        assert w.status_code == 201
    finally:
        app.dependency_overrides[get_current_principal] = SUPER

    # El super admin quita el privilegio de escritura a OCEAN_OPERATOR.
    roles = (await client.get("/api/v1/admin/roles")).json()
    oo = next(r for r in roles if r["role_name"] == "OCEAN_OPERATOR")
    upd = await client.patch(f"/api/v1/admin/roles/{oo['id']}", json={"can_write": False})
    assert upd.status_code == 200 and upd.json()["can_write"] is False

    # Ahora OCEAN_OPERATOR ya NO puede escribir, pero sí leer.
    _as(["OCEAN_OPERATOR"])
    try:
        assert (await client.get("/api/v1/cases")).status_code == 200
        blocked = await client.post(
            "/api/v1/customers", json={"ruc": "1790012345001", "legal_name": "Y"}
        )
        assert blocked.status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_super_admin_row_protected(client):
    await client.post("/api/v1/admin/roles/seed-defaults")
    roles = (await client.get("/api/v1/admin/roles")).json()
    sa = next(r for r in roles if r["role_name"] == "SUPER_ADMIN")
    assert (await client.patch(f"/api/v1/admin/roles/{sa['id']}", json={"can_admin": False})).status_code == 409
    assert (await client.delete(f"/api/v1/admin/roles/{sa['id']}")).status_code == 409


@pytest.mark.asyncio
async def test_admin_only_super(client):
    _as(["OPERATIONS_MANAGER"])
    try:
        assert (await client.get("/api/v1/admin/roles")).status_code == 403
        assert (await client.get("/api/v1/admin/users")).status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_user_management(client):
    fake = FakeKC()
    app.dependency_overrides[get_kc_admin] = lambda: fake
    try:
        roles = (await client.get("/api/v1/admin/realm-roles")).json()
        assert "OCEAN_OPERATOR" in roles

        created = (await client.post("/api/v1/admin/users", json={
            "username": "jperez", "email": "j@demo.ec", "password": "Temp123!",
            "roles": ["OCEAN_OPERATOR"],
        })).json()
        uid = created["id"]
        assert created["username"] == "jperez"

        listed = (await client.get("/api/v1/admin/users")).json()
        assert any(u["id"] == uid for u in listed)

        assert (await client.post(f"/api/v1/admin/users/{uid}/roles",
                                  json={"roles": ["AUDITOR"]})).status_code == 204
        assert fake.users[uid]["roles"] == ["AUDITOR"]

        assert (await client.delete(f"/api/v1/admin/users/{uid}")).status_code == 204
        assert uid not in fake.users
    finally:
        app.dependency_overrides.pop(get_kc_admin, None)
