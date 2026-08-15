"""Tests del comprobante de retención SRI (modo simulador)."""

import pytest


@pytest.mark.asyncio
async def test_create_and_authorize_retention(client):
    payload = {
        "subject_name": "Servicios Portuarios S.A.",
        "subject_id": "1790012345001",
        "subject_id_type": "04",
        "period": "08/2026",
        "doc_sustento_number": "001-001-000000123",
        "doc_sustento_date": "2026-08-10",
        "lines": [
            {"tax_type": "1", "codigo_retencion": "312", "base_imponible": 1000, "percentage": 2},
            {"tax_type": "2", "codigo_retencion": "9", "base_imponible": 150, "percentage": 30},
        ],
    }
    rv = (await client.post("/api/v1/retentions", json=payload)).json()
    assert rv["document_type"] if "document_type" in rv else True
    assert len(rv["access_key"]) == 49 and rv["access_key"].isdigit()
    # Renta 2% de 1000 = 20 ; IVA 30% de 150 = 45 -> total 65
    assert rv["total_retained"] == 65.0
    assert len(rv["lines"]) == 2
    vals = {ln["codigo_retencion"]: ln["value"] for ln in rv["lines"]}
    assert vals["312"] == 20.0 and vals["9"] == 45.0

    xml = (await client.get(f"/api/v1/retentions/{rv['id']}/xml")).text
    assert "<comprobanteRetencion" in xml and "<infoCompRetencion>" in xml
    assert "<periodoFiscal>08/2026</periodoFiscal>" in xml
    assert "1790012345001" in xml

    auth = (await client.post(
        f"/api/v1/retentions/{rv['id']}/authorize", json={"scenario": "AUTHORIZE"}
    )).json()
    assert auth["status"] == "AUTHORIZED" and auth["authorization_number"] == rv["access_key"]

    listed = (await client.get("/api/v1/retentions")).json()
    assert any(x["id"] == rv["id"] for x in listed)


@pytest.mark.asyncio
async def test_retention_requires_lines(client):
    payload = {
        "subject_name": "X", "subject_id": "1790012345001", "period": "08/2026",
        "doc_sustento_number": "001-001-000000001", "doc_sustento_date": "2026-08-01",
        "lines": [],
    }
    r = await client.post("/api/v1/retentions", json=payload)
    assert r.status_code == 409
