"""Auto-vínculo de documentos con el checklist del expediente.

Cuando se sube/asocia un documento a un expediente con un doc_type que coincide
con un ítem del checklist, ese ítem se marca COMPLETE automáticamente, se recalcula
el readiness y se registra el evento. Esto reduce toques humanos: subir el documento
avanza el expediente solo.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist import ChecklistItem
from app.models.document import Document
from app.models.shipment import CaseEvent, CustomsCase
from app.services.checklist import recompute_readiness


async def autolink_document(session: AsyncSession, document: Document) -> ChecklistItem | None:
    """Si el documento está asociado a un caso y su doc_type calza con un ítem
    pendiente del checklist, lo completa y recalcula readiness. Devuelve el ítem
    completado (o None si no hubo coincidencia)."""
    if not document.customs_case_id or not document.doc_type or document.doc_type == "UNCLASSIFIED":
        return None

    case = await session.get(CustomsCase, document.customs_case_id)
    if case is None:
        return None

    # Siempre registramos que llegó un documento al expediente.
    session.add(
        CaseEvent(
            customs_case_id=case.id,
            event_type="DOCUMENT_RECEIVED",
            event_source="SYSTEM",
            normalized_payload={"doc_type": document.doc_type, "document_id": str(document.id)},
        )
    )

    item = await session.scalar(
        select(ChecklistItem)
        .where(
            ChecklistItem.customs_case_id == case.id,
            ChecklistItem.doc_type == document.doc_type,
            ChecklistItem.status != "COMPLETE",
        )
        .order_by(ChecklistItem.status.desc())  # MISSING antes que otros
    )
    if item is None:
        return None

    item.status = "COMPLETE"
    item.document_id = document.id
    await session.flush()
    await recompute_readiness(session, case)
    session.add(
        CaseEvent(
            customs_case_id=case.id,
            event_type="CHECKLIST_AUTO_COMPLETED",
            event_source="SYSTEM",
            normalized_payload={
                "doc_type": document.doc_type,
                "readiness": float(case.customs_readiness_score),
            },
        )
    )
    await session.flush()
    return item
