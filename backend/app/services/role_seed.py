"""Privilegios por rol base (espejo del RBAC en código). Punto de partida editable."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_privilege import RolePrivilege

# (role, is_staff, can_write, can_admin, can_sign, can_audit, descripción)
DEFAULTS = [
    ("SUPER_ADMIN", True, True, True, True, True, "Super administrador (poder total)"),
    ("OPERATIONS_MANAGER", True, True, True, False, True, "Jefe de operaciones"),
    ("CUSTOMS_AGENT", True, True, False, True, False, "Agente afianzado (firma DAI)"),
    ("CUSTOMS_ASSISTANT", True, True, False, False, False, "Asistente de aduanas"),
    ("OCEAN_OPERATOR", True, True, False, False, False, "Operador marítimo"),
    ("AIR_OPERATOR", True, True, False, False, False, "Operador aéreo"),
    ("DOCUMENT_SPECIALIST", True, True, False, False, False, "Especialista documental"),
    ("SALES", True, True, False, False, False, "Ventas"),
    ("FINANCE", True, True, False, False, False, "Finanzas"),
    ("API_SERVICE", True, True, False, False, False, "Cuenta de servicio (API)"),
    ("AUDITOR", True, False, False, False, True, "Auditor (solo lectura + auditoría)"),
    ("CUSTOMER", False, False, False, False, False, "Cliente (solo portal)"),
]


async def seed_role_privileges(session: AsyncSession) -> list[str]:
    created: list[str] = []
    for name, staff, write, admin, sign, audit, desc in DEFAULTS:
        exists = await session.scalar(
            select(RolePrivilege).where(RolePrivilege.role_name == name)
        )
        if exists:
            continue
        session.add(RolePrivilege(
            role_name=name, description=desc, is_staff=staff, can_write=write,
            can_admin=admin, can_sign=sign, can_audit=audit,
        ))
        created.append(name)
    await session.flush()
    return created
