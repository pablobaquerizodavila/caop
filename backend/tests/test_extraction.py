"""Tests del pipeline de extracción de proforma (extractor heurístico de texto)."""

import pytest

PROFORMA = (
    b"SHENZHEN TECH CO LTD\n"
    b"PROFORMA INVOICE No: PI-2024-0088\n"
    b"Date: 2024-11-05\n"
    b"Incoterm: FOB Shenzhen\n"
    b"Currency: USD\n"
    b"1 x Laptop stand   12500.00 USD\n"
    b"Total Amount: 12,500.00\n"
)


@pytest.mark.asyncio
async def test_extract_proforma_fields(client):
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("proforma.txt", PROFORMA, "text/plain")},
        data={"doc_type": "INVOICE"},
    )
    doc_id = up.json()["id"]

    resp = await client.post(f"/api/v1/documents/{doc_id}/versions/1/extract")
    assert resp.status_code == 201, resp.text
    fields = {f["field_name"]: f for f in resp.json()}

    assert fields["invoice_number"]["extracted_value"] == "PI-2024-0088"
    assert fields["incoterm"]["extracted_value"] == "FOB"
    assert fields["currency"]["extracted_value"] == "USD"
    assert fields["total_amount"]["extracted_value"] == "12500.00"
    # Cada dato lleva confianza
    assert 0 < fields["invoice_number"]["confidence_score"] <= 1


@pytest.mark.asyncio
async def test_list_extractions(client):
    up = await client.post(
        "/api/v1/documents", files={"file": ("p.txt", PROFORMA, "text/plain")}
    )
    doc_id = up.json()["id"]
    await client.post(f"/api/v1/documents/{doc_id}/versions/1/extract")
    listed = await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")
    assert listed.status_code == 200
    assert len(listed.json()) >= 4
