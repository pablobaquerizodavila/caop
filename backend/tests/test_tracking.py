"""Tests de Track & Trace: enlace público, vista del cliente y envío de enlace."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers",
        json={"ruc": RUC, "legal_name": "Importadora Demo S.A.", "trade_name": "DemoImports",
              "email": "cliente@demo.ec"},
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
async def test_tracking_link_and_public_view(client):
    case_id = await _case(client)
    await client.patch(
        f"/api/v1/cases/{case_id}/transport",
        json={"carrier": "MAERSK", "vessel": "Ever Given", "voyage": "12E",
              "pol": "CNSHA", "pod": "ECGYE", "eta": (date.today() + timedelta(days=5)).isoformat()},
    )
    await client.post(
        f"/api/v1/cases/{case_id}/containers",
        json={"container_number": "MSKU1234567", "iso_type": "40HC",
              "arrival_date": date.today().isoformat(), "free_days": 5,
              "daily_rate": 120, "status": "AT_PORT"},
    )

    link = (await client.get(f"/api/v1/cases/{case_id}/tracking")).json()
    assert link["token"] and link["enabled"] is True
    assert link["token"] in link["url"] and "/track/" in link["url"]

    view = await client.get(f"/api/v1/track/{link['token']}")
    assert view.status_code == 200
    v = view.json()
    assert v["customer_name"] == "DemoImports"  # usa el nombre comercial
    assert v["transport"]["mode"] == "Marítimo"
    assert v["transport"]["vessel_or_flight"] == "Ever Given 12E"
    keys = [m["key"] for m in v["milestones"]]
    assert keys == ["RECEIVED", "DOCS", "DEPARTURE", "ARRIVAL", "CUSTOMS", "RELEASED", "DELIVERED"]
    assert v["milestones"][0]["status"] == "done"  # RECEIVED
    assert any(m["status"] == "current" for m in v["milestones"])
    assert v["containers"][0]["number"] == "MSKU1234567"
    assert v["containers"][0]["alarm_label"]  # etiqueta amigable presente
    assert 0 <= v["progress_pct"] <= 100


@pytest.mark.asyncio
async def test_unknown_and_disabled_token_return_404(client):
    case_id = await _case(client)
    assert (await client.get("/api/v1/track/no-existe")).status_code == 404

    link = (await client.get(f"/api/v1/cases/{case_id}/tracking")).json()
    await client.patch(f"/api/v1/cases/{case_id}/tracking", json={"enabled": False})
    assert (await client.get(f"/api/v1/track/{link['token']}")).status_code == 404


@pytest.mark.asyncio
async def test_rotate_invalidates_previous_token(client):
    case_id = await _case(client)
    old = (await client.get(f"/api/v1/cases/{case_id}/tracking")).json()["token"]
    new = (await client.post(f"/api/v1/cases/{case_id}/tracking/rotate")).json()["token"]
    assert old != new
    assert (await client.get(f"/api/v1/track/{old}")).status_code == 404
    assert (await client.get(f"/api/v1/track/{new}")).status_code == 200


@pytest.mark.asyncio
async def test_send_tracking_uses_customer_email(client):
    case_id = await _case(client)
    await client.post("/api/v1/notifications/templates/seed-defaults")
    r = await client.post(f"/api/v1/cases/{case_id}/tracking/send", json={"channel": "EMAIL"})
    assert r.status_code == 200
    body = r.json()
    assert body["to"] == "cliente@demo.ec"
    assert body["status"] == "SENT"
