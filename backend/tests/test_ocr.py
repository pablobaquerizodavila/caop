"""Tests de OCR/extracción automática: auto-extracción al subir, revisión humana,
extracciones por expediente y degradación elegante cuando no hay OCR."""

import pytest

RUC = "1712345675001"

PROFORMA = (
    b"SHENZHEN TECH CO LTD\n"
    b"COMMERCIAL INVOICE No: CI-2026-0420\n"
    b"Date: 2026-03-11\n"
    b"Incoterm: FOB Shenzhen\n"
    b"Currency: USD\n"
    b"2 x Router industrial   8400.00 USD\n"
    b"Total Amount: 8,400.00\n"
)

# PNG mínimo (1x1) para forzar la ruta de imagen/OCR sin binario Tesseract en test.
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c636060606000000005000107a0b4e70000000049454e44ae426082"
)


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Demo"}
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
async def test_auto_extract_on_upload(client):
    """Subir una factura comercial dispara la extracción automática (sin llamada extra)."""
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("invoice.txt", PROFORMA, "text/plain")},
        data={"doc_type": "COMMERCIAL_INVOICE"},
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    listed = await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")
    fields = {f["field_name"]: f for f in listed.json()}
    assert fields["invoice_number"]["extracted_value"] == "CI-2026-0420"
    assert fields["currency"]["extracted_value"] == "USD"
    assert fields["total_amount"]["extracted_value"] == "8400.00"


@pytest.mark.asyncio
async def test_no_auto_extract_for_unclassified(client):
    """Un documento sin clasificar NO se auto-extrae (evita OCR innecesario)."""
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("misc.txt", PROFORMA, "text/plain")},
    )
    doc_id = up.json()["id"]
    listed = await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")
    assert listed.json() == []


@pytest.mark.asyncio
async def test_verify_extraction(client):
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("invoice.txt", PROFORMA, "text/plain")},
        data={"doc_type": "COMMERCIAL_INVOICE"},
    )
    doc_id = up.json()["id"]
    rows = (await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")).json()
    ext_id = rows[0]["id"]
    r = await client.patch(
        f"/api/v1/documents/{doc_id}/versions/1/extractions/{ext_id}",
        json={"verified_value": "VALOR-CORREGIDO"},
    )
    assert r.status_code == 200
    assert r.json()["verified_value"] == "VALOR-CORREGIDO"


@pytest.mark.asyncio
async def test_case_extractions_and_event(client):
    case_id = await _case(client)
    await client.post(
        "/api/v1/documents",
        files={"file": ("invoice.txt", PROFORMA, "text/plain")},
        data={"doc_type": "COMMERCIAL_INVOICE", "customs_case_id": case_id},
    )
    docs = (await client.get(f"/api/v1/documents/case/{case_id}/extractions")).json()
    assert len(docs) == 1
    assert docs[0]["doc_type"] == "COMMERCIAL_INVOICE"
    assert any(f["field_name"] == "invoice_number" for f in docs[0]["fields"])

    # El evento de extracción queda en el timeline del expediente.
    case = (await client.get(f"/api/v1/cases/{case_id}")).json()
    assert any(e["event_type"] == "DOCUMENT_EXTRACTED" for e in case["events"])


@pytest.mark.asyncio
async def test_image_upload_degrades_without_ocr(client):
    """Sin binario/librerías de OCR, subir una imagen no rompe: degrada a baja confianza."""
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", PNG_1x1, "image/png")},
        data={"doc_type": "COMMERCIAL_INVOICE"},
    )
    assert up.status_code == 201  # la subida nunca falla por OCR
    doc_id = up.json()["id"]
    rows = (await client.get(f"/api/v1/documents/{doc_id}/versions/1/extractions")).json()
    # Se registran los campos (para revisión), todos sin valor reconocido.
    assert rows and all(f["extracted_value"] is None for f in rows)
