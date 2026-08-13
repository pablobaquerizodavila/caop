"""Tests del flujo estrella: cotización aceptada → expediente (S4/S5)."""

import pytest

VALID_RUC = "1712345675001"


async def _setup(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={"tax_type": "AD_VALOREM", "hs_code": "8471.30.00", "percentage": "5",
              "base_formula": "CIF", "depends_on": [], "effective_from": "2020-01-01"},
    )
    await client.post("/api/v1/requirements/seed-defaults")
    cust = await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Importadora Demo"}
    )
    return cust.json()["id"]


def _quote(customer_id):
    return {
        "customer_id": customer_id,
        "transport_mode": "OCEAN",
        "incoterm": "FOB",
        "origin_country": "CN",
        "calculation_date": "2026-01-01",
        "total_freight": "100",
        "total_insurance": "10",
        "items": [{"description": "Laptop stand", "hs_code": "8471.30.00",
                   "quantity": "10", "unit_price": "100"}],
        "cost_lines": [{"category": "FEE", "estimated_amount": "200", "confidence": "HIGH"}],
    }


async def _accept(client, customer_id):
    qid = (await client.post("/api/v1/quotes", json=_quote(customer_id))).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    acc = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    assert acc.status_code == 200, acc.text
    return qid


@pytest.mark.asyncio
async def test_accept_creates_expediente(client):
    cid = await _setup(client)
    qid = await _accept(client, cid)

    case_resp = await client.get(f"/api/v1/quotes/{qid}/case")
    assert case_resp.status_code == 200, case_resp.text
    case = case_resp.json()
    assert case["case_number"].startswith("EC-IMP-2026-")
    assert case["customs_regime"] == "10"
    assert case["current_state"] == "AWAITING_DOCUMENTS"
    assert float(case["customs_readiness_score"]) == 0.0

    detail = (await client.get(f"/api/v1/cases/{case['id']}")).json()
    doc_types = {i["doc_type"] for i in detail["checklist"]}
    # OCEAN sin acuerdo: factura, packing, BL, seguro (no certificado de origen)
    assert {"COMMERCIAL_INVOICE", "PACKING_LIST", "BILL_OF_LADING", "INSURANCE_POLICY"} == doc_types
    assert "CERTIFICATE_OF_ORIGIN" not in doc_types
    assert any(e["event_type"] == "CASE_CREATED" for e in detail["events"])
    assert any(s["milestone"] == "DOCUMENTS_COMPLETE" for s in detail["sla"])


@pytest.mark.asyncio
async def test_accept_without_customer_blocked(client):
    await _setup(client)
    payload = _quote(None)
    payload["customer_id"] = None
    qid = (await client.post("/api/v1/quotes", json=payload)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    resp = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_conversion_idempotent(client):
    cid = await _setup(client)
    qid = await _accept(client, cid)
    c1 = (await client.get(f"/api/v1/quotes/{qid}/case")).json()
    c2 = (await client.post(f"/api/v1/quotes/{qid}/convert")).json()
    assert c1["id"] == c2["id"]  # no crea un segundo expediente


@pytest.mark.asyncio
async def test_readiness_rises_as_documents_complete(client):
    cid = await _setup(client)
    qid = await _accept(client, cid)
    case = (await client.get(f"/api/v1/quotes/{qid}/case")).json()
    detail = (await client.get(f"/api/v1/cases/{case['id']}")).json()

    items = detail["checklist"]
    total = len(items)
    for idx, it in enumerate(items, start=1):
        upd = await client.patch(
            f"/api/v1/cases/{case['id']}/checklist/{it['id']}", json={"status": "COMPLETE"}
        )
        assert upd.status_code == 200
        expected = round(idx / total * 100, 2)
        assert float(upd.json()["customs_readiness_score"]) == expected

    final = (await client.get(f"/api/v1/cases/{case['id']}")).json()
    assert float(final["customs_readiness_score"]) == 100.0
    assert final["current_state"] == "READY_FOR_CUSTOMS"
