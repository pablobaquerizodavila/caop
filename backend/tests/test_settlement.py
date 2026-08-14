"""Tests de liquidación al cliente: borrador autopoblado, IVA, edición y emisión."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Demo", "trade_name": "DemoImports"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "10", "unit_price": "100", "hs_code": "8471.30.00.00"}],
         "cost_lines": [
             {"category": "FEE", "description": "Honorarios de despacho", "estimated_amount": "150"},
             {"category": "FREIGHT", "description": "Flete internacional", "estimated_amount": "800"},
         ]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


@pytest.mark.asyncio
async def test_build_draft_autopopulates(client):
    case_id = await _case(client)
    # Agregar almacenaje vencido para que entre como desembolso.
    entry = (date.today() - timedelta(days=8)).isoformat()
    await client.post(
        f"/api/v1/cases/{case_id}/warehouse",
        json={"reference": "H1", "entry_date": entry, "free_days": 3,
              "rate_type": "PER_DAY", "daily_rate": 40},
    )

    stl = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()
    assert stl["settlement_number"].startswith("LIQ-")
    cats = {ln["category"] for ln in stl["lines"]}
    assert "HONORARIO" in cats and "FLETE" in cats
    assert "TRIBUTO" in cats  # tributos estimados de la cotización
    assert "ALMACENAJE" in cats  # 5 días * 40 = 200

    fees = [ln for ln in stl["lines"] if ln["kind"] == "FEE"]
    assert fees and fees[0]["taxable"] is True
    # IVA 15% sobre honorarios (150) = 22.5
    assert stl["subtotal_fees"] == 150.0
    assert stl["tax_amount"] == 22.5
    assert stl["total"] == round(stl["subtotal_fees"] + stl["tax_amount"] + stl["subtotal_disbursements"], 2)


@pytest.mark.asyncio
async def test_idempotent_and_edit_and_issue(client):
    case_id = await _case(client)
    a = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()
    b = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()
    assert a["id"] == b["id"]  # no duplica

    # Agregar un honorario adicional gravado.
    upd = (await client.post(
        f"/api/v1/settlements/{a['id']}/lines",
        json={"kind": "FEE", "category": "HONORARIO", "description": "Gestión extra",
              "amount": 50, "taxable": True},
    )).json()
    assert upd["subtotal_fees"] == 200.0
    assert upd["tax_amount"] == 30.0  # 15% de 200

    # Emitir.
    issued = (await client.post(f"/api/v1/settlements/{a['id']}/issue")).json()
    assert issued["status"] == "ISSUED"


@pytest.mark.asyncio
async def test_pdf_generation(client):
    case_id = await _case(client)
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    gen = await client.post(f"/api/v1/settlements/{sid}/pdf")
    assert gen.status_code == 200 and gen.json()["size"] > 0
    dl = await client.get(f"/api/v1/settlements/{sid}/pdf/download")
    assert dl.status_code == 200 and dl.json()["url"]


@pytest.mark.asyncio
async def test_iva_rate_change_recomputes(client):
    case_id = await _case(client)
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    upd = (await client.patch(f"/api/v1/settlements/{sid}", json={"iva_rate": 0})).json()
    assert upd["tax_amount"] == 0.0
