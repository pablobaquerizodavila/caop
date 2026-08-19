"""Alertas proactivas: recopila las excepciones de la operación y arma/envía un digest.

Excepciones consideradas: demurrage, almacenaje, SLA y control previo (VUE) en riesgo.
El envío reutiliza el motor de notificaciones (plantilla ALERT_DIGEST).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.document import Document, DocumentVersion
from app.models.shipment import Container, CustomsCase, Shipment
from app.models.sla import SLAInstance
from app.models.vue import VuePermit
from app.models.warehouse import WarehouseStorage
from app.services.demurrage import compute as compute_demurrage
from app.services.notifications import dispatch
from app.services.payments_service import receivables as compute_receivables
from app.services.warehouse import compute as compute_storage

SLA_RISKY = ("AT_RISK", "CRITICAL", "BREACHED")


async def expiring_documents(session: AsyncSession, within_days: int = 30) -> list[dict]:
    """Documentos de clientes vencidos o por vencer (última versión) dentro de la
    ventana. Usa la versión más reciente de cada documento con fecha de vencimiento."""
    today = date.today()
    horizon = today + timedelta(days=within_days)
    latest = (
        select(
            DocumentVersion.document_id.label("doc_id"),
            func.max(DocumentVersion.version).label("mv"),
        )
        .group_by(DocumentVersion.document_id)
        .subquery()
    )
    stmt = (
        select(DocumentVersion, Document.doc_type, Customer.id, Customer.legal_name)
        .join(
            latest,
            (DocumentVersion.document_id == latest.c.doc_id)
            & (DocumentVersion.version == latest.c.mv),
        )
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(Customer, Customer.id == Document.customer_id)
        .where(
            DocumentVersion.expiry_date.is_not(None),
            DocumentVersion.expiry_date <= horizon,
        )
        .order_by(DocumentVersion.expiry_date)
    )
    out: list[dict] = []
    for dv, doc_type, cid, cname in (await session.execute(stmt)).all():
        days = (dv.expiry_date - today).days
        out.append({
            "customer_id": str(cid),
            "customer_name": cname,
            "doc_type": doc_type,
            "expiry_date": dv.expiry_date.isoformat(),
            "days_left": days,
            "status": "EXPIRED" if days < 0 else "SOON",
        })
    return out


async def gather_exceptions(session: AsyncSession) -> dict:
    today = date.today()

    # Demurrage en riesgo
    demurrage: list[dict] = []
    rows = await session.execute(
        select(Container, CustomsCase.case_number)
        .join(Shipment, Container.shipment_id == Shipment.id)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
    )
    for cont, case_number in rows.all():
        d = compute_demurrage(cont, today)
        if d.at_risk and cont.status != "EMPTY_RETURNED":
            demurrage.append({
                "case_number": case_number, "ref": cont.container_number,
                "alarm": d.alarm, "days_to": d.days_to_last_free_day,
                "amount": float(d.estimated_demurrage),
            })

    # Almacenaje en riesgo
    storage: list[dict] = []
    rows = await session.execute(
        select(WarehouseStorage, CustomsCase.case_number)
        .join(Shipment, WarehouseStorage.shipment_id == Shipment.id)
        .join(CustomsCase, CustomsCase.shipment_id == Shipment.id)
    )
    for st, case_number in rows.all():
        d = compute_storage(st, today)
        if d.at_risk and st.status != "WITHDRAWN":
            storage.append({
                "case_number": case_number, "ref": st.reference or st.warehouse_name or "-",
                "alarm": d.alarm, "days_to": d.days_to_last_free_day,
                "amount": float(d.estimated_storage),
            })

    # SLA en riesgo
    sla: list[dict] = []
    rows = await session.execute(
        select(SLAInstance, CustomsCase.case_number)
        .join(
            CustomsCase,
            (CustomsCase.id == SLAInstance.entity_id)
            & (SLAInstance.entity_type == "CUSTOMS_CASE"),
            isouter=True,
        )
        .where(SLAInstance.status.in_(SLA_RISKY))
    )
    for inst, case_number in rows.all():
        sla.append({
            "case_number": case_number or "-", "milestone": inst.milestone,
            "status": inst.status, "escalation": inst.escalation_level,
        })

    # Control previo (VUE) bloqueante pendiente
    vue: list[dict] = []
    rows = await session.execute(
        select(VuePermit, CustomsCase.case_number)
        .join(CustomsCase, CustomsCase.id == VuePermit.customs_case_id)
        .where(VuePermit.blocking.is_(True))
    )
    for permit, case_number in rows.all():
        if not permit.is_satisfied(today):
            vue.append({
                "case_number": case_number, "entity": permit.entity,
                "document_code": permit.document_code, "status": permit.status,
            })

    # Cuentas por cobrar vencidas
    rec = await compute_receivables(session)
    overdue = [r for r in rec["items"] if r["days_overdue"] > 0]

    # Documentos de clientes vencidos o por vencer (≤30 días)
    documents = await expiring_documents(session, within_days=30)

    total = len(demurrage) + len(storage) + len(sla) + len(vue) + len(overdue) + len(documents)
    return {
        "demurrage": demurrage, "storage": storage, "sla": sla, "vue": vue,
        "receivables": overdue, "documents": documents,
        "counts": {
            "demurrage": len(demurrage), "storage": len(storage),
            "sla": len(sla), "vue": len(vue), "receivables": len(overdue),
            "documents": len(documents),
        },
        "total": total,
    }


def build_digest_text(ex: dict) -> str:
    lines: list[str] = []
    lines.append("Resumen de excepciones operativas de CAOP.\n")
    c = ex["counts"]
    lines.append(
        f"Totales — Demurrage: {c['demurrage']} · Almacenaje: {c['storage']} · "
        f"SLA: {c['sla']} · Control previo (VUE): {c['vue']} · "
        f"Cobranza vencida: {c.get('receivables', 0)} · "
        f"Documentos por vencer: {c.get('documents', 0)}\n"
    )

    if ex.get("documents"):
        lines.append("DOCUMENTOS DE CLIENTES VENCIDOS / POR VENCER:")
        for x in ex["documents"]:
            estado = "VENCIDO" if x["status"] == "EXPIRED" else f"vence en {x['days_left']}d"
            lines.append(
                f"  - {x['customer_name']} · {x['doc_type']} · {x['expiry_date']} · {estado}"
            )
        lines.append("")

    if ex["demurrage"]:
        lines.append("DEMURRAGE EN RIESGO:")
        for x in ex["demurrage"]:
            lines.append(
                f"  - {x['case_number']} · {x['ref']} · {x['alarm']} · "
                f"días a último libre: {x['days_to']} · est. USD {x['amount']:,.2f}"
            )
        lines.append("")

    if ex["storage"]:
        lines.append("ALMACENAJE EN RIESGO:")
        for x in ex["storage"]:
            lines.append(
                f"  - {x['case_number']} · {x['ref']} · {x['alarm']} · "
                f"días a último libre: {x['days_to']} · est. USD {x['amount']:,.2f}"
            )
        lines.append("")

    if ex["sla"]:
        lines.append("SLA EN RIESGO:")
        for x in ex["sla"]:
            lines.append(
                f"  - {x['case_number']} · {x['milestone']} · {x['status']} · "
                f"escalación {x['escalation']}"
            )
        lines.append("")

    if ex["vue"]:
        lines.append("CONTROL PREVIO (VUE) PENDIENTE:")
        for x in ex["vue"]:
            lines.append(
                f"  - {x['case_number']} · {x['entity']}/{x['document_code']} · {x['status']}"
            )
        lines.append("")

    if ex.get("receivables"):
        lines.append("COBRANZA VENCIDA:")
        for x in ex["receivables"]:
            lines.append(
                f"  - {x['settlement_number']} · {x['customer']} · saldo "
                f"{x['currency']} {x['balance']:,.2f} · {x['days_overdue']} días ({x['bucket']})"
            )
        lines.append("")

    if ex["total"] == 0:
        lines.append("Sin excepciones. La operación está al día.")

    return "\n".join(lines)


async def send_digest(
    session: AsyncSession, recipients: list[str] | None = None, skip_if_empty: bool = False
) -> dict:
    ex = await gather_exceptions(session)
    to_list = recipients if recipients is not None else settings.alerts_recipients_list

    if skip_if_empty and ex["total"] == 0:
        return {"total": 0, "skipped": True, "sent": []}
    if not to_list:
        return {"total": ex["total"], "skipped": False, "sent": [],
                "note": "Sin destinatarios configurados (ALERTS_RECIPIENTS)."}

    body = build_digest_text(ex)
    sent: list[dict] = []
    for to in to_list:
        notif = await dispatch(
            session, channel="EMAIL", template_code="ALERT_DIGEST", to=to,
            context={"count": ex["total"], "body": body},
        )
        sent.append({"to": to, "status": notif.status, "error": notif.error})
    return {"total": ex["total"], "skipped": False, "sent": sent}
