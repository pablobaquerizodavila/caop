"""Track & Trace: token público de seguimiento y construcción de la vista del cliente.

La vista pública traduce el estado interno del expediente a hitos y mensajes aptos
para el importador. No expone costos, márgenes, ni motivos técnicos de rechazo:
cualquier bloqueo/observación se presenta como un aviso neutral.
"""

from __future__ import annotations

import secrets
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.shipment import CaseEvent, Container, CustomsCase, Shipment
from app.schemas.tracking import (
    TrackContainer,
    TrackMilestone,
    TrackTransport,
    TrackView,
)
from app.services.demurrage import compute

# --- Diccionarios de presentación (cliente) ---

_STATUS_LABEL = {
    "CASE_CREATED": "Expediente recibido",
    "AWAITING_DOCUMENTS": "Reuniendo documentación",
    "READY_FOR_CUSTOMS": "Listo para trámite aduanero",
    "READY_FOR_SIGNATURE": "Preparando declaración",
    "SIGNED": "Declaración firmada",
    "TRANSMISSION_REJECTED": "Declaración en revisión",
    "ACCEPTED_SENAE": "Declaración presentada a la aduana",
    "LIQUIDATED": "Liquidación de tributos emitida",
    "PAID": "Tributos pagados",
    "AFORO_ASSIGNED": "En aforo aduanero",
    "OBSERVED": "En revisión por la aduana",
    "OBSERVATION_RESOLVED": "Observación resuelta",
    "RELEASED": "Mercancía liberada",
}

_STATUS_SEM = {
    "CASE_CREATED": "warn",
    "AWAITING_DOCUMENTS": "warn",
    "READY_FOR_CUSTOMS": "ok",
    "READY_FOR_SIGNATURE": "warn",
    "SIGNED": "warn",
    "TRANSMISSION_REJECTED": "risk",
    "ACCEPTED_SENAE": "ok",
    "LIQUIDATED": "ok",
    "PAID": "ok",
    "AFORO_ASSIGNED": "warn",
    "OBSERVED": "risk",
    "OBSERVATION_RESOLVED": "ok",
    "RELEASED": "ok",
}

_NEXT_STEP = {
    "SIGN": "Preparación y firma de la declaración",
    "TRANSMIT": "Envío de la declaración a la aduana",
    "LIQUIDATION": "Emisión de la liquidación de tributos",
    "PAYMENT": "Pago de tributos",
    "AFORO": "Asignación de aforo",
    "RELEASE": "Autorización de levante",
    "RESOLVE_OBSERVATION": "Atención de un requerimiento aduanero",
    "DELIVERY": "Coordinación de la entrega",
    "FIX_AND_RETRANSMIT": "Ajustes y reenvío de la declaración",
}

_CONTAINER_STATUS = {
    "IN_TRANSIT": "En tránsito",
    "AT_PORT": "En puerto",
    "GATE_OUT": "Retirado del puerto",
    "EMPTY_RETURNED": "Devuelto vacío",
}

_ALARM_LABEL = {
    "OK": "En plazo",
    "WARN": "Próximo a vencer",
    "AT_RISK": "Por vencer",
    "CRITICAL": "Vencido / demora",
}

# Estados que implican que el trámite aduanero ya inició/avanzó.
_CUSTOMS_STATES = {
    "ACCEPTED_SENAE", "LIQUIDATED", "PAID", "AFORO_ASSIGNED",
    "OBSERVED", "OBSERVATION_RESOLVED", "RELEASED",
}
_RELEASED_STATES = {"RELEASED"}


def generate_token() -> str:
    return secrets.token_urlsafe(24)


async def ensure_token(session: AsyncSession, case: CustomsCase) -> str:
    if not case.tracking_token:
        case.tracking_token = generate_token()
        await session.flush()
    return case.tracking_token


def public_url(token: str) -> str:
    return f"{settings.public_app_url.rstrip('/')}/track/{token}"


async def get_case_by_token(session: AsyncSession, token: str) -> CustomsCase | None:
    return await session.scalar(
        select(CustomsCase).where(CustomsCase.tracking_token == token)
    )


def _mode_label(mode: str | None) -> str | None:
    return {"OCEAN": "Marítimo", "AIR": "Aéreo"}.get(mode or "", mode)


def _vessel_or_flight(s: Shipment) -> str | None:
    if s.flight_number:
        return s.flight_number
    if s.vessel:
        return f"{s.vessel} {s.voyage}".strip() if s.voyage else s.vessel
    return None


def _first_event_ts(events: list[CaseEvent], *types: str) -> datetime | None:
    for e in events:  # events ya vienen ordenados por timestamp asc
        if e.event_type in types:
            return e.timestamp
    return None


def _last_event_ts(events: list[CaseEvent], *types: str) -> datetime | None:
    found = None
    for e in events:
        if e.event_type in types:
            found = e.timestamp
    return found


