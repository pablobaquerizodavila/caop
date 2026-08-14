"""Tests de exportación de reportes a CSV."""

import pytest

RUC = "1712345675001"


async def _case_and_quote(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo"}
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
async def test_cases_and_quotes_csv(client):
    await _case_and_quote(client)

    cases = await client.get("/api/v1/exports/cases.csv")
    assert cases.status_code == 200
    assert cases.headers["content-type"].startswith("text/csv")
    assert "attachment" in cases.headers["content-disposition"]
    text = cases.text
    assert text.startswith("﻿")  # BOM para Excel
    assert "Expediente;Cliente;Estado" in text
    assert "Importadora Demo" in text

    quotes = await client.get("/api/v1/exports/quotes.csv")
    assert quotes.status_code == 200
    assert "Cotizacion;Version;Cliente" in quotes.text


@pytest.mark.asyncio
async def test_receivables_csv(client):
    case_id = await _case_and_quote(client)
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    await client.post(f"/api/v1/settlements/{sid}/issue")
    r = await client.get("/api/v1/exports/receivables.csv")
    assert r.status_code == 200
    assert "Liquidacion;Cliente;Moneda" in r.text
