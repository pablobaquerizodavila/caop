"""Tests de la API del Tax Rule Engine y el simulador."""

import pytest


@pytest.mark.asyncio
async def test_seed_and_simulate(client):
    # Sembrar tributos generales (FODINFA, IVA)
    seed = await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    assert seed.status_code == 200
    assert set(seed.json()["created"]) == {"FODINFA", "IVA"}

    # Crear un AD_VALOREM para una subpartida
    rule = await client.post(
        "/api/v1/tax/rules",
        json={
            "tax_type": "AD_VALOREM",
            "hs_code": "8471.30.00",
            "percentage": "5",
            "base_formula": "CIF",
            "depends_on": [],
            "effective_from": "2020-01-01",
        },
    )
    assert rule.status_code == 201

    # Simular
    resp = await client.post(
        "/api/v1/tax/simulate",
        json={
            "calculation_date": "2026-01-01",
            "items": [
                {
                    "hs_code": "8471.30.00",
                    "invoice_value": "1000",
                    "freight": "100",
                    "insurance": "10",
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    item = body["items"][0]
    comps = {c["tax_type"]: c for c in item["components"]}
    assert comps["AD_VALOREM"]["amount"] == 55.50
    assert comps["FODINFA"]["amount"] == 5.55
    assert comps["IVA"]["amount"] == 175.66
    assert item["total_taxes"] == 236.71
    # Los tributos sembrados NO están verificados
    assert comps["FODINFA"]["verified"] is False
    assert "estimación" in body["disclaimer"].lower()


@pytest.mark.asyncio
async def test_seed_is_idempotent(client):
    first = await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    second = await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    assert first.json()["created"]  # creó algo
    assert second.json()["created"] == []  # nada nuevo la segunda vez
