"""Tests de la API de Documentos: subida, integridad SHA-256 y versionado."""

import hashlib
from datetime import date, timedelta

import pytest


@pytest.mark.asyncio
async def test_upload_creates_version_and_hash(client, storage):
    content = b"contenido de la factura proforma"
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("proforma.pdf", content, "application/pdf")},
        data={"doc_type": "INVOICE", "source": "PORTAL"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["doc_type"] == "INVOICE"
    assert len(body["versions"]) == 1

    v1 = body["versions"][0]
    assert v1["version"] == 1
    assert v1["sha256"] == hashlib.sha256(content).hexdigest()
    assert v1["size"] == len(content)

    # El objeto quedó almacenado con esos bytes exactos.
    assert content in storage.objects.values()


@pytest.mark.asyncio
async def test_upload_with_expiry_date(client):
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("ruc.pdf", b"ruc", "application/pdf")},
        data={"doc_type": "RUC", "expiry_date": "2027-06-30"},
    )
    assert resp.status_code == 201, resp.text
    v1 = resp.json()["versions"][0]
    assert v1["expiry_date"] == "2027-06-30"


@pytest.mark.asyncio
async def test_expiring_documents_alert(client):
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": "1712345675001", "legal_name": "Con Docs"}
    )).json()["id"]
    soon = (date.today() + timedelta(days=10)).isoformat()
    await client.post(
        "/api/v1/documents",
        files={"file": ("ruc.pdf", b"x", "application/pdf")},
        data={"doc_type": "RUC", "customer_id": cid, "expiry_date": soon},
    )
    r = await client.get("/api/v1/alerts/expiring-documents?within_days=30")
    assert r.status_code == 200
    items = r.json()
    assert any(x["customer_id"] == cid and x["doc_type"] == "RUC" for x in items)
    hit = next(x for x in items if x["customer_id"] == cid)
    assert hit["days_left"] == 10 and hit["status"] == "SOON"


@pytest.mark.asyncio
async def test_versioning_increments(client):
    up = await client.post(
        "/api/v1/documents",
        files={"file": ("a.pdf", b"v1", "application/pdf")},
    )
    doc_id = up.json()["id"]
    resp = await client.post(
        f"/api/v1/documents/{doc_id}/versions",
        files={"file": ("a.pdf", b"v2 contenido", "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    versions = resp.json()["versions"]
    assert [v["version"] for v in versions] == [1, 2]


@pytest.mark.asyncio
async def test_download_returns_presigned_url(client):
    up = await client.post(
        "/api/v1/documents", files={"file": ("a.pdf", b"data", "application/pdf")}
    )
    doc_id = up.json()["id"]
    resp = await client.get(f"/api/v1/documents/{doc_id}/versions/1/download")
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("https://fake-storage.local/")


@pytest.mark.asyncio
async def test_empty_file_rejected(client):
    resp = await client.post(
        "/api/v1/documents", files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert resp.status_code == 400
