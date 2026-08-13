"""Motor de checklist documental y cálculo de readiness del expediente."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist import ChecklistItem, Requirement
from app.models.shipment import CustomsCase


@dataclass
class CaseContext:
    transport_mode: str | None
    has_agreement: bool = False


def requirement_applies(req: Requirement, ctx: CaseContext) -> bool:
    cond = req.applies_when or {}
    if "transport_mode" in cond and ctx.transport_mode != cond["transport_mode"]:
        return False
    if cond.get("requires_agreement") and not ctx.has_agreement:
        return False
    return True


async def generate_checklist(
    session: AsyncSession, case: CustomsCase, ctx: CaseContext
) -> list[ChecklistItem]:
    reqs = list(await session.scalars(select(Requirement).where(Requirement.status == "ACTIVE")))
    items: list[ChecklistItem] = []
    for req in reqs:
        if not requirement_applies(req, ctx):
            continue
        item = ChecklistItem(
            customs_case_id=case.id,
            requirement_id=req.id,
            doc_type=req.doc_type,
            category=req.category,
            blocking=req.blocking,
            status="MISSING",
        )
        session.add(item)
        items.append(item)
    return items


async def recompute_readiness(session: AsyncSession, case: CustomsCase) -> Decimal:
    items = list(
        await session.scalars(
            select(ChecklistItem).where(ChecklistItem.customs_case_id == case.id)
        )
    )
    applicable = [i for i in items if i.status != "NOT_APPLICABLE"]
    if not applicable:
        score = Decimal(0)
    else:
        complete = sum(1 for i in applicable if i.status == "COMPLETE")
        score = (Decimal(complete) / Decimal(len(applicable)) * 100).quantize(Decimal("0.01"))

    case.customs_readiness_score = score

    # Estado y bloqueos según documentos que faltan (solo los bloqueantes detienen)
    missing_blocking = [i for i in applicable if i.blocking and i.status != "COMPLETE"]
    if score >= 100:
        case.current_state = "READY_FOR_CUSTOMS"
        case.next_expected_event = "CLASSIFICATION_APPROVAL_OR_DAI_DRAFT"
        case.blocker = None
    else:
        case.current_state = "AWAITING_DOCUMENTS"
        case.next_expected_event = "DOCUMENT_RECEIVED"
        case.blocker = (
            "Faltan documentos: " + ", ".join(i.doc_type for i in missing_blocking)
            if missing_blocking
            else None
        )
    return score
