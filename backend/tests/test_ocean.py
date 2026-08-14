"""Tests de la API Ocean: transporte, contenedores y demurrage."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


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
async def test_update_transport(client):
    case_id = await _case(client)
    r = await client.patch(
        f"/api/v1/cases/{case_id}/transport",
        json={"carrier": "MAERSK", "mbl_number": "MAEU123", "vessel": "Ever Given",
              "pol": "CNSHA", "pod": "ECGYE", "load_type": "FCL"},
    )
    assert r.status_code == 200
    assert r.json()["carrier"] == "MAERSK" and r.json()["mbl_number"] == "MAEU123"


@pytest.mark.asyncio
async def test_container_demurrage_and_risk(client):
    case_id = await _case(client)
    overdue = (date.today() - timedelta(days=10)).isoformat()
    r = await client.post(
        f"/api/v1/cases/{case_id}/containers",
        json={"container_number": "MSKU1234567", "iso_type": "40HC",
              "arrival_date": overdue, "free_days": 5, "daily_rate": 120, "status": "AT_PORT"},
    )
    assert r.status_code == 201
    c = r.json()
    assert c["days_overdue"] == 5
    assert c["estimated_demurrage"] == 600.0
    assert c["alarm"] == "CRITICAL"

    summ = (await client.get(f"/api/v1/cases/{case_id}/demurrage")).json()
    assert summ["money_at_risk"] == 600.0
    assert summ["max_alarm"] == "CRITICAL"

    at_risk = (await client.get("/api/v1/ocean/demurrage-at-risk")).json()
    mine = [a for a in at_risk if a["container_number"] == "MSKU1234567"]
    assert mine and mine[0]["alarm"] == "CRITICAL"


@pytest.mark.asyncio
async def test_container_returned_clears_risk(client):
    case_id = await _case(client)
    overdue = (date.today() - timedelta(days=10)).isoformat()
    cid = (await client.post(
        f"/api/v1/cases/{case_id}/containers",
        json={"container_number": "TCLU7654321", "arrival_date": overdue, "free_days": 5,
              "daily_rate": 100, "status": "AT_PORT"},
    )).json()["id"]
    upd = await client.patch(
        f"/api/v1/containers/{cid}",
        json={"status": "EMPTY_RETURNED", "empty_return_date": date.today().isoformat()},
    )
    assert upd.status_code == 200
    assert upd.json()["alarm"] == "OK"
    summ = (await client.get(f"/api/v1/cases/{case_id}/demurrage")).json()
    assert summ["money_at_risk"] == 0.0  # devuelto -> no cuenta como riesgo
