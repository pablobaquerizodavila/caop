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
