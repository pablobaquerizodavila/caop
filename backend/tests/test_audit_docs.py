"""Tests de gestión documental (por expediente) y visor de auditoría."""

import pytest

from app.core.security import Principal, get_current_principal
from app.main import app

RUC = "1712345675001"
PROFORMA = b"COMMERCIAL INVOICE No: CI-1\nCurrency: USD\nTotal Amount: 100.00\n"
SUPER = lambda: Principal(subject="t", username="a", roles=["SUPER_ADMIN"])  # noqa: E731


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Demo"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


@pytest.mark.asyncio
async def test_documents_by_case(client):
    case_id = await _case(client)
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("inv.txt", PROFORMA, "text/plain")},
        data={"doc_type": "COMMERCIAL_INVOICE", "customs_case_id": case_id},
    )
    assert up.status_code == 201
    docs = (await client.get(f"/api/v1/documents?customs_case_id={case_id}")).json()
    assert len(docs) == 1
    d = docs[0]
    assert d["doc_type"] == "COMMERCIAL_INVOICE"
    assert d["versions"] and d["versions"][0]["filename"] == "inv.txt"

    # Descarga por versión (URL prefirmada).
    dv = d["versions"][0]["version"]
    dl = await client.get(f"/api/v1/documents/{d['id']}/versions/{dv}/download")
    assert dl.status_code == 200 and dl.json()["url"]


@pytest.mark.asyncio
async def test_audit_trail_and_rbac(client):
    case_id = await _case(client)  # genera múltiples inserts auditados

    # Auditor puede leer.
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="a", username="aud", roles=["AUDITOR"]
    )
    try:
        r = await client.get("/api/v1/audit?limit=500")
        assert r.status_code == 200
        events = r.json()
        assert any(e["entity"] == "customs_case" and e["action"] == "CREATE" for e in events)
        # Filtro por entidad
        cust = await client.get("/api/v1/audit?entity=customer&action=CREATE")
        assert cust.status_code == 200 and cust.json()
    finally:
        app.dependency_overrides[get_current_principal] = SUPER


@pytest.mark.asyncio
async def test_audit_forbidden_for_operator(client):
    await _case(client)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="o", username="op", roles=["OCEAN_OPERATOR"]
    )
    try:
        assert (await client.get("/api/v1/audit")).status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = SUPER
