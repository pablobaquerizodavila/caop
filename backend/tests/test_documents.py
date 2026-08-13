"""Tests de la API de Documentos: subida, integridad SHA-256 y versionado."""

import hashlib

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
