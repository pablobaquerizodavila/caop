"""Test de vincular/reasignar cliente a una cotización (S17)."""

import pytest

RUC_A = "1712345675001"
RUC_B = "0912345675001"  # segundo RUC natural válido (provincia 09)


@pytest.mark.asyncio
async def test_link_customer_enables_accept(client):
    # Cotización SIN cliente no se puede aceptar
    q = {"transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    blocked = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    assert blocked.status_code == 409

    # Crear cliente y vincularlo
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC_A, "legal_name": "Cliente A"}
    )).json()["id"]
    linked = await client.post(f"/api/v1/quotes/{qid}/link-customer", json={"customer_id": cid})
    assert linked.status_code == 200
    assert linked.json()["customer_id"] == cid

    # Ahora sí se acepta (y se crea el expediente)
    ok = await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_reassign_propagates_to_shipment(client):
    a = (await client.post("/api/v1/customers", json={"ruc": RUC_A, "legal_name": "A"})).json()["id"]
    b = (await client.post("/api/v1/customers", json={"ruc": RUC_B, "legal_name": "B"})).json()["id"]
    q = {"customer_id": a, "transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})

    # Reasignar al cliente B -> se propaga al shipment
    r = await client.post(f"/api/v1/quotes/{qid}/link-customer", json={"customer_id": b})
    assert r.status_code == 200 and r.json()["customer_id"] == b
    shipments = (await client.get(f"/api/v1/shipments?customer_id={b}")).json()
    assert any(s["source_quote_id"] == qid for s in shipments)


@pytest.mark.asyncio
async def test_link_unknown_customer_404(client):
    import uuid
    q = {"transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}], "cost_lines": []}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    r = await client.post(
        f"/api/v1/quotes/{qid}/link-customer", json={"customer_id": str(uuid.uuid4())}
    )
    assert r.status_code == 404
