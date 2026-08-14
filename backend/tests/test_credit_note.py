"""Tests de notas de crédito SRI (modo simulador)."""

import pytest

RUC = "1712345675001"


async def _authorized_invoice(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo S.A."}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "description": "Honorarios", "estimated_amount": "150"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    inv = (await client.post(f"/api/v1/settlements/{sid}/invoice")).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/authorize", json={"scenario": "AUTHORIZE"})
    return inv


@pytest.mark.asyncio
async def test_credit_note_requires_authorized_invoice(client):
    # Factura en DRAFT (sin autorizar) -> no se puede acreditar.
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post("/api/v1/customers", json={"ruc": RUC, "legal_name": "D"})).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "150"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    inv = (await client.post(f"/api/v1/settlements/{sid}/invoice")).json()
    r = await client.post(f"/api/v1/invoices/{inv['id']}/credit-notes", json={"motivo": "x"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_full_credit_note_and_authorize(client):
    inv = await _authorized_invoice(client)
    cn = (await client.post(
        f"/api/v1/invoices/{inv['id']}/credit-notes",
        json={"motivo": "Anulación por error"},
    )).json()
    assert cn["document_type"] == "04"
    assert cn["total"] == inv["total"]  # crédito total
    assert len(cn["access_key"]) == 49 and cn["access_key"].isdigit()

    xml = (await client.get(f"/api/v1/credit-notes/{cn['id']}/xml")).text
    assert "<notaCredito" in xml and "<codDocModificado>01</codDocModificado>" in xml
    assert f"{inv['estab']}-{inv['pto_emi']}-{inv['secuencial']}" in xml
    assert "Anulación por error" in xml

    auth = (await client.post(
        f"/api/v1/credit-notes/{cn['id']}/authorize", json={"scenario": "AUTHORIZE"}
    )).json()
    assert auth["status"] == "AUTHORIZED" and auth["authorization_number"] == cn["access_key"]

    listed = (await client.get(f"/api/v1/invoices/{inv['id']}/credit-notes")).json()
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_partial_credit_note(client):
    inv = await _authorized_invoice(client)
    cn = (await client.post(
        f"/api/v1/invoices/{inv['id']}/credit-notes",
        json={"amount": 57.5, "motivo": "Devolución parcial"},
    )).json()
    assert cn["total"] == 57.5
    # base + IVA = total
    assert round(cn["subtotal"] + cn["tax_amount"], 2) == 57.5


@pytest.mark.asyncio
async def test_credit_note_amount_cannot_exceed_invoice(client):
    inv = await _authorized_invoice(client)
    r = await client.post(
        f"/api/v1/invoices/{inv['id']}/credit-notes",
        json={"amount": inv["total"] + 100, "motivo": "x"},
    )
    assert r.status_code == 409
