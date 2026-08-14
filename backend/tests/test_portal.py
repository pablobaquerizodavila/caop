"""Tests del portal del cliente: alcance por cliente, aislamiento y bloqueo del staff."""

import pytest

from app.core.security import Principal, get_current_principal
from app.main import app

SUPER = lambda: Principal(subject="t", username="admin", roles=["SUPER_ADMIN"])  # noqa: E731


def _ruc(base9: str) -> str:
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    s = 0
    for c, d in zip(coef, (int(x) for x in base9)):
        p = c * d
        s += p - 9 if p > 9 else p
    return f"{base9}{(10 - s % 10) % 10}001"


def _as_customer(email: str):
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="c", username="cli", email=email, roles=["CUSTOMER"]
    )


async def _customer_with_case(client, ruc: str, email: str):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": ruc, "legal_name": "Cli", "email": email}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    return cid, case_id


@pytest.mark.asyncio
async def test_portal_scoped_and_staff_blocked(client):
    _cid, case_id = await _customer_with_case(client, _ruc("171234567"), "cliente@demo.ec")
    _as_customer("cliente@demo.ec")
    try:
        me = (await client.get("/api/v1/portal/me")).json()
        assert me["linked"] is True and me["cases"] >= 1

        cases = (await client.get("/api/v1/portal/cases")).json()
        assert any(c["id"] == case_id for c in cases)

        detail = await client.get(f"/api/v1/portal/cases/{case_id}")
        assert detail.status_code == 200
        assert detail.json()["track"]["reference"]

        # El rol CUSTOMER NO accede a la API del staff.
        assert (await client.get("/api/v1/cases")).status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_portal_isolation_between_customers(client):
    _a, case_a = await _customer_with_case(client, _ruc("171234567"), "a@demo.ec")
    _b, case_b = await _customer_with_case(client, _ruc("171234568"), "b@demo.ec")
    _as_customer("b@demo.ec")
    try:
        # B ve su caso pero NO el de A.
        assert (await client.get(f"/api/v1/portal/cases/{case_b}")).status_code == 200
        assert (await client.get(f"/api/v1/portal/cases/{case_a}")).status_code == 404
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_portal_unlinked_account(client):
    _as_customer("desconocido@nadie.ec")
    try:
        me = (await client.get("/api/v1/portal/me")).json()
        assert me["linked"] is False
        assert (await client.get("/api/v1/portal/cases")).status_code == 404
    finally:
        app.dependency_overrides[get_current_principal] = SUPER
