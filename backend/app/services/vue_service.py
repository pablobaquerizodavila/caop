"""Orquestación de control previo (VUE): solicitar/consultar permisos y gating del DAI.

Un expediente no puede preparar la DAI si tiene permisos de control previo
bloqueantes sin aprobar/eximir: es un requisito real de importación en Ecuador.
La interacción con la VUE usa un conector enchufable (hoy, simulador etiquetado).
"""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote, QuoteItem
from app.models.shipment import CaseEvent, CustomsCase, Shipment
from app.models.vue import VuePermit, VueRule
from app.services.vue_connector import (
    VueUnavailableError,
    get_vue_connector,
    map_vue_external,
)

# Catálogo de referencia (punto de partida — VERIFICAR contra normativa vigente).
# entity = entidad emisora; document_code = documento de control previo.
CATALOG: list[dict] = [
    {"entity": "INEN", "document_code": "CRC",
     "description": "Certificado de Reconocimiento (Reglamento Técnico INEN)"},
    {"entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
     "description": "Registro / Notificación sanitaria (ARCSA)"},
    {"entity": "ARCSA", "document_code": "AUTORIZACION_IMPORTACION",
     "description": "Autorización de importación (ARCSA)"},
    {"entity": "AGROCALIDAD", "document_code": "AZSV",
     "description": "Autorización zoosanitaria / fitosanitaria (Agrocalidad)"},
    {"entity": "AGROCALIDAD", "document_code": "CERT_FITOSANITARIO",
     "description": "Certificado fitosanitario"},
    {"entity": "MPCEIP", "document_code": "LICENCIA_IMPORTACION",
     "description": "Licencia / autorización previa (MPCEIP / MIPRO)"},
    {"entity": "MSP", "document_code": "PERMISO_PREVIO",
     "description": "Permiso previo (Ministerio de Salud Pública)"},
]


def _log(session: AsyncSession, case_id, event_type: str, payload: dict | None = None) -> None:
    session.add(
        CaseEvent(
            customs_case_id=case_id, event_type=event_type, event_source="SYSTEM",
            normalized_payload=payload,
        )
    )


async def list_permits(session: AsyncSession, case_id) -> list[VuePermit]:
    return list(
        await session.scalars(
            select(VuePermit)
            .where(VuePermit.customs_case_id == case_id)
            .order_by(VuePermit.created_at)
        )
    )


async def request_permit(
    session: AsyncSession, permit: VuePermit, scenario: str = "APPROVE"
) -> VuePermit:
    conn = get_vue_connector()
    payload = {
        "entity": permit.entity,
        "document_code": permit.document_code,
        "case_id": str(permit.customs_case_id),
    }
    try:
        result = conn.request_permit(payload, scenario)
    except VueUnavailableError as exc:
        permit.error_description = str(exc)
        _log(session, permit.customs_case_id, "INTEGRATION_DEGRADED",
             {"service": "VUE", "retry": True})
        return permit  # queda como estaba -> reintentable

    internal = map_vue_external(result.external_status)
    permit.status = internal
    permit.external_ref = result.external_ref or permit.external_ref
    if result.permit_number:
        permit.permit_number = result.permit_number
    if result.valid_until:
        permit.valid_until = date.fromisoformat(result.valid_until)
        permit.issued_at = date.today()
    permit.error_description = result.error_description

    event = {
        "APPROVED": "VUE_PERMIT_APPROVED",
        "REJECTED": "VUE_PERMIT_REJECTED",
        "REQUESTED": "VUE_PERMIT_REQUESTED",
    }.get(internal, "VUE_PERMIT_UPDATED")
    _log(session, permit.customs_case_id, event,
         {"entity": permit.entity, "document_code": permit.document_code,
          "ref": permit.external_ref})
    await session.flush()
    return permit


async def mark_exempt(session: AsyncSession, permit: VuePermit, reason: str | None) -> VuePermit:
    permit.status = "EXEMPT"
    permit.error_description = None
    if reason:
        permit.notes = reason
    _log(session, permit.customs_case_id, "VUE_PERMIT_EXEMPT",
         {"entity": permit.entity, "document_code": permit.document_code})
    await session.flush()
    return permit


async def blocking_pending(session: AsyncSession, case_id) -> list[VuePermit]:
    """Permisos bloqueantes que aún NO satisfacen el despacho (no aprobados/vigentes)."""
    today = date.today()
    permits = await list_permits(session, case_id)
    return [p for p in permits if p.blocking and not p.is_satisfied(today)]


