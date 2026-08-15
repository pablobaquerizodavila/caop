"""Plantillas de notificación base (versionadas)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationTemplate

DEFAULTS: list[dict] = [
    {
        "code": "DOCUMENT_REQUIRED",
        "version": 1,
        "channel": "EMAIL",
        "subject_template": "Documentos requeridos — expediente {{case_number}}",
        "body_template": (
            "Estimado/a {{customer_name}}:\n\n"
            "Para continuar con su importación (expediente {{case_number}}) necesitamos los "
            "siguientes documentos:\n{{missing_docs}}\n\n"
            "Puede cargarlos respondiendo a este correo o desde el portal.\n\n"
            "Gracias,\nCAOP"
        ),
    },
    {
        "code": "DOCUMENT_REQUIRED",
        "version": 1,
        "channel": "WHATSAPP",
        "subject_template": None,
        "body_template": (
            "Hola {{customer_name}}, para su importación {{case_number}} nos faltan: "
            "{{missing_docs}}. Puede enviarlos por aquí. — CAOP"
        ),
    },
    {
        "code": "PAYMENT_REMINDER",
        "version": 1,
        "channel": "EMAIL",
        "subject_template": "Recordatorio de pago — liquidación {{settlement_number}}",
        "body_template": (
            "Estimado/a {{customer_name}}:\n\n"
            "Le recordamos que la liquidación {{settlement_number}} tiene un saldo pendiente "
            "de {{currency}} {{balance}} con vencimiento {{due_date}} ({{days_overdue}} días).\n\n"
            "Agradecemos su pronta gestión. Si ya realizó el pago, por favor ignore este mensaje.\n\n"
            "Saludos,\nCAOP"
        ),
    },
    {
        "code": "PAYMENT_REMINDER",
        "version": 1,
        "channel": "WHATSAPP",
        "subject_template": None,
        "body_template": (
            "Hola {{customer_name}}, la liquidación {{settlement_number}} tiene saldo pendiente "
            "de {{currency}} {{balance}} (vence {{due_date}}). Gracias por su gestión. — CAOP"
        ),
    },
    {
        "code": "ALERT_DIGEST",
        "version": 1,
        "channel": "EMAIL",
        "subject_template": "CAOP — Alertas operativas ({{count}})",
        "body_template": "{{body}}",
    },
    {
        "code": "TRACKING_LINK",
        "version": 1,
        "channel": "EMAIL",
        "subject_template": "Seguimiento de su importación — expediente {{case_number}}",
        "body_template": (
            "Estimado/a {{customer_name}}:\n\n"
            "Puede seguir el avance de su importación (expediente {{case_number}}) en "
            "tiempo real desde el siguiente enlace:\n{{tracking_url}}\n\n"
            "El enlace muestra el estado del trámite, el transporte y las fechas clave.\n\n"
            "Saludos,\nCAOP"
        ),
    },
    {
        "code": "TRACKING_LINK",
        "version": 1,
        "channel": "WHATSAPP",
        "subject_template": None,
        "body_template": (
            "Hola {{customer_name}}, siga su importación {{case_number}} en tiempo real aquí: "
            "{{tracking_url}} — CAOP"
        ),
    },
    {
        "code": "QUOTATION_SENT",
        "version": 1,
        "channel": "EMAIL",
        "subject_template": "Cotización {{quote_number}} — costo estimado de importación",
        "body_template": (
            "Estimado/a {{customer_name}}:\n\n"
            "Adjuntamos su cotización {{quote_number}}.\n"
            "Costo total estimado de importación (landed): {{currency}} {{landed_cost_total}}.\n"
            "Válida hasta: {{valid_until}}.\n\n"
            "Quedamos atentos.\nCAOP"
        ),
    },
]


async def seed_notification_templates(session: AsyncSession) -> list[str]:
    created: list[str] = []
    for spec in DEFAULTS:
        exists = await session.scalar(
            select(NotificationTemplate).where(
                NotificationTemplate.code == spec["code"],
                NotificationTemplate.channel == spec["channel"],
                NotificationTemplate.version == spec["version"],
            )
        )
        if exists:
            continue
        session.add(NotificationTemplate(active=True, **spec))
        created.append(f"{spec['code']}/{spec['channel']}")
    await session.flush()
    return created
