"""Test del historial de importaciones por cliente (S17)."""

import pytest

RUC = "1712345675001"


@pytest.mark.asyncio
async def test_customer_history(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Recurrente S.A."}
    )).json()["id"]

    # Dos cotizaciones; una aceptada -> genera expediente
    for i in range(2):
        q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
             "calculation_date": "2026-01-01",
             "items": [{"quantity": "1", "unit_price": "100"}],
             "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
        qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
        if i == 0:
            await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
            await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})

    hist = await client.get(f"/api/v1/customers/{cid}/history")
    assert hist.status_code == 200
    d = hist.json()
    assert d["customer"]["ruc"] == RUC
    assert d["stats"]["total_quotes"] == 2
    assert d["stats"]["total_cases"] == 1
    assert len(d["cases"]) == 1
    assert d["cases"][0]["case_number"].startswith("EC-IMP-")
    assert d["cases"][0]["transport_mode"] == "OCEAN"


@pytest.mark.asyncio
async def test_history_empty_for_new_customer(client):
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Nuevo"}
    )).json()["id"]
    d = (await client.get(f"/api/v1/customers/{cid}/history")).json()
    assert d["stats"]["total_cases"] == 0 and d["stats"]["total_quotes"] == 0
