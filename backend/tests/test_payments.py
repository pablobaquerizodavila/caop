"""Tests de cobranza: pagos, saldo/estado y cuentas por cobrar (aging)."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _issued_settlement(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "description": "Honorarios", "estimated_amount": "100"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    return sid


@pytest.mark.asyncio
async def test_partial_then_full_payment(client):
    sid = await _issued_settlement(client)
    view0 = (await client.get(f"/api/v1/settlements/{sid}/payments")).json()
    total = view0["total"]
    assert total > 0 and view0["status"] == "PENDING" and view0["balance"] == total

    half = round(total / 2, 2)
    v1 = (await client.post(
        f"/api/v1/settlements/{sid}/payments",
        json={"amount": half, "paid_at": date.today().isoformat(), "method": "TRANSFER"},
    )).json()
    assert v1["status"] == "PARTIAL" and v1["paid"] == half

    v2 = (await client.post(
        f"/api/v1/settlements/{sid}/payments",
        json={"amount": round(total - half, 2), "paid_at": date.today().isoformat(), "method": "CASH"},
    )).json()
    assert v2["status"] == "PAID" and v2["balance"] == 0.0
    assert len(v2["payments"]) == 2


@pytest.mark.asyncio
async def test_receivables_aging(client):
    sid = await _issued_settlement(client)
    total = (await client.get(f"/api/v1/settlements/{sid}/payments")).json()["total"]
    await client.patch(
        f"/api/v1/settlements/{sid}",
        json={"due_date": (date.today() - timedelta(days=45)).isoformat()},
    )
    rec = (await client.get("/api/v1/analytics/receivables")).json()
    mine = [x for x in rec["items"] if x["settlement_id"] == sid]
    assert mine and mine[0]["balance"] == total
    assert mine[0]["bucket"] == "31-60" and mine[0]["days_overdue"] >= 45
    assert rec["total_balance"] >= total


@pytest.mark.asyncio
async def test_paid_not_in_receivables(client):
    sid = await _issued_settlement(client)
    total = (await client.get(f"/api/v1/settlements/{sid}/payments")).json()["total"]
    await client.post(
        f"/api/v1/settlements/{sid}/payments",
        json={"amount": total, "paid_at": date.today().isoformat()},
    )
    rec = (await client.get("/api/v1/analytics/receivables")).json()
    assert all(x["settlement_id"] != sid for x in rec["items"])
