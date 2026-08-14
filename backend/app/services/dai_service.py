"""Orquestación de la DAI: preparar → firmar → transmitir → aforo → levante.

Respeta invariantes: readiness 100% para preparar, firma humana obligatoria antes
de transmitir, e idempotencia (una DAI NUNCA se transmite dos veces). Usa el
conector SENAE (simulador) y registra cada intercambio.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customs_declaration import CustomsDeclaration
from app.models.shipment import CaseEvent, CustomsCase
from app.services import vue_service
from app.services.senae_connector import (
    SenaeResult,
    SenaeUnavailableError,
    get_senae_connector,
    map_external,
)


class DAIError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_declaration(session: AsyncSession, case_id) -> CustomsDeclaration | None:
    return await session.scalar(
        select(CustomsDeclaration).where(CustomsDeclaration.customs_case_id == case_id)
    )


async def _next_number(session: AsyncSession, year: int) -> str:
    prefix = f"DAI-SIM-{year}-"
    last = await session.scalar(
        select(func.max(CustomsDeclaration.declaration_number)).where(
            CustomsDeclaration.declaration_number.like(f"{prefix}%")
        )
    )
    seq = (int(last.split("-")[-1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _log(session: AsyncSession, case_id, event_type: str, payload: dict | None = None) -> None:
    session.add(
        CaseEvent(
            customs_case_id=case_id, event_type=event_type, event_source="SYSTEM",
            normalized_payload=payload,
        )
    )


def _record(dec: CustomsDeclaration, direction: str, data: dict) -> None:
    dec.exchanges = (dec.exchanges or []) + [{"direction": direction, "data": data}]


async def prepare(session: AsyncSession, case: CustomsCase) -> CustomsDeclaration:
    if float(case.customs_readiness_score or 0) < 100:
        raise DAIError("El expediente no está listo (readiness < 100%).")
    # Control previo (VUE): sin permisos bloqueantes aprobados/eximidos no hay DAI.
    pending = await vue_service.blocking_pending(session, case.id)
    if pending:
        names = ", ".join(f"{p.entity}/{p.document_code}" for p in pending)
        raise DAIError(f"Control previo (VUE) pendiente de aprobación: {names}.")
    existing = await get_declaration(session, case.id)
    if existing is not None:
        return existing
    dec = CustomsDeclaration(
        customs_case_id=case.id,
        declaration_number=await _next_number(session, case.created_at.year if case.created_at else 2026),
        regime=case.customs_regime,
        status="READY_FOR_SIGNATURE",
    )
    session.add(dec)
    await session.flush()
    _log(session, case.id, "DAI_PREPARED", {"declaration": dec.declaration_number})
    case.current_state = "READY_FOR_SIGNATURE"
    case.next_expected_event = "SIGN"
    return dec


async def sign(session: AsyncSession, case: CustomsCase, signed_by: str) -> CustomsDeclaration:
    dec = await get_declaration(session, case.id)
    if dec is None:
        raise DAIError("No hay DAI preparada.")
    if dec.status != "READY_FOR_SIGNATURE":
        raise DAIError(f"La DAI no está lista para firma (estado {dec.status}).")
    dec.signed = True
    dec.signed_by = signed_by
    dec.signed_at = _now()
    dec.status = "SIGNED"
    _log(session, case.id, "DAI_SIGNED", {"signed_by": signed_by})
    case.current_state = "SIGNED"
    case.next_expected_event = "TRANSMIT"
    return dec


async def transmit(session: AsyncSession, case: CustomsCase, scenario: str = "ACCEPT") -> CustomsDeclaration:
    dec = await get_declaration(session, case.id)
    if dec is None:
        raise DAIError("No hay DAI preparada.")
    if not dec.signed:
        raise DAIError("La DAI debe estar firmada antes de transmitir.")
    # Idempotencia: solo se transmite desde SIGNED o reintento tras REJECTED.
    if dec.status not in ("SIGNED", "REJECTED"):
        return dec  # ya transmitida; no se transmite dos veces

    payload = {
        "simulated": True,
        "declaration_number": dec.declaration_number,
        "regime": dec.regime,
        "case_number": case.case_number,
        "readiness": float(case.customs_readiness_score or 0),
    }
    dec.raw_sent = payload
    _record(dec, "OUT", payload)

    conn = get_senae_connector()
    try:
        result: SenaeResult = conn.transmit(payload, scenario)
    except SenaeUnavailableError as exc:
        dec.error_code = "UNAVAILABLE"
        dec.error_description = str(exc)
        _record(dec, "IN", {"error": "UNAVAILABLE"})
        _log(session, case.id, "INTEGRATION_DEGRADED", {"service": "SENAE", "retry": True})
        return dec  # sigue en SIGNED -> reintentable

    dec.raw_response = result.payload
    _record(dec, "IN", result.payload)
    internal = map_external(result.external_status)

    if internal == "REJECTED":
        dec.status = "REJECTED"
        dec.error_code = result.error_code
        dec.error_description = result.error_description
        case.current_state = "TRANSMISSION_REJECTED"
        case.next_expected_event = "FIX_AND_RETRANSMIT"
        case.blocker = f"DAI rechazada: {result.error_description}"
        _log(session, case.id, "VALIDATION_ERROR", {"error_code": result.error_code})
        return dec

    # ACCEPTED
    dec.status = "ACCEPTED"
    dec.external_ref = result.external_ref
    dec.transmitted_at = _now()
    dec.error_code = None
    dec.error_description = None
    case.current_state = "ACCEPTED_SENAE"
    case.next_expected_event = "LIQUIDATION"
    case.blocker = None
    _log(session, case.id, "TRANSMISSION_SENT", {"ref": result.external_ref})
    _log(session, case.id, "ACCEPTED", {"ref": result.external_ref})
    return dec


_STEP = {
    "ACCEPTED": "LIQUIDATE",
    "LIQUIDATED": "PAY",
    "PAID": "AFORO",
    "AFORO_ASSIGNED": "RELEASE",
    "OBSERVATION_RESOLVED": "RELEASE",
}


async def advance(
    session: AsyncSession, case: CustomsCase, aforo_channel: str | None = None,
    observation: bool = False,
) -> CustomsDeclaration:
    dec = await get_declaration(session, case.id)
    if dec is None:
        raise DAIError("No hay DAI.")
    if dec.status == "OBSERVED":
        raise DAIError("Hay una observación pendiente; resuélvela antes de continuar.")
    if dec.status == "RELEASED":
        raise DAIError("La mercancía ya fue liberada.")
    step = _STEP.get(dec.status)
    if step is None:
        raise DAIError(f"No se puede avanzar desde el estado {dec.status}.")

    options = {"aforo_channel": aforo_channel, "observation": observation}
    result = get_senae_connector().next_event(dec.external_ref or "", step, options)
    dec.raw_response = result.payload
    _record(dec, "IN", result.payload)
    internal = map_external(result.external_status)

    dec.status = internal
    if internal == "AFORO_ASSIGNED":
        dec.aforo_channel = (aforo_channel or "AUTOMATICO").upper()
        _log(session, case.id, "CHANNEL_ASSIGNED", {"aforo_channel": dec.aforo_channel})
    elif internal == "OBSERVED":
        dec.aforo_channel = (aforo_channel or "FISICO").upper()
        case.blocker = "Observación aduanera pendiente de atención."
        _log(session, case.id, "OBSERVATION_RECEIVED", {"aforo_channel": dec.aforo_channel})
    elif internal == "RELEASED":
        case.blocker = None
        _log(session, case.id, "RELEASE_AUTHORIZED", {})
        _log(session, case.id, "CUSTOMS_RELEASED", {})
    else:
        _log(session, case.id, internal, {})

    case.current_state = internal
    case.next_expected_event = {
        "LIQUIDATED": "PAYMENT", "PAID": "AFORO", "AFORO_ASSIGNED": "RELEASE",
        "OBSERVED": "RESOLVE_OBSERVATION", "RELEASED": "DELIVERY",
    }.get(internal)
    return dec


async def resolve_observation(session: AsyncSession, case: CustomsCase) -> CustomsDeclaration:
    dec = await get_declaration(session, case.id)
    if dec is None or dec.status != "OBSERVED":
        raise DAIError("No hay una observación pendiente.")
    result = get_senae_connector().next_event(dec.external_ref or "", "RESOLVE_OBSERVATION", {})
    dec.raw_response = result.payload
    _record(dec, "IN", result.payload)
    dec.status = map_external(result.external_status)  # OBSERVATION_RESOLVED
    case.current_state = dec.status
    case.next_expected_event = "RELEASE"
    case.blocker = None
    _log(session, case.id, "OBSERVATION_RESOLVED", {})
    return dec
