"""Tests de notificaciones: plantillas, envío y auto-notificación al crear expediente."""

import pytest

from app.services.notifications import RealNotifier, render

VALID_RUC = "1712345675001"


def test_render_placeholders():
    assert render("Hola {{name}}, caso {{case}}", {"name": "Ana", "case": "X1"}) == "Hola Ana, caso X1"
    assert render("Sin {{faltante}}", {}) == "Sin "


@pytest.mark.asyncio
async def test_whatsapp_simulated_without_token():
    # Sin token configurado, el conector NO inventa: opera en modo SIMULADO.
    res = await RealNotifier().send("WHATSAPP", "+593999999999", None, "hola")
    assert res.status == "SIMULATED"


@pytest.mark.asyncio
async def test_seed_and_send(client):
    seed = await client.post("/api/v1/notifications/templates/seed-defaults")
    assert seed.status_code == 200
    assert any(c.startswith("DOCUMENT_REQUIRED") for c in seed.json()["created"])

    resp = await client.post(
        "/api/v1/notifications/send",
        json={
            "channel": "EMAIL",
            "template_code": "DOCUMENT_REQUIRED",
            "to": "cliente@demo.ec",
            "context": {"customer_name": "Demo", "case_number": "EC-IMP-2026-00000009",
                        "missing_docs": "COMMERCIAL_INVOICE"},
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "SENT"
    assert body["template_version"] == 1
    assert "EC-IMP-2026-00000009" in body["subject"]


@pytest.mark.asyncio
async def test_auto_notify_on_conversion(client):
    # Preparar tributos, requisitos y plantillas
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={"tax_type": "AD_VALOREM", "hs_code": "8471.30.00", "percentage": "5",
              "base_formula": "CIF", "depends_on": [], "effective_from": "2020-01-01"},
    )
    await client.post("/api/v1/requirements/seed-defaults")
    await client.post("/api/v1/notifications/templates/seed-defaults")

    cust = await client.post(
        "/api/v1/customers",
        json={"ruc": VALID_RUC, "legal_name": "Importadora Demo", "email": "cliente@demo.ec"},
    )
    cid = cust.json()["id"]

    quote = {
        "customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
        "calculation_date": "2026-01-01",
        "items": [{"hs_code": "8471.30.00", "quantity": "10", "unit_price": "100"}],
        "cost_lines": [{"category": "FEE", "estimated_amount": "200"}],
    }
    qid = (await client.post("/api/v1/quotes", json=quote)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})

    # Debe existir una notificación DOCUMENT_REQUIRED al cliente
    notifs = (await client.get(f"/api/v1/notifications?customer_id={cid}")).json()
    doc_req = [n for n in notifs if n["template_code"] == "DOCUMENT_REQUIRED"]
    assert doc_req, "no se generó la notificación de documentos requeridos"
    assert doc_req[0]["status"] == "SENT"
    assert doc_req[0]["channel"] == "EMAIL"

    # y el evento en el timeline del expediente
    case = (await client.get(f"/api/v1/quotes/{qid}/case")).json()
    detail = (await client.get(f"/api/v1/cases/{case['id']}")).json()
    assert any(e["event_type"] == "DOCUMENT_REQUIRED_SENT" for e in detail["events"])
