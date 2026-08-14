"""Tests de los endpoints de salud y de la protección por token."""

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_ready_ok(client):
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_me_returns_principal(client):
    # En tests la auth está bypasseada (override); /me devuelve el principal de prueba.
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "tester"


@pytest.mark.asyncio
async def test_correlation_id_header(client):
    resp = await client.get("/api/v1/health")
    assert "X-Correlation-ID" in resp.headers
