"""Servicio de notificaciones: plantillas versionadas + envío por email/WhatsApp.

- Email: SMTP (mailpit en dev, mailcow en prod) vía aiosmtplib.
- WhatsApp: conector propio sobre la WhatsApp Business Platform oficial (Graph API).
  Sin token configurado, opera en modo SIMULADO (registra pero no envía) — no se
  inventan credenciales ni endpoints.

El notificador es un singleton sustituible en tests (set_notifier).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.correlation import get_correlation_id
from app.models.notification import Notification, NotificationTemplate

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, context: dict) -> str:
    return _PLACEHOLDER.sub(lambda m: str(context.get(m.group(1), "")), template or "")


@dataclass
class SendResult:
    status: str  # SENT / SIMULATED / FAILED
    error: str | None = None


class Notifier(Protocol):
    async def send(self, channel: str, to: str, subject: str | None, body: str) -> SendResult: ...


class RealNotifier:
    async def send(self, channel: str, to: str, subject: str | None, body: str) -> SendResult:
        try:
            if channel == "EMAIL":
                return await self._email(to, subject, body)
            if channel == "WHATSAPP":
                return await self._whatsapp(to, body)
            return SendResult("FAILED", f"Canal no soportado: {channel}")
        except Exception as exc:  # noqa: BLE001
            return SendResult("FAILED", str(exc))

    async def _email(self, to: str, subject: str | None, body: str) -> SendResult:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject or "(sin asunto)"
        msg.set_content(body)
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=settings.smtp_use_tls,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
        )
        return SendResult("SENT")

    async def _whatsapp(self, to: str, body: str) -> SendResult:
        if not (settings.whatsapp_enabled and settings.whatsapp_token and settings.whatsapp_phone_id):
            return SendResult("SIMULATED", "WhatsApp no configurado (token/phone_id ausentes)")
        url = f"{settings.whatsapp_api_url}/{settings.whatsapp_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url, json=payload,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            )
            if resp.status_code >= 400:
                return SendResult("FAILED", f"WhatsApp API {resp.status_code}: {resp.text[:200]}")
        return SendResult("SENT")


_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    global _notifier
    if _notifier is None:
        _notifier = RealNotifier()
    return _notifier


def set_notifier(n: Notifier) -> None:
    global _notifier
    _notifier = n


async def dispatch(
    session: AsyncSession,
    *,
    channel: str,
    template_code: str,
    to: str,
    context: dict,
    customer_id=None,
    customs_case_id=None,
) -> Notification:
    """Renderiza la plantilla activa, registra y envía la notificación."""
    tpl = await session.scalar(
        select(NotificationTemplate)
        .where(
            NotificationTemplate.code == template_code,
            NotificationTemplate.channel == channel,
            NotificationTemplate.active.is_(True),
        )
        .order_by(NotificationTemplate.version.desc())
    )
    subject = render(tpl.subject_template, context) if tpl else None
    body = render(tpl.body_template, context) if tpl else context.get("body", "")

    notif = Notification(
        customer_id=customer_id,
        customs_case_id=customs_case_id,
        channel=channel,
        template_code=template_code,
        template_version=tpl.version if tpl else None,
        to_address=to,
        subject=subject,
        body=body,
        status="QUEUED",
        payload=context,
        correlation_id=get_correlation_id(),
    )
    session.add(notif)
    await session.flush()

    result = await get_notifier().send(channel, to, subject, body)
    notif.status = result.status
    notif.error = result.error
    await session.flush()
    return notif
