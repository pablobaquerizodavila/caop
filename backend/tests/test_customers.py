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
async def test_company_legal_rep_name_parts(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "IMPORTADORA ANDINA S.A.",
        "entity_type": "COMPANY",
        "legal_rep_name": "PEREZ GARCIA JUAN CARLOS",
        "legal_rep_first_name": "Juan",
        "legal_rep_middle_name": "Carlos",
        "legal_rep_last_name": "Pérez",
        "legal_rep_second_last_name": "García",
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["legal_rep_first_name"] == "Juan"
    assert body["legal_rep_last_name"] == "Pérez"
    assert body["legal_rep_second_last_name"] == "García"


@pytest.mark.asyncio
async def test_list_customers_search_by_name(client):
    # Persona natural con apellido Pérez.
    await client.post("/api/v1/customers", json={
        "ruc": VALID_RUC, "legal_name": "PEREZ JUAN", "first_name": "Juan", "last_name": "Pérez",
    })
    # Empresa cuyo representante se apellida Zambrano.
    await client.post("/api/v1/customers", json={
        "ruc": "0912345675001", "legal_name": "OTRA CIA", "entity_type": "COMPANY",
        "legal_rep_name": "ZAMBRANO ANA", "legal_rep_first_name": "Ana", "legal_rep_last_name": "Zambrano",
    })
    # Filtra por apellido de la persona natural.
    r1 = await client.get("/api/v1/customers?q=Pérez")
    assert r1.status_code == 200
    assert any(c["legal_name"] == "PEREZ JUAN" for c in r1.json())
    assert all(c["legal_name"] != "OTRA CIA" for c in r1.json())
    # Filtra por apellido del representante legal (empresa).
    r2 = await client.get("/api/v1/customers?q=Zambrano")
    assert any(c["legal_name"] == "OTRA CIA" for c in r2.json())
    # Sin coincidencias.
    r3 = await client.get("/api/v1/customers?q=inexistente-xyz")
    assert r3.json() == []


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
async def test_create_customer_structured_address(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "Con Dirección",
        "province": "Pichincha",
        "city": "Quito",
        "address": "Av. Amazonas N34-45 y Pereira",
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["country"] == "Ecuador"  # por defecto
    assert body["province"] == "Pichincha"
    assert body["city"] == "Quito"


@pytest.mark.asyncio
async def test_customer_name_parts_and_dispatch_same(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "PEREZ GARCIA JUAN CARLOS",
        "first_name": "Juan",
        "middle_name": "Carlos",
        "last_name": "Pérez",
        "second_last_name": "García",
        "province": "Pichincha",
        "city": "Quito",
        "address": "Av. Amazonas N34-45",
        "dispatch_same_as_address": True,
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["first_name"] == "Juan"
    assert body["second_last_name"] == "García"
    # Despacho = misma dirección: se copió la física.
    assert body["dispatch_same_as_address"] is True
    assert body["dispatch_city"] == "Quito"
    assert body["dispatch_address"] == "Av. Amazonas N34-45"


@pytest.mark.asyncio
async def test_customer_dispatch_distinct_address(client):
    payload = {
        "ruc": VALID_RUC,
        "legal_name": "Empresa X S.A.",
        "entity_type": "COMPANY",
        "legal_rep_name": "Ana Ruiz",
        "province": "Pichincha",
        "city": "Quito",
        "address": "Oficina matriz Quito",
        "dispatch_same_as_address": False,
        "dispatch_province": "Guayas",
        "dispatch_city": "Guayaquil",
        "dispatch_address": "Bodega puerto Guayaquil",
    }
    resp = await client.post("/api/v1/customers", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["dispatch_same_as_address"] is False
    assert body["dispatch_city"] == "Guayaquil"
    assert body["dispatch_address"] == "Bodega puerto Guayaquil"
    assert body["city"] == "Quito"  # la física no cambió


@pytest.mark.asyncio
async def test_delete_customer_without_history(client):
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Borrable"}
    )).json()["id"]
    r = await client.delete(f"/api/v1/customers/{cid}")
    assert r.status_code == 204, r.text
    assert (await client.get(f"/api/v1/customers/{cid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_customer_with_history_blocks_then_cascades(client):
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Con Historial"}
    )).json()["id"]
    # Cotización aceptada -> crea expediente asociado.
    q = {"customer_id": cid, "transport_mode": "OCEAN", "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})

    # Al aceptar se crea el expediente con un SLA (DOCUMENTS_COMPLETE).
    case_id = (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]
    assert len((await client.get(f"/api/v1/sla?entity_id={case_id}")).json()) >= 1

    # Sin cascade: protegido (409).
    blocked = await client.delete(f"/api/v1/customers/{cid}")
    assert blocked.status_code == 409
    assert (await client.get(f"/api/v1/customers/{cid}")).status_code == 200

    # Con cascade: elimina cliente + expediente + cotización + SLA (sin huérfanos).
    ok = await client.delete(f"/api/v1/customers/{cid}?cascade=true")
    assert ok.status_code == 204, ok.text
    assert (await client.get(f"/api/v1/customers/{cid}")).status_code == 404
    assert (await client.get(f"/api/v1/quotes/{qid}")).status_code == 404
    assert (await client.get(f"/api/v1/sla?entity_id={case_id}")).json() == []


@pytest.mark.asyncio
async def test_delete_unknown_customer_404(client):
    import uuid
    r = await client.delete(f"/api/v1/customers/{uuid.uuid4()}")
    assert r.status_code == 404


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
