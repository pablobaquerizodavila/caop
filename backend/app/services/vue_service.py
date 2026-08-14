"""Orquestación de control previo (VUE): solicitar/consultar permisos y gating del DAI.

Un expediente no puede preparar la DAI si tiene permisos de control previo
bloqueantes sin aprobar/eximir: es un requisito real de importación en Ecuador.
La interacción con la VUE usa un conector enchufable (hoy, simulador etiquetado).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import CaseEvent
from app.models.vue import VuePermit
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
