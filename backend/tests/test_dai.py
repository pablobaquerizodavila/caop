"""Tests de la DAI contra el simulador SENAE (S16)."""

import pytest

VALID_RUC = "1712345675001"


async def _accepted_case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={"tax_type": "AD_VALOREM", "hs_code": "8471.30.00", "percentage": "5",
              "base_formula": "CIF", "depends_on": [], "effective_from": "2020-01-01"},
    )
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": VALID_RUC, "legal_name": "Demo"}
    )).json()["id"]
    quote = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
             "calculation_date": "2026-01-01",
             "items": [{"hs_code": "8471.30.00", "quantity": "10", "unit_price": "100"}],
             "cost_lines": [{"category": "FEE", "estimated_amount": "200"}]}
    qid = (await client.post("/api/v1/quotes", json=quote)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


async def _ready_case(client):
    case_id = await _accepted_case(client)
    detail = (await client.get(f"/api/v1/cases/{case_id}")).json()
    for it in detail["checklist"]:
        await client.patch(
            f"/api/v1/cases/{case_id}/checklist/{it['id']}", json={"status": "COMPLETE"}
        )
    return case_id


async def _prep_sign(client, case_id):
    await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    await client.post(f"/api/v1/cases/{case_id}/dai/sign")


@pytest.mark.asyncio
async def test_prepare_requires_readiness(client):
    case_id = await _accepted_case(client)  # readiness 0
    r = await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_transmit_requires_signature(client):
    case_id = await _ready_case(client)
    await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    r = await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={"scenario": "ACCEPT"})
    assert r.status_code == 409  # sin firmar


@pytest.mark.asyncio
async def test_happy_path_to_release(client):
    case_id = await _ready_case(client)
    prep = await client.post(f"/api/v1/cases/{case_id}/dai/prepare")
    assert prep.status_code == 201 and prep.json()["status"] == "READY_FOR_SIGNATURE"
    sign = await client.post(f"/api/v1/cases/{case_id}/dai/sign")
    assert sign.json()["status"] == "SIGNED" and sign.json()["signed"] is True

    tr = await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={"scenario": "ACCEPT"})
    dec = tr.json()
    assert dec["status"] == "ACCEPTED"
    assert dec["external_ref"] and dec["raw_sent"] and dec["raw_response"]
    assert len(dec["exchanges"]) >= 2  # OUT + IN

    for expected in ["LIQUIDATED", "PAID", "AFORO_ASSIGNED"]:
        st = (await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})).json()["status"]
        assert st == expected
    rel = (await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})).json()
    assert rel["status"] == "RELEASED"
    assert rel["aforo_channel"] == "AUTOMATICO"


@pytest.mark.asyncio
async def test_idempotent_transmit(client):
    case_id = await _ready_case(client)
    await _prep_sign(client, case_id)
    first = (await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={})).json()
    again = (await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={})).json()
    assert first["external_ref"] == again["external_ref"]
    assert again["status"] == "ACCEPTED"  # no se re-transmite ni cambia


@pytest.mark.asyncio
async def test_reject_scenario(client):
    case_id = await _ready_case(client)
    await _prep_sign(client, case_id)
    dec = (await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={"scenario": "REJECT"})).json()
    assert dec["status"] == "REJECTED"
    assert dec["error_code"] == "SIM-VAL-001"


@pytest.mark.asyncio
async def test_unavailable_then_retry(client):
    case_id = await _ready_case(client)
    await _prep_sign(client, case_id)
    un = (await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={"scenario": "UNAVAILABLE"})).json()
    assert un["status"] == "SIGNED" and un["error_code"] == "UNAVAILABLE"
    ok = (await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={"scenario": "ACCEPT"})).json()
    assert ok["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_observation_flow(client):
    case_id = await _ready_case(client)
    await _prep_sign(client, case_id)
    await client.post(f"/api/v1/cases/{case_id}/dai/transmit", json={})
    await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})  # LIQUIDATED
    await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})  # PAID
    obs = (await client.post(
        f"/api/v1/cases/{case_id}/dai/advance",
        json={"aforo_channel": "FISICO", "observation": True},
    )).json()
    assert obs["status"] == "OBSERVED" and obs["aforo_channel"] == "FISICO"
    # No se puede avanzar con observación pendiente
    blocked = await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})
    assert blocked.status_code == 409
    res = (await client.post(f"/api/v1/cases/{case_id}/dai/resolve-observation")).json()
    assert res["status"] == "OBSERVATION_RESOLVED"
    rel = (await client.post(f"/api/v1/cases/{case_id}/dai/advance", json={})).json()
    assert rel["status"] == "RELEASED"
