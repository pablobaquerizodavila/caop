"""Tests de RBAC: lectura abierta a autenticados, escritura y config por rol."""

import pytest

from app.core.security import Principal, get_current_principal
from app.main import app

RUC = "1712345675001"
SUPER = lambda: Principal(subject="t", username="admin", roles=["SUPER_ADMIN"])  # noqa: E731


def _as(roles: list[str]):
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="u", username="u", roles=roles
    )


@pytest.mark.asyncio
async def test_viewer_reads_but_cannot_write(client):
    _as(["AUDITOR"])  # rol de solo lectura
    try:
        assert (await client.get("/api/v1/cases")).status_code == 200
        w = await client.post("/api/v1/customers", json={"ruc": RUC, "legal_name": "X"})
        assert w.status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_operator_writes_but_not_admin_config(client):
    _as(["OCEAN_OPERATOR"])  # puede operar, no administrar config
    try:
        created = await client.post("/api/v1/customers", json={"ruc": RUC, "legal_name": "Op"})
        assert created.status_code == 201  # escritura operativa permitida
        # Reglas HS→VUE son configuración: solo administración.
        assert (await client.get("/api/v1/vue/rules")).status_code == 200  # lectura ok
        blocked = await client.post(
            "/api/v1/vue/rules",
            json={"hs_prefix": "33", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO"},
        )
        assert blocked.status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_admin_can_manage_config(client):
    _as(["OPERATIONS_MANAGER"])
    try:
        r = await client.post(
            "/api/v1/vue/rules",
            json={"hs_prefix": "8471", "entity": "INEN", "document_code": "CRC"},
        )
        assert r.status_code == 201
    finally:
        app.dependency_overrides[get_current_principal] = SUPER
