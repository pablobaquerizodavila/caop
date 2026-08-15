"""Tests de CRM: contactos, consentimiento (LOPDP) y proveedores."""

import pytest

RUC = "1712345675001"


async def _customer(client):
    return (await client.post(
        "/api/v1/customers",
        json={"ruc": RUC, "legal_name": "Importadora Demo", "email": "cli@demo.ec"},
    )).json()["id"]


@pytest.mark.asyncio
async def test_contacts_add_and_delete(client):
    cid = await _customer(client)
    c = (await client.post(
        f"/api/v1/customers/{cid}/contacts",
        json={"name": "Ana Pérez", "email": "ana@demo.ec", "role": "Compras", "is_primary": True},
    )).json()
    assert c["name"] == "Ana Pérez"

    # Aparece en el detalle del cliente.
    detail = (await client.get(f"/api/v1/customers/{cid}")).json()
    assert any(x["id"] == c["id"] for x in detail["contacts"])

    d = await client.delete(f"/api/v1/customers/{cid}/contacts/{c['id']}")
    assert d.status_code == 204
    detail2 = (await client.get(f"/api/v1/customers/{cid}")).json()
    assert all(x["id"] != c["id"] for x in detail2["contacts"])


@pytest.mark.asyncio
async def test_consent_grant_and_revoke(client):
    cid = await _customer(client)
    con = (await client.post(
        f"/api/v1/customers/{cid}/consents",
        json={"purpose": "Comunicaciones comerciales", "legal_basis": "consentimiento",
              "granted_at": "2026-01-01T00:00:00Z"},
    )).json()
    assert con["revoked_at"] is None

    rev = (await client.post(f"/api/v1/customers/{cid}/consents/{con['id']}/revoke")).json()
    assert rev["revoked_at"] is not None

    listed = (await client.get(f"/api/v1/customers/{cid}/consents")).json()
    assert listed[0]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_supplier_crud(client):
    s = (await client.post(
        "/api/v1/suppliers", json={"name": "Shenzhen Tech", "country": "CN"}
    )).json()
    sid = s["id"]
    upd = await client.patch(f"/api/v1/suppliers/{sid}", json={"country": "HK"})
    assert upd.status_code == 200 and upd.json()["country"] == "HK"

    listed = (await client.get("/api/v1/suppliers")).json()
    assert any(x["id"] == sid for x in listed)

    d = await client.delete(f"/api/v1/suppliers/{sid}")
    assert d.status_code == 204
    assert all(x["id"] != sid for x in (await client.get("/api/v1/suppliers")).json())
