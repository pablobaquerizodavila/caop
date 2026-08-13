"""Auditoría automática por eventos de SQLAlchemy.

Registra INSERT/UPDATE/DELETE de las entidades auditables en `audit_event`,
salvo la propia tabla de auditoría (que es inmutable y no se audita a sí misma).

Nota S0: sienta la base del rastro de auditoría. El enriquecimiento con
user_id/role/ip desde el request se conectará en S1 vía contextvars.
"""

from __future__ import annotations

import uuid

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.core.correlation import get_correlation_id
from app.models.audit import AuditEvent

_EXCLUDED_TABLES = {"audit_event"}


def _serialize(obj) -> dict:
    data = {}
    for attr in inspect(obj).mapper.column_attrs:
        value = getattr(obj, attr.key)
        data[attr.key] = str(value) if isinstance(value, uuid.UUID) else value
    return data


def _entity_id(obj) -> str | None:
    pk = getattr(obj, "id", None)
    return str(pk) if pk is not None else None


def _record(session: Session, obj, action: str) -> None:
    if obj.__tablename__ in _EXCLUDED_TABLES:
        return
    session.add(
        AuditEvent(
            action=action,
            entity=obj.__tablename__,
            entity_id=_entity_id(obj),
            new_value=_serialize(obj) if action != "DELETE" else None,
            old_value=_serialize(obj) if action == "DELETE" else None,
            correlation_id=get_correlation_id(),
        )
    )


def register_audit_listeners() -> None:
    @event.listens_for(Session, "before_flush")
    def _before_flush(session: Session, flush_context, instances):  # noqa: ARG001
        for obj in session.new:
            if not isinstance(obj, AuditEvent):
                _record(session, obj, "CREATE")
        for obj in session.dirty:
            if session.is_modified(obj) and not isinstance(obj, AuditEvent):
                _record(session, obj, "UPDATE")
        for obj in session.deleted:
            if not isinstance(obj, AuditEvent):
                _record(session, obj, "DELETE")
