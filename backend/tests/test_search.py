"""Tests de búsqueda global."""

import pytest

RUC = "1712345675001"


@pytest.mark.asyncio
async def test_search_across_entities(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers",
        json={"ruc": RUC, "legal_name": "Importadora Andina S.A.", "trade_name": "Andina"},
    )).json()["id"]
    await client.post("/api/v1/suppliers", json={"name": "Shenzhen Andina Tech", "country": "CN"})
    q = {"customer_id": cid, "transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    quote_number = (await client.get(f"/api/v1/quotes/{qid}")).json()["quote_number"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_number = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["case_number"]

    # Cliente / proveedor por término común
    r = (await client.get("/api/v1/search?q=Andina")).json()
    assert any(c["sub"] == RUC for c in r["customers"])
    assert any("Andina" in s["label"] for s in r["suppliers"])

    # Expediente por número
    r2 = (await client.get(f"/api/v1/search?q={case_number}")).json()
    assert any(c["label"] == case_number for c in r2["cases"])

    # Cotización por número
    r3 = (await client.get(f"/api/v1/search?q={quote_number}")).json()
    assert any(quote_number in x["label"] for x in r3["quotes"])


@pytest.mark.asyncio
async def test_search_short_query_empty(client):
    r = (await client.get("/api/v1/search?q=a")).json()
    assert r["cases"] == [] and r["customers"] == []
