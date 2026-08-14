"""Tests del centro de notificaciones: listado/filtro, reenvío y edición de plantillas."""

import pytest


@pytest.mark.asyncio
async def test_list_filter_and_resend(client):
    await client.post("/api/v1/notifications/templates/seed-defaults")
    sent = await client.post(
        "/api/v1/notifications/send",
        json={"channel": "EMAIL", "template_code": "DOCUMENT_REQUIRED", "to": "cli@demo.ec",
              "context": {"customer_name": "Demo", "case_number": "EC-1", "missing_docs": "Factura"}},
    )
    assert sent.status_code == 201
    nid = sent.json()["id"]

    # Listado + filtro por canal, con cuerpo renderizado.
    lst = (await client.get("/api/v1/notifications?channel=EMAIL")).json()
    mine = [n for n in lst if n["id"] == nid]
    assert mine and mine[0]["to_address"] == "cli@demo.ec"
    assert "Factura" in (mine[0]["body"] or "")

    # Reenvío -> nueva notificación enviada.
    re = await client.post(f"/api/v1/notifications/{nid}/resend")
    assert re.status_code == 200
    assert re.json()["status"] == "SENT"
    assert re.json()["id"] != nid


@pytest.mark.asyncio
async def test_template_edit(client):
    await client.post("/api/v1/notifications/templates/seed-defaults")
    templates = (await client.get("/api/v1/notifications/templates")).json()
    tid = templates[0]["id"]
    upd = await client.patch(
        f"/api/v1/notifications/templates/{tid}",
        json={"active": False, "body_template": "Nuevo cuerpo {{case_number}}"},
    )
    assert upd.status_code == 200
    assert upd.json()["active"] is False
    assert upd.json()["body_template"] == "Nuevo cuerpo {{case_number}}"
