"""Tests de almacenaje (bodega/depósito temporal): costo, alarma y retiro."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _air_case(client):
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
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


@pytest.mark.asyncio
async def test_storage_per_kg_day_overdue(client):
    case_id = await _air_case(client)
    entry = (date.today() - timedelta(days=8)).isoformat()
    r = await client.post(
        f"/api/v1/cases/{case_id}/warehouse",
        json={"warehouse_name": "Depósito GYE", "reference": "HAWB-001",
              "entry_date": entry, "free_days": 3, "rate_type": "PER_KG_DAY",
              "daily_rate": 0.5, "chargeable_weight_kg": 200},
    )
    assert r.status_code == 201
    s = r.json()
    # 8 días desde ingreso, 3 libres -> 5 días vencidos * 0.5 * 200 = 500
    assert s["days_overdue"] == 5
    assert s["estimated_storage"] == 500.0
    assert s["alarm"] == "CRITICAL"

    summ = (await client.get(f"/api/v1/cases/{case_id}/warehouse")).json()
    assert summ["money_at_risk"] == 500.0 and summ["max_alarm"] == "CRITICAL"

    at_risk = (await client.get("/api/v1/warehouse/at-risk")).json()
    assert any(a["reference"] == "HAWB-001" and a["alarm"] == "CRITICAL" for a in at_risk)


@pytest.mark.asyncio
async def test_withdraw_clears_risk(client):
    case_id = await _air_case(client)
    entry = (date.today() - timedelta(days=8)).isoformat()
    sid = (await client.post(
        f"/api/v1/cases/{case_id}/warehouse",
        json={"reference": "HAWB-002", "entry_date": entry, "free_days": 3,
              "rate_type": "PER_DAY", "daily_rate": 40},
    )).json()["id"]
    upd = await client.patch(
        f"/api/v1/warehouse/{sid}",
        json={"status": "WITHDRAWN", "withdrawal_date": date.today().isoformat()},
    )
    assert upd.status_code == 200
    assert upd.json()["alarm"] == "OK"
    summ = (await client.get(f"/api/v1/cases/{case_id}/warehouse")).json()
    assert summ["money_at_risk"] == 0.0  # retirado -> no cuenta como riesgo


@pytest.mark.asyncio
async def test_tariff_crud(client):
    created = await client.post(
        "/api/v1/warehouse/tariffs",
        json={"warehouse_name": "Depósito GYE", "transport_mode": "AIR",
              "free_days": 2, "rate_type": "PER_KG_DAY", "daily_rate": 0.5, "currency": "USD"},
    )
    assert created.status_code == 201
    tid = created.json()["id"]

    listed = (await client.get("/api/v1/warehouse/tariffs")).json()
    assert any(t["id"] == tid and t["warehouse_name"] == "Depósito GYE" for t in listed)

    upd = await client.patch(f"/api/v1/warehouse/tariffs/{tid}", json={"free_days": 5, "active": False})
    assert upd.status_code == 200
    assert upd.json()["free_days"] == 5 and upd.json()["active"] is False

    dele = await client.delete(f"/api/v1/warehouse/tariffs/{tid}")
    assert dele.status_code == 204
    assert all(t["id"] != tid for t in (await client.get("/api/v1/warehouse/tariffs")).json())


@pytest.mark.asyncio
async def test_within_free_days_ok(client):
    case_id = await _air_case(client)
    entry = date.today().isoformat()
    s = (await client.post(
        f"/api/v1/cases/{case_id}/warehouse",
        json={"reference": "HAWB-003", "entry_date": entry, "free_days": 5,
              "rate_type": "PER_DAY", "daily_rate": 40},
    )).json()
    assert s["days_overdue"] == 0
    assert s["estimated_storage"] == 0.0
    assert s["alarm"] == "OK"
