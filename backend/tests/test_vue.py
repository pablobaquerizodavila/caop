"""Tests de VUE (control previo): alta, solicitud simulada, exención y gating del DAI."""

import pytest

RUC = "1712345675001"


async def _ready_case(client):
    """Crea un expediente y lo deja con readiness 100% (para probar el gating de VUE)."""
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Demo"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "AIR", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]

    # Completar todos los ítems del checklist para llegar a readiness 100%.
    detail = (await client.get(f"/api/v1/cases/{case_id}")).json()
    for it in detail["checklist"]:
        await client.patch(
            f"/api/v1/cases/{case_id}/checklist/{it['id']}", json={"status": "COMPLETE"}
        )
    detail = (await client.get(f"/api/v1/cases/{case_id}")).json()
    assert float(detail["customs_readiness_score"]) >= 100
    return case_id


@pytest.mark.asyncio
async def test_catalog_available(client):
    cat = (await client.get("/api/v1/vue/catalog")).json()
    assert any(e["entity"] == "INEN" for e in cat)


@pytest.mark.asyncio
async def test_request_approve_flow(client):
    case_id = await _ready_case(client)
    p = (await client.post(
        f"/api/v1/cases/{case_id}/vue-permits",
        json={"entity": "INEN", "document_code": "CRC", "description": "Reglamento técnico"},
    )).json()
    assert p["status"] == "REQUIRED" and p["satisfied"] is False

    approved = (await client.post(
        f"/api/v1/vue-permits/{p['id']}/request", json={"scenario": "APPROVE"}
    )).json()
    assert approved["status"] == "APPROVED"
    assert approved["satisfied"] is True
    assert approved["permit_number"] and approved["valid_until"]
    assert approved["external_ref"].startswith("VUE-SIM-")


@pytest.mark.asyncio
async def test_reject_flow_keeps_blocking(client):
    case_id = await _ready_case(client)
    p = (await client.post(
        f"/api/v1/cases/{case_id}/vue-permits",
        json={"entity": "ARCSA", "document_code": "REGISTRO_SANITARIO"},
    )).json()
    rejected = (await client.post(
        f"/api/v1/vue-permits/{p['id']}/request", json={"scenario": "REJECT"}
    )).json()
    assert rejected["status"] == "REJECTED" and rejected["satisfied"] is False
    assert rejected["error_description"]


@pytest.mark.asyncio
async def test_dai_prepare_blocked_until_vue_ok(client):
    case_id = await _ready_case(client)
    # Con readiness 100% pero SIN control previo, el DAI se puede preparar.
    ok = await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    assert ok.status_code == 201

    # Nota: para probar el gating, usamos un caso nuevo con permiso pendiente.
    case2 = await _ready_case(client)
    p = (await client.post(
        f"/api/v1/cases/{case2}/vue-permits",
        json={"entity": "AGROCALIDAD", "document_code": "AZSV"},
    )).json()
    blocked = await client.post(f"/api/v1/cases/{case2}/dai/prepare")
    assert blocked.status_code == 409
    assert "Control previo" in blocked.json()["detail"]

    # Al aprobar el permiso, el DAI ya puede prepararse.
    await client.post(f"/api/v1/vue-permits/{p['id']}/request", json={"scenario": "APPROVE"})
    unblocked = await client.post(f"/api/v1/cases/{case2}/dai/prepare")
    assert unblocked.status_code == 201


@pytest.mark.asyncio
async def test_exempt_satisfies_gating(client):
    case_id = await _ready_case(client)
    p = (await client.post(
        f"/api/v1/cases/{case_id}/vue-permits",
        json={"entity": "MSP", "document_code": "PERMISO_PREVIO"},
    )).json()
    ex = (await client.post(
        f"/api/v1/vue-permits/{p['id']}/exempt", json={"reason": "No aplica a esta mercancía"}
    )).json()
    assert ex["status"] == "EXEMPT" and ex["satisfied"] is True
    prep = await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    assert prep.status_code == 201
