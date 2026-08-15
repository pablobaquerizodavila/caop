"""Tests de guía de remisión SRI (modo simulador)."""

import pytest


@pytest.mark.asyncio
async def test_create_and_authorize_waybill(client):
    payload = {
        "transporter_name": "Transportes GYE S.A.",
        "transporter_id": "1790012345001",
        "transporter_id_type": "04",
        "placa": "GBA1234",
        "dir_partida": "Puerto de Guayaquil",
        "fecha_ini_transporte": "2026-08-15",
        "fecha_fin_transporte": "2026-08-16",
        "dest_name": "Importadora Demo S.A.",
        "dest_id": "1712345675001",
        "dest_address": "Av. Principal 123, Quito",
        "motivo_traslado": "Entrega de mercancía importada",
        "num_doc_sustento": "001-001-000000123",
        "fecha_doc_sustento": "2026-08-14",
        "items": [
            {"description": "Routers industriales", "quantity": 10},
            {"description": "Cables de red", "quantity": 200},
        ],
    }
    g = (await client.post("/api/v1/waybills", json=payload)).json()
    assert len(g["access_key"]) == 49 and g["access_key"].isdigit()
    assert g["placa"] == "GBA1234" and len(g["items"]) == 2

    xml = (await client.get(f"/api/v1/waybills/{g['id']}/xml")).text
    assert "<guiaRemision" in xml and "<infoGuiaRemision>" in xml
    assert "<destinatarios>" in xml and "GBA1234" in xml
    assert "Routers industriales" in xml

    auth = (await client.post(
        f"/api/v1/waybills/{g['id']}/authorize", json={"scenario": "AUTHORIZE"}
    )).json()
    assert auth["status"] == "AUTHORIZED" and auth["authorization_number"] == g["access_key"]

    listed = (await client.get("/api/v1/waybills")).json()
    assert any(x["id"] == g["id"] for x in listed)


@pytest.mark.asyncio
async def test_waybill_requires_items(client):
    payload = {
        "transporter_name": "T", "transporter_id": "1790012345001", "placa": "AAA1111",
        "fecha_ini_transporte": "2026-08-15", "fecha_fin_transporte": "2026-08-16",
        "dest_name": "D", "dest_id": "1712345675001", "items": [],
    }
    r = await client.post("/api/v1/waybills", json=payload)
    assert r.status_code == 409
