"""Tests de alertas proactivas: recopilación de excepciones y envío del digest."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    await client.post("/api/v1/notifications/templates/seed-defaults")
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
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


async def _add_exceptions(client, case_id):
    overdue = (date.today() - timedelta(days=10)).isoformat()
    # Contenedor vencido (demurrage)
    await client.post(
        f"/api/v1/cases/{case_id}/containers",
        json={"container_number": "MSKU1234567", "arrival_date": overdue, "free_days": 5,
              "daily_rate": 100, "status": "AT_PORT"},
    )
    # Almacenaje vencido
    await client.post(
        f"/api/v1/cases/{case_id}/warehouse",
        json={"reference": "H1", "entry_date": overdue, "free_days": 3,
              "rate_type": "PER_DAY", "daily_rate": 40},
    )
    # Control previo pendiente (bloqueante)
    await client.post(
        f"/api/v1/cases/{case_id}/vue-permits",
        json={"entity": "INEN", "document_code": "CRC"},
    )


@pytest.mark.asyncio
async def test_gather_exceptions(client):
    case_id = await _case(client)
    await _add_exceptions(client, case_id)
    ex = (await client.get("/api/v1/alerts/exceptions")).json()
    assert ex["counts"]["demurrage"] >= 1
    assert ex["counts"]["storage"] >= 1
    assert ex["counts"]["vue"] >= 1
    assert ex["total"] >= 3


@pytest.mark.asyncio
async def test_send_digest_to_explicit_recipient(client):
    case_id = await _case(client)
    await _add_exceptions(client, case_id)
    r = await client.post("/api/v1/alerts/digest/send", json={"to": ["ops@caop.local"]})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 3
    assert body["sent"] and body["sent"][0]["to"] == "ops@caop.local"
    assert body["sent"][0]["status"] == "SENT"


@pytest.mark.asyncio
async def test_overdue_receivable_in_exceptions(client):
    case_id = await _case(client)
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    await client.patch(
        f"/api/v1/settlements/{sid}",
        json={"due_date": (date.today() - timedelta(days=20)).isoformat()},
    )
    ex = (await client.get("/api/v1/alerts/exceptions")).json()
    assert ex["counts"]["receivables"] >= 1
    assert any(r["settlement_id"] == sid for r in ex["receivables"])


@pytest.mark.asyncio
async def test_send_digest_no_recipients_configured(client):
    await _case(client)
    r = await client.post("/api/v1/alerts/digest/send", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["sent"] == []
    assert "note" in body  # sin destinatarios configurados
