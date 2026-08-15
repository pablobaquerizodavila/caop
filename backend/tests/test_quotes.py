"""Tests de Cotización + Landed Cost + PDF + ciclo de estados."""

import pytest


async def _setup_tax(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={
            "tax_type": "AD_VALOREM",
            "hs_code": "8471.30.00",
            "percentage": "5",
            "base_formula": "CIF",
            "depends_on": [],
            "effective_from": "2020-01-01",
        },
    )


def _quote_payload():
    return {
        "currency": "USD",
        "calculation_date": "2026-01-01",
        "origin_country": "CN",
        "total_freight": "100",
        "total_insurance": "10",
        "items": [
            {
                "description": "Laptop stand",
                "hs_code": "8471.30.00",
                "quantity": "10",
                "unit_price": "100",
            }
        ],
        "cost_lines": [
            {"category": "FEE", "description": "Honorarios despacho", "estimated_amount": "200",
             "confidence": "HIGH"},
            {"category": "PORT", "description": "Gastos portuarios", "estimated_amount": "50",
             "quoted_amount": "60", "confidence": "MEDIUM"},
            {"category": "OTHER", "description": "Demurrage", "estimated_amount": "0",
             "is_included": False},
        ],
    }


@pytest.mark.asyncio
async def test_create_quote_landed_cost(client):
    await _setup_tax(client)
    resp = await client.post("/api/v1/quotes", json=_quote_payload())
    assert resp.status_code == 201, resp.text
    q = resp.json()

    assert q["quote_number"].startswith("QT-2026-")
    assert q["status"] == "DRAFT"
    assert float(q["total_cif"]) == 1110.0
    assert float(q["total_taxes"]) == 236.71
    assert float(q["customer_price_total"]) == 260.0
    assert float(q["landed_cost_total"]) == 1606.71
    assert float(q["landed_cost_per_unit"]) == 160.671
    # Margen (interno): 260 - 250 = 10
    assert float(q["margin_amount"]) == 10.0
    # Ítem con desglose de tributos
    item = q["items"][0]
    types = {c["tax_type"] for c in item["tax_breakdown"]}
    assert {"AD_VALOREM", "FODINFA", "IVA"} <= types


@pytest.mark.asyncio
async def test_update_draft_adds_subpartida_and_recomputes(client):
    await _setup_tax(client)
    # Crea SIN subpartida -> incompleto, sin AD_VALOREM.
    payload = _quote_payload()
    payload["items"][0]["hs_code"] = None
    created = (await client.post("/api/v1/quotes", json=payload)).json()
    qid = created["id"]
    assert created["items"][0]["tax_complete"] is False
    types0 = {c["tax_type"] for c in created["items"][0]["tax_breakdown"]}
    assert "AD_VALOREM" not in types0  # faltante ≠ 0%

    # Edita agregando la subpartida -> recalcula con AD_VALOREM.
    payload["items"][0]["hs_code"] = "8471.30.00"
    r = await client.put(f"/api/v1/quotes/{qid}", json=payload)
    assert r.status_code == 200, r.text
    edited = r.json()
    # El edit recomputa: ahora sí resuelve el AD_VALOREM de la subpartida.
    types1 = {c["tax_type"] for c in edited["items"][0]["tax_breakdown"]}
    assert {"AD_VALOREM", "FODINFA", "IVA"} <= types1
    assert edited["items"][0]["hs_code"] == "8471.30.00"


@pytest.mark.asyncio
async def test_item_model_field(client):
    await _setup_tax(client)
    payload = _quote_payload()
    payload["items"][0]["model"] = "PV33-6048 TLV"
    resp = await client.post("/api/v1/quotes", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["items"][0]["model"] == "PV33-6048 TLV"


@pytest.mark.asyncio
async def test_cannot_edit_non_draft(client):
    await _setup_tax(client)
    qid = (await client.post("/api/v1/quotes", json=_quote_payload())).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    r = await client.put(f"/api/v1/quotes/{qid}", json=_quote_payload())
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_public_view_hides_margin(client):
    await _setup_tax(client)
    created = await client.post("/api/v1/quotes", json=_quote_payload())
    qid = created.json()["id"]

    pub = await client.get(f"/api/v1/quotes/{qid}/public")
    assert pub.status_code == 200
    body = pub.json()
    assert "margin_amount" not in body
    assert "internal_cost_total" not in body
    assert body["disclaimer"]
    # los rubros públicos no exponen el costo interno
    for cl in body["cost_lines"]:
        assert "estimated_amount" not in cl


@pytest.mark.asyncio
async def test_status_transitions(client):
    await _setup_tax(client)
    qid = (await client.post("/api/v1/quotes", json=_quote_payload())).json()["id"]

    ok = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT", "channel": "EMAIL"})
    assert ok.status_code == 200
    # transición inválida SENT -> DRAFT
    bad = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "DRAFT"})
    assert bad.status_code == 409
    # SENT -> REJECTED es válida (no requiere cliente ni conversión)
    ok2 = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "REJECTED"})
    assert ok2.status_code == 200


@pytest.mark.asyncio
async def test_pdf_generation(client, storage):
    await _setup_tax(client)
    qid = (await client.post("/api/v1/quotes", json=_quote_payload())).json()["id"]

    gen = await client.post(f"/api/v1/quotes/{qid}/pdf")
    assert gen.status_code == 200, gen.text
    key = gen.json()["object_key"]
    assert storage.objects[key].startswith(b"%PDF")

    dl = await client.get(f"/api/v1/quotes/{qid}/pdf/download")
    assert dl.status_code == 200
    assert dl.json()["url"].startswith("https://fake-storage.local/")


@pytest.mark.asyncio
async def test_revise_creates_new_version(client):
    await _setup_tax(client)
    qid = (await client.post("/api/v1/quotes", json=_quote_payload())).json()["id"]
    rev = await client.post(f"/api/v1/quotes/{qid}/revise")
    assert rev.status_code == 201
    assert rev.json()["version"] == 2
    assert float(rev.json()["landed_cost_total"]) == 1606.71
