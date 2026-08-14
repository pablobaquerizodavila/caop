"""Tests del auto-vínculo documento → checklist (S8)."""

import pytest

VALID_RUC = "1712345675001"


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={"tax_type": "AD_VALOREM", "hs_code": "8471.30.00", "percentage": "5",
              "base_formula": "CIF", "depends_on": [], "effective_from": "2020-01-01"},
    )
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Demo"}
    )).json()["id"]
    quote = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
             "calculation_date": "2026-01-01",
             "items": [{"hs_code": "8471.30.00", "quantity": "10", "unit_price": "100"}],
             "cost_lines": [{"category": "FEE", "estimated_amount": "200"}]}
    qid = (await client.post("/api/v1/quotes", json=quote)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case = (await client.get(f"/api/v1/quotes/{qid}/case")).json()
    return cid, case["id"]


async def _readiness(client, case_id):
    d = (await client.get(f"/api/v1/cases/{case_id}")).json()
    return float(d["customs_readiness_score"]), d


@pytest.mark.asyncio
async def test_upload_autocompletes_checklist(client):
    _, case_id = await _case(client)
    r0, _ = await _readiness(client, case_id)
    assert r0 == 0.0

    up = await client.post(
        "/api/v1/documents",
        files={"file": ("bl.pdf", b"bill of lading", "application/pdf")},
        data={"customs_case_id": case_id, "doc_type": "BILL_OF_LADING"},
    )
    assert up.status_code == 201, up.text

    r1, detail = await _readiness(client, case_id)
    assert r1 == 25.0  # 1 de 4 aplicables
    bl = next(i for i in detail["checklist"] if i["doc_type"] == "BILL_OF_LADING")
    assert bl["status"] == "COMPLETE"
    assert bl["document_id"] is not None
    types = {e["event_type"] for e in detail["events"]}
    assert "DOCUMENT_RECEIVED" in types and "CHECKLIST_AUTO_COMPLETED" in types


@pytest.mark.asyncio
async def test_unclassified_does_not_change_checklist(client):
    _, case_id = await _case(client)
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("x.pdf", b"algo", "application/pdf")},
        data={"customs_case_id": case_id},  # doc_type por defecto UNCLASSIFIED
    )
    assert up.status_code == 201
    r, _ = await _readiness(client, case_id)
    assert r == 0.0


@pytest.mark.asyncio
async def test_attach_existing_document(client):
    _, case_id = await _case(client)
    doc_id = (await client.post(
        "/api/v1/documents",
        files={"file": ("inv.pdf", b"factura", "application/pdf")},
    )).json()["id"]

    resp = await client.post(
        f"/api/v1/documents/{doc_id}/attach",
        params={"customs_case_id": case_id, "doc_type": "COMMERCIAL_INVOICE"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["matched"] is True
    r, _ = await _readiness(client, case_id)
    assert r == 25.0


@pytest.mark.asyncio
async def test_full_readiness_reaches_ready_for_customs(client):
    _, case_id = await _case(client)
    for dt in ["COMMERCIAL_INVOICE", "PACKING_LIST", "BILL_OF_LADING", "INSURANCE_POLICY"]:
        await client.post(
            "/api/v1/documents",
            files={"file": (f"{dt}.pdf", dt.encode(), "application/pdf")},
            data={"customs_case_id": case_id, "doc_type": dt},
        )
    r, detail = await _readiness(client, case_id)
    assert r == 100.0
    assert detail["current_state"] == "READY_FOR_CUSTOMS"
