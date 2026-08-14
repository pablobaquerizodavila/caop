"""Test del reporte operativo: estructura, throughput, top clientes y dinero en riesgo."""

from datetime import date, timedelta

import pytest

RUC = "1712345675001"


async def _case(client):
    await client.post("/api/v1/tax/rules/seed-ecuador-defaults")
    await client.post("/api/v1/requirements/seed-defaults")
    cid = (await client.post(
        "/api/v1/customers", json={"ruc": RUC, "legal_name": "Importadora Demo"}
    )).json()["id"]
    q = {"customer_id": cid, "transport_mode": "OCEAN", "origin_country": "CN",
         "calculation_date": "2026-01-01",
         "items": [{"quantity": "1", "unit_price": "100"}],
         "cost_lines": [{"category": "FEE", "estimated_amount": "50"}]}
    qid = (await client.post("/api/v1/quotes", json=q)).json()["id"]
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "SENT"})
    await client.post(f"/api/v1/quotes/{qid}/status", json={"status": "ACCEPTED"})
    return (await client.get(f"/api/v1/quotes/{qid}/case")).json()["id"]


@pytest.mark.asyncio
async def test_operations_report(client):
    case_id = await _case(client)
    # Contenedor vencido -> dinero en riesgo
    overdue = (date.today() - timedelta(days=10)).isoformat()
    await client.post(
        f"/api/v1/cases/{case_id}/containers",
        json={"container_number": "MSKU1234567", "arrival_date": overdue, "free_days": 5,
              "daily_rate": 100, "status": "AT_PORT"},
    )

    ops = (await client.get("/api/v1/analytics/operations")).json()
    assert {"stages", "throughput", "top_customers", "aforo", "money_at_risk"} <= ops.keys()

    # Throughput registra el expediente creado.
    assert sum(m["created"] for m in ops["throughput"]) >= 1
    # Top clientes incluye al importador.
    assert any(c["customer"] == "Importadora Demo" and c["cases"] >= 1 for c in ops["top_customers"])
    # Dinero en riesgo por demurrage (5 días * 100 = 500).
    assert ops["money_at_risk"]["demurrage"] == 500.0
    assert ops["money_at_risk"]["total"] >= 500.0
    # Las etapas están definidas aunque sin datos completos.
    assert [s["stage"] for s in ops["stages"]]
