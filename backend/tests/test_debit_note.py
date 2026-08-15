"""Tests de notas de débito SRI (modo simulador)."""

import pytest

RUC = "1712345675001"


async def _authorized_invoice(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo S.A."}
    )).json()["id"]
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
    await client.post(f"/api/v1/invoices/{inv['id']}/authorize", json={"scenario": "AUTHORIZE"})
    return inv


@pytest.mark.asyncio
async def test_debit_note_requires_authorized_invoice(client):
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
    r = await client.post(f"/api/v1/invoices/{inv['id']}/debit-notes",
                          json={"amount": 20, "motivo": "Interés"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_and_authorize_debit_note(client):
    inv = await _authorized_invoice(client)
    dn = (await client.post(
        f"/api/v1/invoices/{inv['id']}/debit-notes",
        json={"amount": 23, "motivo": "Interés por mora"},
    )).json()
    assert dn["document_type"] == "05" and dn["total"] == 23.0
    assert round(dn["subtotal"] + dn["tax_amount"], 2) == 23.0
    assert len(dn["access_key"]) == 49 and dn["access_key"].isdigit()

    xml = (await client.get(f"/api/v1/debit-notes/{dn['id']}/xml")).text
    assert "<notaDebito" in xml and "<infoNotaDebito>" in xml
    assert "<motivos>" in xml and "Interés por mora" in xml
    assert f"{inv['estab']}-{inv['pto_emi']}-{inv['secuencial']}" in xml

    auth = (await client.post(
        f"/api/v1/debit-notes/{dn['id']}/authorize", json={"scenario": "AUTHORIZE"}
    )).json()
    assert auth["status"] == "AUTHORIZED" and auth["authorization_number"] == dn["access_key"]

    listed = (await client.get(f"/api/v1/invoices/{inv['id']}/debit-notes")).json()
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_debit_note_amount_must_be_positive(client):
    inv = await _authorized_invoice(client)
    r = await client.post(f"/api/v1/invoices/{inv['id']}/debit-notes",
                          json={"amount": 0, "motivo": "x"})
    assert r.status_code == 409
