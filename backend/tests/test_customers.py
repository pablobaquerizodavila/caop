"""Tests de la API de Clientes / Contactos / Consentimiento."""

import pytest

VALID_RUC = "1712345675001"


@pytest.mark.asyncio
async def test_create_customer_with_contact(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "Importadora Demo S.A.",
        "contacts": [{"name": "Ana Pérez", "email": "ana@demo.ec", "is_primary": True}],
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["ruc"] == VALID_RUC
    assert body["status"] == "LEAD"
    assert len(body["contacts"]) == 1
    assert body["contacts"][0]["name"] == "Ana Pérez"


@pytest.mark.asyncio
async def test_create_company_with_legal_rep_and_address(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "Importadora Andina S.A.",
        "entity_type": "COMPANY",
        "address": "Av. Amazonas N34-45 y Pereira, Quito, Pichincha",
        "legal_rep_name": "Juan Pérez",
        "legal_rep_id": "1710000009",
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["entity_type"] == "COMPANY"
    assert body["address"].startswith("Av. Amazonas")
    assert body["legal_rep_name"] == "Juan Pérez"
    assert body["legal_rep_id"] == "1710000009"


@pytest.mark.asyncio
async def test_company_requires_legal_rep(client):
    payload = {"ruc": VALID_RUC, "legal_name": "Empresa Sin Rep", "entity_type": "COMPANY"}
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 422  # empresa sin representante legal


@pytest.mark.asyncio
async def test_natural_person_defaults(client):
    resp = await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Persona Natural"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["entity_type"] == "NATURAL"


@pytest.mark.asyncio
async def test_reject_invalid_ruc(client):
    resp = await client.post(
        "/api/v1/customers", json={"ruc": "1712345670001", "legal_name": "X"}
    )
    assert resp.status_code == 422  # validación Pydantic


@pytest.mark.asyncio
async def test_duplicate_ruc_conflict(client):
    payload = {"ruc": VALID_RUC, "legal_name": "Uno"}
    assert (await client.post("/api/v1/customers", json=payload)).status_code == 201
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_consent_lifecycle(client):
    created = await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Con Consent"}
    )
    cid = created.json()["id"]
    resp = await client.post(
        f"/api/v1/customers/{cid}/consents",
        json={"purpose": "Operación aduanera", "legal_basis": "contrato"},
    )
    assert resp.status_code == 201
    listed = await client.get(f"/api/v1/customers/{cid}/consents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
