"""Tests de recordatorios de cobro al cliente."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _issued_settlement(client, email="cliente@demo.ec"):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    await client.post("/api/v1/notifications/templates/seed-defaults")
    cust = {"ruc": RUC, "legal_name": "Demo"}
    if email:
        cust["email"] = email
    cid = (await client.post("/api/v1/customers", json=cust)).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "100"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    return sid


@pytest.mark.asyncio
async def test_manual_reminder_sends_to_customer(client):
    sid = await _issued_settlement(client)
    r = (await client.post(f"/api/v1/settlements/{sid}/reminder")).json()
    assert r["status"] == "SENT" and r["to"] == "cliente@demo.ec"
    # last_reminder_at queda registrado
    stl = (await client.get(f"/api/v1/settlements/{sid}/payments")).json()
    assert stl["status"] == "PENDING"


@pytest.mark.asyncio
async def test_reminder_skipped_when_paid(client):
    sid = await _issued_settlement(client)
    total = (await client.get(f"/api/v1/settlements/{sid}/payments")).json()["total"]
    await client.post(
        f"/api/v1/settlements/{sid}/payments",
        json={"amount": total, "paid_at": date.today().isoformat()},
    )
    r = (await client.post(f"/api/v1/settlements/{sid}/reminder")).json()
    assert r["status"] == "SKIPPED" and "saldo" in r["reason"]


@pytest.mark.asyncio
async def test_reminder_skipped_without_email(client):
    sid = await _issued_settlement(client, email=None)
    r = (await client.post(f"/api/v1/settlements/{sid}/reminder")).json()
    assert r["status"] == "SKIPPED" and "destinatario" in r["reason"]