def _build_milestones(
    case: CustomsCase, shipment: Shipment | None, events: list[CaseEvent], today: date
) -> list[TrackMilestone]:
    readiness = float(case.customs_readiness_score or 0)
    state = case.current_state
    etd, eta, ata = (shipment.etd, shipment.eta, shipment.ata) if shipment else (None, None, None)

    docs_done = readiness >= 100 or state not in ("CASE_CREATED", "AWAITING_DOCUMENTS")
    departure_done = bool(ata) or (etd is not None and etd <= today) or state in _CUSTOMS_STATES
    arrival_done = ata is not None or state in _CUSTOMS_STATES or state in _RELEASED_STATES
    customs_done = state in _CUSTOMS_STATES or _first_event_ts(events, "TRANSMISSION_SENT") is not None
    released_done = state in _RELEASED_STATES or _first_event_ts(
        events, "CUSTOMS_RELEASED", "RELEASE_AUTHORIZED"
    ) is not None
    delivered_done = _first_event_ts(events, "DELIVERY", "DELIVERED") is not None

    specs = [
        ("RECEIVED", "Expediente recibido", True, case.created_at, None),
        (
            "DOCS", "Documentación completa", docs_done,
            _last_event_ts(events, "CHECKLIST_UPDATED") if docs_done else None,
            None if docs_done else "Estamos validando los documentos de tu importación",
        ),
        (
            "DEPARTURE", "Embarque en origen", departure_done, None,
            f"ETD {etd.isoformat()}" if etd else "Embarque por programar",
        ),
        (
            "ARRIVAL", "Arribo a destino", arrival_done, None,
            f"Arribo {ata.isoformat()}" if ata
            else (f"ETA {eta.isoformat()}" if eta else "Fecha por confirmar"),
        ),
        (
            "CUSTOMS", "Trámite aduanero (DAI)", customs_done,
            _first_event_ts(events, "TRANSMISSION_SENT", "ACCEPTED"),
            "Declaración aduanera presentada" if customs_done else "Declaración aduanera en preparación",
        ),
        (
            "RELEASED", "Levante autorizado", released_done,
            _first_event_ts(events, "CUSTOMS_RELEASED", "RELEASE_AUTHORIZED"), None,
        ),
        ("DELIVERED", "Entrega", delivered_done, _first_event_ts(events, "DELIVERY", "DELIVERED"), None),
    ]

    out: list[TrackMilestone] = []
    current_set = False
    for key, label, done, at, detail in specs:
        if done:
            status = "done"
        elif not current_set:
            status, current_set = "current", True
        else:
            status = "pending"
        out.append(TrackMilestone(key=key, label=label, status=status, at=at, detail=detail))
    return out


async def build_view(session: AsyncSession, case: CustomsCase) -> TrackView:
    today = date.today()
    shipment = await session.get(Shipment, case.shipment_id)
    customer = await session.get(Customer, shipment.customer_id) if shipment else None
    events = list(
        await session.scalars(
            select(CaseEvent)
            .where(CaseEvent.customs_case_id == case.id)
            .order_by(CaseEvent.timestamp)
        )
    )

    milestones = _build_milestones(case, shipment, events, today)
    done = sum(1 for m in milestones if m.status == "done")
    progress = round(done / len(milestones) * 100) if milestones else 0

    containers_out: list[TrackContainer] = []
    if shipment:
        containers = list(
            await session.scalars(
                select(Container)
                .where(Container.shipment_id == shipment.id)
                .order_by(Container.container_number)
            )
        )
        for c in containers:
            d = compute(c, today)
            containers_out.append(
                TrackContainer(
                    number=c.container_number,
                    status_label=_CONTAINER_STATUS.get(c.status, c.status),
                    last_free_day=d.last_free_day,
                    days_to_last_free_day=d.days_to_last_free_day,
                    alarm=d.alarm,
                    alarm_label=_ALARM_LABEL.get(d.alarm, d.alarm),
                )
            )

    attention = None
    if case.current_state in ("OBSERVED", "TRANSMISSION_REJECTED"):
        attention = (
            "Estamos gestionando un requerimiento con la aduana. "
            "Tu ejecutivo de comercio exterior te contactará con los próximos pasos."
        )
    elif case.blocker:
        attention = (
            "Hay un punto pendiente en tu expediente que estamos resolviendo. "
            "Tu ejecutivo de comercio exterior te contactará con los próximos pasos."
        )

    customer_name = "Cliente"
    if customer:
        customer_name = customer.trade_name or customer.legal_name

    transport = TrackTransport(
        mode=_mode_label(shipment.transport_mode) if shipment else None,
        origin=(shipment.pol or shipment.origin_country) if shipment else None,
        destination=shipment.pod if shipment else None,
        carrier=shipment.carrier if shipment else None,
        vessel_or_flight=_vessel_or_flight(shipment) if shipment else None,
        etd=shipment.etd if shipment else None,
        eta=shipment.eta if shipment else None,
        ata=shipment.ata if shipment else None,
    )

    last_update = events[-1].timestamp if events else case.updated_at

    return TrackView(
        reference=case.case_number,
        customer_name=customer_name,
        status_label=_STATUS_LABEL.get(case.current_state, case.current_state),
        status_sem=_STATUS_SEM.get(case.current_state, "warn"),
        progress_pct=progress,
        next_step=_NEXT_STEP.get(case.next_expected_event or "", None),
        attention=attention,
        transport=transport,
        milestones=milestones,
        containers=containers_out,
        last_update=last_update,
    )
