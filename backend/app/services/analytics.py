"""Métricas ejecutivas (dashboard §33-34): automatización y toques humanos.

Todo se calcula sobre los datos reales del sistema. Los KPI centrales del prompt:
- HUMAN TOUCHES PER SHIPMENT: cuántas veces intervino una persona por expediente.
- STRAIGHT-THROUGH PROCESSING: % de expedientes que avanzaron sin intervención.
- AUTOMATION RATE: % de eventos generados por el sistema vs. por personas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.customs_declaration import CustomsDeclaration
from app.models.notification import Notification
from app.models.quote import Quote
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.models.warehouse import WarehouseStorage
from app.services.demurrage import compute as compute_demurrage
from app.services.warehouse import compute as compute_storage


def _r(v: float | None, n: int = 1) -> float:
    return round(float(v), n) if v is not None else 0.0


async def _count(session: AsyncSession, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for w in where:
        stmt = stmt.where(w)
    return int(await session.scalar(stmt) or 0)


async def _group(session: AsyncSession, col) -> dict[str, int]:
    rows = await session.execute(select(col, func.count()).group_by(col))
    return {str(k): int(v) for k, v in rows.all()}


async def overview(session: AsyncSession) -> dict:
    total_cases = await _count(session, CustomsCase)
    cases_by_state = await _group(session, CustomsCase.current_state)
    ready = cases_by_state.get("READY_FOR_CUSTOMS", 0)
    avg_readiness = _r(await session.scalar(select(func.avg(CustomsCase.customs_readiness_score))))

    total_events = await _count(session, CaseEvent)
    user_events = await _count(session, CaseEvent, CaseEvent.event_source == "USER")
    system_events = total_events - user_events

    # Expedientes con al menos un toque humano
    cases_with_touch = int(
        await session.scalar(
            select(func.count(func.distinct(CaseEvent.customs_case_id))).where(
                CaseEvent.event_source == "USER"
            )
        )
        or 0
    )
    straight_through = (
        _r((total_cases - cases_with_touch) / total_cases * 100) if total_cases else 0.0
    )
    human_touches_per_shipment = _r(user_events / total_cases, 2) if total_cases else 0.0
    automation_rate = _r(system_events / total_events * 100) if total_events else 0.0

    # Tiempo de preparación (aprox): creado -> listo para aduana
    rows = await session.execute(
        select(CustomsCase.created_at, CustomsCase.updated_at).where(
            CustomsCase.current_state == "READY_FOR_CUSTOMS"
        )
    )
    diffs = [
        (u - c).total_seconds() / 3600 for c, u in rows.all() if c and u and u > c
    ]
    avg_prep_hours = _r(mean(diffs)) if diffs else 0.0

    total_quotes = await _count(session, Quote)
    quotes_by_status = await _group(session, Quote.status)
    accepted = quotes_by_status.get("ACCEPTED", 0)
    conversion_rate = _r(accepted / total_quotes * 100) if total_quotes else 0.0

    notif_total = await _count(session, Notification)
    notif_by_status = await _group(session, Notification.status)

    sla_open = await _count(session, SLAInstance, SLAInstance.status != "MET")
    sla_breached = await _count(session, SLAInstance, SLAInstance.status == "BREACHED")
    sla_at_risk = await _count(
        session, SLAInstance, SLAInstance.status.in_(["AT_RISK", "CRITICAL"])
    )

    return {
        "cases": {
            "total": total_cases,
            "ready_for_customs": ready,
            "avg_readiness": avg_readiness,
            "by_state": cases_by_state,
            "avg_prep_hours": avg_prep_hours,
        },
        "automation": {
            "human_touches_per_shipment": human_touches_per_shipment,
            "straight_through_rate": straight_through,
            "automation_rate": automation_rate,
            "system_events": system_events,
            "user_events": user_events,
        },
        "commercial": {
            "total_quotes": total_quotes,
            "accepted": accepted,
            "conversion_rate": conversion_rate,
            "by_status": quotes_by_status,
        },
        "notifications": {"total": notif_total, "by_status": notif_by_status},
        "sla": {"open": sla_open, "at_risk": sla_at_risk, "breached": sla_breached},
    }


# Etapas del ciclo (evento inicio -> evento fin). Se mide la duración entre la
# primera ocurrencia de cada evento por expediente.
_STAGE_DEFS = [
    ("Recepción → DAI preparada", "CASE_CREATED", "DAI_PREPARED"),
    ("DAI preparada → firmada", "DAI_PREPARED", "DAI_SIGNED"),
    ("Firmada → aceptada SENAE", "DAI_SIGNED", "ACCEPTED"),
    ("Aceptada → levante", "ACCEPTED", "CUSTOMS_RELEASED"),
]


async def operations(session: AsyncSession) -> dict:
    # --- Tiempos de ciclo por etapa ---
    ev_rows = await session.execute(
        select(CaseEvent.customs_case_id, CaseEvent.event_type, CaseEvent.timestamp)
        .order_by(CaseEvent.timestamp)
    )
    first: dict = {}
    for cid, etype, ts in ev_rows.all():
        d = first.setdefault(cid, {})
        d.setdefault(etype, ts)  # primera ocurrencia

    stages = []
    for label, a, b in _STAGE_DEFS:
        diffs = [
            (d[b] - d[a]).total_seconds() / 3600
            for d in first.values()
            if a in d and b in d and d[b] > d[a]
        ]
        stages.append({"stage": label, "avg_hours": _r(mean(diffs)) if diffs else 0.0,
                       "n": len(diffs)})

    # --- Throughput mensual (creados vs. liberados) ---
    created_by_month: dict[str, int] = defaultdict(int)
    for (c,) in (await session.execute(select(CustomsCase.created_at))).all():
        if c:
            created_by_month[c.strftime("%Y-%m")] += 1
    released_by_month: dict[str, int] = defaultdict(int)
    rel = await session.execute(
        select(CaseEvent.timestamp).where(CaseEvent.event_type == "CUSTOMS_RELEASED")
    )
    for (t,) in rel.all():
        if t:
            released_by_month[t.strftime("%Y-%m")] += 1
    months = sorted(set(created_by_month) | set(released_by_month))
    throughput = [
        {"month": m, "created": created_by_month.get(m, 0), "released": released_by_month.get(m, 0)}
        for m in months
    ]

    # --- Top clientes por nº de expedientes y landed cost ---
    cust_rows = await session.execute(
        select(
            Customer.legal_name,
            func.count(func.distinct(CustomsCase.id)),
            func.coalesce(func.sum(Quote.landed_cost_total), 0),
        )
        .select_from(CustomsCase)
        .join(Shipment, CustomsCase.shipment_id == Shipment.id)
        .join(Customer, Shipment.customer_id == Customer.id)
        .join(Quote, Shipment.source_quote_id == Quote.id, isouter=True)
        .group_by(Customer.legal_name)
        .order_by(func.count(func.distinct(CustomsCase.id)).desc())
        .limit(10)
    )
    top_customers = [
        {"customer": name, "cases": int(cases), "landed_cost": _r(float(lc), 2)}
        for name, cases, lc in cust_rows.all()
    ]

    # --- Distribución de canal de aforo ---
    aforo_rows = await session.execute(
        select(CustomsDeclaration.aforo_channel, func.count())
        .where(CustomsDeclaration.aforo_channel.is_not(None))
        .group_by(CustomsDeclaration.aforo_channel)
    )
    aforo = {str(k): int(v) for k, v in aforo_rows.all()}

    # --- Dinero en riesgo (demurrage + almacenaje) ---
    today = date.today()
    conts = list(await session.scalars(select(Container)))
    dem = sum(
        (compute_demurrage(c, today).estimated_demurrage for c in conts
         if c.status != "EMPTY_RETURNED"),
        0,
    )
    sts = list(await session.scalars(select(WarehouseStorage)))
    stg = sum(
        (compute_storage(s, today).estimated_storage for s in sts if s.status != "WITHDRAWN"),
        0,
    )
    money_at_risk = {
        "demurrage": _r(float(dem), 2), "storage": _r(float(stg), 2),
        "total": _r(float(dem) + float(stg), 2),
    }

    return {
        "stages": stages,
        "throughput": throughput,
        "top_customers": top_customers,
        "aforo": aforo,
        "money_at_risk": money_at_risk,
    }
