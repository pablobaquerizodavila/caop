"""Cliente de la Admin API de Keycloak para gestionar usuarios y sus roles de realm.

Es sustituible (get_kc_admin) para pruebas. La instancia real obtiene un token de
administrador (realm master, client admin-cli) y opera sobre el realm de la aplicación.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import settings


class KeycloakError(Exception):
    pass


class KeycloakAdmin(Protocol):
    async def list_users(self, search: str | None = None) -> list[dict]: ...
    async def create_user(self, data: dict) -> str: ...
    async def update_user(self, user_id: str, data: dict) -> None: ...
    async def delete_user(self, user_id: str) -> None: ...
    async def get_user_roles(self, user_id: str) -> list[str]: ...
    async def set_user_roles(self, user_id: str, roles: list[str]) -> None: ...
    async def reset_password(self, user_id: str, password: str, temporary: bool) -> None: ...
    async def list_realm_roles(self) -> list[str]: ...


class RealKeycloakAdmin:
    def __init__(self) -> None:
        self.base = settings.keycloak_admin_base.rstrip("/")
        self.realm = settings.keycloak_realm

    async def _token(self, client: httpx.AsyncClient) -> str:
        r = await client.post(
            f"{self.base}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password,
            },
        )
        if r.status_code != 200:
            raise KeycloakError(f"No se pudo autenticar con Keycloak admin ({r.status_code})")
        return r.json()["access_token"]

    def _url(self, path: str) -> str:
        return f"{self.base}/admin/realms/{self.realm}{path}"

    async def _client(self) -> httpx.AsyncClient:
        c = httpx.AsyncClient(timeout=20)
        tok = await self._token(c)
        c.headers["Authorization"] = f"Bearer {tok}"
        return c

    async def list_users(self, search: str | None = None) -> list[dict]:
        async with await self._client() as c:
            params = {"max": 200, "briefRepresentation": "true"}
            if search:
                params["search"] = search
            r = await c.get(self._url("/users"), params=params)
            r.raise_for_status()
            users = r.json()
            # roles por usuario
            roles_reps = (await c.get(self._url("/roles"))).json()
            out = []
            for u in users:
                rr = await c.get(self._url(f"/users/{u['id']}/role-mappings/realm"))
                roles = [x["name"] for x in rr.json()] if rr.status_code == 200 else []
                out.append({
                    "id": u["id"], "username": u.get("username"), "email": u.get("email"),
                    "first_name": u.get("firstName"), "last_name": u.get("lastName"),
                    "enabled": u.get("enabled", True), "roles": roles,
                })
            _ = roles_reps
            return out

    async def create_user(self, data: dict) -> str:
        async with await self._client() as c:
            body = {
                "username": data["username"], "email": data.get("email"),
                "firstName": data.get("first_name"), "lastName": data.get("last_name"),
                "enabled": True, "emailVerified": True,
            }
            r = await c.post(self._url("/users"), json=body)
            if r.status_code not in (201, 204):
                raise KeycloakError(f"No se pudo crear el usuario ({r.status_code}): {r.text[:200]}")
            # id desde Location
            loc = r.headers.get("Location", "")
            user_id = loc.rstrip("/").split("/")[-1]
            if data.get("password"):
                await self._set_password(c, user_id, data["password"], data.get("temporary", True))
            if data.get("roles"):
                await self._add_roles(c, user_id, data["roles"])
            return user_id

    async def update_user(self, user_id: str, data: dict) -> None:
        async with await self._client() as c:
            body = {}
            if "email" in data and data["email"] is not None:
                body["email"] = data["email"]
            if data.get("first_name") is not None:
                body["firstName"] = data["first_name"]
            if data.get("last_name") is not None:
                body["lastName"] = data["last_name"]
            if data.get("enabled") is not None:
                body["enabled"] = data["enabled"]
            r = await c.put(self._url(f"/users/{user_id}"), json=body)
            if r.status_code not in (204, 200):
                raise KeycloakError(f"No se pudo actualizar el usuario ({r.status_code})")

    async def delete_user(self, user_id: str) -> None:
        async with await self._client() as c:
            r = await c.delete(self._url(f"/users/{user_id}"))
            if r.status_code not in (204, 200):
                raise KeycloakError(f"No se pudo eliminar el usuario ({r.status_code})")

    async def get_user_roles(self, user_id: str) -> list[str]:
        async with await self._client() as c:
            r = await c.get(self._url(f"/users/{user_id}/role-mappings/realm"))
            r.raise_for_status()
            return [x["name"] for x in r.json()]

    async def set_user_roles(self, user_id: str, roles: list[str]) -> None:
        async with await self._client() as c:
            current = {x["name"]: x for x in
                       (await c.get(self._url(f"/users/{user_id}/role-mappings/realm"))).json()}
            desired = set(roles)
            all_roles = {x["name"]: x for x in (await c.get(self._url("/roles"))).json()}
            to_add = [all_roles[n] for n in desired - set(current) if n in all_roles]
            to_remove = [current[n] for n in set(current) - desired]
            if to_add:
                await c.post(self._url(f"/users/{user_id}/role-mappings/realm"), json=to_add)
            if to_remove:
                await c.request("DELETE", self._url(f"/users/{user_id}/role-mappings/realm"), json=to_remove)

    async def _add_roles(self, c: httpx.AsyncClient, user_id: str, roles: list[str]) -> None:
        all_roles = {x["name"]: x for x in (await c.get(self._url("/roles"))).json()}
        reps = [all_roles[n] for n in roles if n in all_roles]
        if reps:
            await c.post(self._url(f"/users/{user_id}/role-mappings/realm"), json=reps)

    async def _set_password(self, c: httpx.AsyncClient, user_id: str, password: str, temporary: bool) -> None:
        await c.put(self._url(f"/users/{user_id}/reset-password"),
                    json={"type": "password", "value": password, "temporary": temporary})

    async def reset_password(self, user_id: str, password: str, temporary: bool) -> None:
        async with await self._client() as c:
            await self._set_password(c, user_id, password, temporary)

    async def list_realm_roles(self) -> list[str]:
        async with await self._client() as c:
            r = await c.get(self._url("/roles"))
            r.raise_for_status()
            hidden = {"offline_access", "uma_authorization", "default-roles-caop"}
            return sorted(x["name"] for x in r.json() if x["name"] not in hidden)


_kc: KeycloakAdmin | None = None


def get_kc_admin() -> KeycloakAdmin:
    global _kc
    if _kc is None:
        _kc = RealKeycloakAdmin()
    return _kc


def set_kc_admin(k: KeycloakAdmin) -> None:
    global _kc
    _kc = k