# --------------------------------------------------------------------------- #
#  Reglas HS -> control previo (autosugerencia por subpartida)
# --------------------------------------------------------------------------- #
# Catálogo de REFERENCIA — verificar contra la normativa vigente. No es oficial.
RULE_DEFAULTS: list[dict] = [
    {"hs_prefix": "01", "entity": "AGROCALIDAD", "document_code": "AZSV",
     "description": "Animales vivos — autorización zoosanitaria"},
    {"hs_prefix": "06", "entity": "AGROCALIDAD", "document_code": "AZSV",
     "description": "Plantas vivas — autorización fitosanitaria"},
    {"hs_prefix": "07", "entity": "AGROCALIDAD", "document_code": "CERT_FITOSANITARIO",
     "description": "Hortalizas — certificado fitosanitario"},
    {"hs_prefix": "08", "entity": "AGROCALIDAD", "document_code": "CERT_FITOSANITARIO",
     "description": "Frutas — certificado fitosanitario"},
    {"hs_prefix": "04", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
     "description": "Lácteos/procesados — registro/notificación sanitaria"},
    {"hs_prefix": "19", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
     "description": "Preparaciones alimenticias — registro sanitario"},
    {"hs_prefix": "21", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
     "description": "Preparaciones alimenticias diversas — registro sanitario"},
    {"hs_prefix": "30", "entity": "ARCSA", "document_code": "AUTORIZACION_IMPORTACION",
     "description": "Medicamentos — autorización/registro sanitario"},
    {"hs_prefix": "33", "entity": "ARCSA", "document_code": "REGISTRO_SANITARIO",
     "description": "Cosméticos — notificación sanitaria obligatoria"},
    {"hs_prefix": "3808", "entity": "AGROCALIDAD", "document_code": "AUTORIZACION_IMPORTACION",
     "description": "Plaguicidas — autorización de importación"},
    {"hs_prefix": "4011", "entity": "INEN", "document_code": "CRC",
     "description": "Neumáticos — Certificado de Reconocimiento (reglamento técnico)"},
    {"hs_prefix": "8418", "entity": "INEN", "document_code": "CRC",
     "description": "Refrigeración — Certificado de Reconocimiento (eficiencia/rotulado)"},
    {"hs_prefix": "8516", "entity": "INEN", "document_code": "CRC",
     "description": "Electrodomésticos — Certificado de Reconocimiento (reglamento técnico)"},
]


def _normalize_hs(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


async def seed_vue_rules(session: AsyncSession) -> list[str]:
    created: list[str] = []
    for spec in RULE_DEFAULTS:
        exists = await session.scalar(
            select(VueRule).where(
                VueRule.hs_prefix == spec["hs_prefix"],
                VueRule.entity == spec["entity"],
                VueRule.document_code == spec["document_code"],
            )
        )
        if exists:
            continue
        session.add(VueRule(status="ACTIVE", note="referencia — verificar", **spec))
        created.append(f"{spec['hs_prefix']}->{spec['entity']}/{spec['document_code']}")
    await session.flush()
    return created


async def _hs_codes_for_case(session: AsyncSession, case_id) -> list[str]:
    case = await session.get(CustomsCase, case_id)
    if case is None:
        return []
    shipment = await session.get(Shipment, case.shipment_id)
    if shipment is None or shipment.source_quote_id is None:
        return []
    rows = await session.scalars(
        select(QuoteItem.hs_code).where(QuoteItem.quote_id == shipment.source_quote_id)
    )
    return [c for c in rows if c]


def match_rules(rules: list[VueRule], hs_codes: list[str]) -> list[VueRule]:
    norm_codes = [_normalize_hs(c) for c in hs_codes]
    out: list[VueRule] = []
    for rule in rules:
        prefix = _normalize_hs(rule.hs_prefix)
        if prefix and any(code.startswith(prefix) for code in norm_codes):
            out.append(rule)
    return out


async def suggest_for_case(session: AsyncSession, case_id) -> list[VueRule]:
    """Reglas HS que aplican al expediente y aún NO están agregadas como permiso."""
    hs_codes = await _hs_codes_for_case(session, case_id)
    if not hs_codes:
        return []
    rules = list(await session.scalars(select(VueRule).where(VueRule.status == "ACTIVE")))
    matched = match_rules(rules, hs_codes)
    existing = {(p.entity, p.document_code) for p in await list_permits(session, case_id)}
    return [r for r in matched if (r.entity, r.document_code) not in existing]


async def apply_suggestions(session: AsyncSession, case_id) -> list[VuePermit]:
    """Crea permisos REQUIRED para las reglas HS que aplican y no estén ya agregadas."""
    suggestions = await suggest_for_case(session, case_id)
    created: list[VuePermit] = []
    for rule in suggestions:
        permit = VuePermit(
            customs_case_id=case_id,
            entity=rule.entity,
            document_code=rule.document_code,
            description=rule.description,
            blocking=rule.blocking,
            status="REQUIRED",
            notes=f"Autosugerido por subpartida {rule.hs_prefix}",
        )
        session.add(permit)
        created.append(permit)
    if created:
        _log(session, case_id, "VUE_RULES_APPLIED",
             {"count": len(created),
              "permits": [f"{p.entity}/{p.document_code}" for p in created]})
        await session.flush()
    return created
