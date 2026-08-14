"""Tests del motor de SLA: umbrales, evaluación/escalamiento y ciclo por hito."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.sla import SLAInstance
from app.services.sla_engine import _status_for, evaluate_all

VALID_RUC = "1712345675001"


def test_status_thresholds():
    assert _status_for(50) == ("ON_TIME", 0)
    assert _status_for(70) == ("AT_RISK", 1)
    assert _status_for(85) == ("CRITICAL", 2)
    assert _status_for(100) == ("BREACHED", 3)
    assert _status_for(120) == ("BREACHED", 4)


@pytest.mark.asyncio
async def test_evaluate_breaches_past_deadline(db_sessionmaker):
    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as s:
        sla = SLAInstance(
            entity_type="CUSTOMS_CASE",
            entity_id=uuid.uuid4(),
            milestone="X",
            start_time=now - timedelta(hours=10),
            deadline=now - timedelta(hours=1),
            status="ON_TIME",
        )
        s.add(sla)
        await s.flush()
        res = await evaluate_all(s)
        assert res["breached"] >= 1
        await s.refresh(sla)
        assert sla.status == "BREACHED"
        assert sla.escalation_level >= 3


async def _accept_case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post(
        "/api/v1/tax/rules",
        json={"tax_type": "AD_VALOREM", "hs_code": "8471.30.00", "percentage": "5",
              "base_formula": "CIF", "depends_on": [], "effective_from": "2020-01-01"},
    )
    await client.post("/api/v1/requirements/seed-defaults")
    await client.post("/api/v1/sla/seed-defaults")
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


@pytest.mark.asyncio
async def test_seed_and_case_sla_created(client):
    seed = await client.post("/api/v1/sla/seed-defaults")
    assert "INTERNO" in seed.json()["calendars"]
    assert "DOCUMENTS_COMPLETE" in seed.json()["policies"]

    case_id = await _accept_case(client)
    slas = (await client.get(f"/api/v1/sla?entity_id={case_id}")).json()
    assert len(slas) == 1
    assert slas[0]["milestone"] == "DOCUMENTS_COMPLETE"
    assert slas[0]["status"] == "ON_TIME"
    assert slas[0]["deadline"] is not None


@pytest.mark.asyncio
async def test_sla_met_when_documents_complete(client):
    case_id = await _accept_case(client)
    detail = (await client.get(f"/api/v1/cases/{case_id}")).json()
    for it in detail["checklist"]:
        await client.patch(
            f"/api/v1/cases/{case_id}/checklist/{it['id']}", json={"status": "COMPLETE"}
        )
    slas = (await client.get(f"/api/v1/sla?entity_id={case_id}")).json()
    assert slas[0]["status"] == "MET"
