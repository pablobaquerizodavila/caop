"""Test del overview de analytics."""

import pytest

VALID_RUC = "1712345675001"


@pytest.mark.asyncio
async def test_overview_after_flow(client):
    # Preparar un flujo mínimo: reglas, requisitos, cliente, cotización aceptada.
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

    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    d = resp.json()

    assert d["cases"]["total"] == 1
    assert d["cases"]["by_state"].get("AWAITING_DOCUMENTS") == 1
    assert d["commercial"]["total_quotes"] == 1
    assert d["commercial"]["accepted"] == 1
    assert d["commercial"]["conversion_rate"] == 100.0
    # Sin toques humanos aún -> straight-through 100%, automation_rate alto
    assert d["automation"]["straight_through_rate"] == 100.0
    assert d["automation"]["automation_rate"] == 100.0
    assert "human_touches_per_shipment" in d["automation"]
    assert d["sla"]["open"] >= 1


@pytest.mark.asyncio
async def test_human_touch_counts(client):
    # Un PATCH de checklist genera un evento USER -> baja el straight-through.
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Demo"}
    )).json()["id"]
    quote = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
             "calculation_date": "2026-01-01",
             "items": [{"quantity": "1", "unit_price": "100"}],
             "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=quote)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    item = (await client.get(f"/api/v1/cases/{case_id}")).json()["checklist"][0]
    await client.patch(
        f"/api/v1/cases/{case_id}/checklist/{item['id']}", json={"status": "COMPLETE"}
    )

    d = (await client.get("/api/v1/analytics/overview")).json()
    assert d["automation"]["user_events"] >= 1
    assert d["automation"]["straight_through_rate"] == 0.0  # el único caso tuvo un toque
