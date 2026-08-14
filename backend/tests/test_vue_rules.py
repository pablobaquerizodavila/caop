"""Tests de reglas HS -> control previo (VUE): seed, autosugerencia y aplicación."""

import pytest

RUC = "1712345675001"


async def _seed(client, with_rules: bool):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    if with_rules:
        await client.post("/api/v1/vue/rules/seed-defaults")


async def _case_with_hs(client, hs_code: str):
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Demo"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100", "hs_code": hs_code}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


@pytest.mark.asyncio
async def test_seed_and_list_rules(client):
    await client.post("/api/v1/vue/rules/seed-defaults")
    rules = (await client.get("/api/v1/vue/rules")).json()
    assert any(r["entity"] == "ARCSA" and r["hs_prefix"] == "33" for r in rules)


@pytest.mark.asyncio
async def test_auto_suggest_on_conversion(client):
    await _seed(client, with_rules=True)
    # Cosméticos (subpartida 3304...) -> ARCSA registro sanitario.
    case_id = await _case_with_hs(client, "3304.99.00.00")
    permits = (await client.get(f"/api/v1/cases/{case_id}/vue-permits")).json()
    arcsa = [p for p in permits if p["entity"] == "ARCSA"]
    assert arcsa, "Debió autosugerirse el control previo de ARCSA por la subpartida 33"
    assert arcsa[0]["status"] == "REQUIRED"
    assert "3" in (arcsa[0]["notes"] or "")

    # El expediente ya trae el permiso -> no quedan sugerencias pendientes.
    sug = (await client.get(f"/api/v1/cases/{case_id}/vue-suggestions")).json()
    assert all(s["entity"] != "ARCSA" for s in sug)


@pytest.mark.asyncio
async def test_suggestions_when_rules_added_later(client):
    # Sin reglas al convertir -> no se autoagrega nada.
    await _seed(client, with_rules=False)
    case_id = await _case_with_hs(client, "8516.60.00.00")  # electrodoméstico -> INEN
    assert (await client.get(f"/api/v1/cases/{case_id}/vue-permits")).json() == []

    # Se cargan las reglas después: ahora hay sugerencias y se pueden aplicar.
    await client.post("/api/v1/vue/rules/seed-defaults")
    sug = (await client.get(f"/api/v1/cases/{case_id}/vue-suggestions")).json()
    assert any(s["entity"] == "INEN" and s["hs_prefix"] == "8516" for s in sug)

    applied = (await client.post(
        f"/api/v1/cases/{case_id}/vue-permits/apply-suggestions"
    )).json()
    assert any(p["entity"] == "INEN" for p in applied)
    # Aplicadas -> ya no se vuelven a sugerir (idempotente).
    sug2 = (await client.get(f"/api/v1/cases/{case_id}/vue-suggestions")).json()
    assert all(s["entity"] != "INEN" for s in sug2)


@pytest.mark.asyncio
async def test_rule_crud(client):
    created = await client.post(
        "/api/v1/vue/rules",
        json={"hs_prefix": "2203", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
              "description": "Cerveza"},
    )
    assert created.status_code == 201
    rid = created.json()["id"]

    upd = await client.patch(f"/api/v1/vue/rules/{rid}", json={"blocking": False, "status": "INACTIVE"})
    assert upd.status_code == 200
    assert upd.json()["blocking"] is False and upd.json()["status"] == "INACTIVE"

    dele = await client.delete(f"/api/v1/vue/rules/{rid}")
    assert dele.status_code == 204
    assert all(r["id"] != rid for r in (await client.get("/api/v1/vue/rules")).json())


@pytest.mark.asyncio
async def test_no_suggestion_for_unmatched_hs(client):
    await _seed(client, with_rules=True)
    case_id = await _case_with_hs(client, "9999.99.99.99")  # sin regla
    assert (await client.get(f"/api/v1/cases/{case_id}/vue-suggestions")).json() == []
