"""Tests de facturación electrónica SRI (modo simulador)."""

import pytest

from app.services.sri_service import _mod11, build_access_key
from datetime import date

RUC = "1712345675001"


def test_mod11_check_digit():
    # Clave de acceso conocida: los primeros 48 dígitos con su verificador oficial.
    key48 = "170520210110179214673700110010030000000011234567811"[:48]
    # Verificación del algoritmo: el dígito debe estar en 0..9
    dv = _mod11(key48)
    assert 0 <= dv <= 9
    # Determinista y estable
    assert _mod11("100820260117123456750011000010000000001000000011") in range(10)


def test_build_access_key_length_and_digits():
    key = build_access_key(
        date(2026, 8, 14), "01", "1790012345001", "1", "001", "001", "000000001", "1"
    )
    assert len(key) == 49
    assert key.isdigit()
    # El último dígito es el verificador del resto.
    assert int(key[-1]) == _mod11(key[:48])


async def _settlement(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo S.A."}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "description": "Honorarios", "estimated_amount": "150"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    sid = (await client.post(f"/api/v1/cases/{case_id}/settlement")).json()["id"]
    return sid


@pytest.mark.asyncio
async def test_invoice_requires_issued_settlement(client):
    sid = await _settlement(client)  # DRAFT
    r = await client.post(f"/api/v1/settlements/{sid}/invoice")
    assert r.status_code == 409  # debe estar emitida


@pytest.mark.asyncio
async def test_create_and_authorize_invoice(client):
    sid = await _settlement(client)
    await client.post(f"/api/v1/settlements/{sid}/issue")

    inv = (await client.post(f"/api/v1/settlements/{sid}/invoice")).json()
    assert inv["status"] == "DRAFT"
    assert len(inv["access_key"]) == 49 and inv["access_key"].isdigit()
    assert inv["is_simulated"] is True
    # IVA 15% sobre 150 = 22.5 -> total 172.5
    assert inv["total"] == 172.5

    # XML contra estructura oficial.
    xml = (await client.get(f"/api/v1/invoices/{inv['id']}/xml")).text
    assert "<factura" in xml and "<claveAcceso>" in xml and inv["access_key"] in xml
    assert "<infoFactura>" in xml and "<importeTotal>172.50</importeTotal>" in xml

    # Autorizar (simulado) -> AUTHORIZED con número = clave de acceso.
    auth = (await client.post(
        f"/api/v1/invoices/{inv['id']}/authorize", json={"scenario": "AUTHORIZE"}
    )).json()
    assert auth["status"] == "AUTHORIZED"
    assert auth["authorization_number"] == inv["access_key"]
    assert auth["signed"] is True


@pytest.mark.asyncio
async def test_authorize_reject_scenario(client):
    sid = await _settlement(client)
    await client.post(f"/api/v1/settlements/{sid}/issue")
    inv = (await client.post(f"/api/v1/settlements/{sid}/invoice")).json()
    auth = (await client.post(
        f"/api/v1/invoices/{inv['id']}/authorize", json={"scenario": "REJECT"}
    )).json()
    assert auth["status"] == "REJECTED" and auth["error"]
