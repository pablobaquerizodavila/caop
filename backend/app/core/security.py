"""Validación de tokens JWT emitidos por Keycloak (OIDC).

Verifica firma (RS256), issuer y expiración contra el JWKS de Keycloak. La
audiencia se valida de forma flexible (azp/aud dentro de una lista permitida),
porque los tokens emitidos al cliente del frontend no llevan aud=caop-backend.
El JWKS se descarga por la red interna (keycloak:8080); el issuer se compara
contra la URL pública que aparece en el token.
"""

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=True)

# --- Matriz de roles (alineada con el realm de Keycloak) ---
# Roles del personal que pueden ejecutar operaciones de escritura.
WRITER_ROLES = {
    "SUPER_ADMIN", "OPERATIONS_MANAGER", "CUSTOMS_AGENT", "CUSTOMS_ASSISTANT",
    "OCEAN_OPERATOR", "AIR_OPERATOR", "DOCUMENT_SPECIALIST", "SALES", "FINANCE", "API_SERVICE",
}
# Configuración global (reglas HS→VUE, tarifarios): solo administración.
ADMIN_ROLES = ("SUPER_ADMIN", "OPERATIONS_MANAGER")
# Firma de la DAI (nunca autónoma): agente afianzado.
SIGN_ROLES = ("CUSTOMS_AGENT", "SUPER_ADMIN")
# Personal interno: puede acceder a la API operativa (lectura y, según rol, escritura).
# El rol CUSTOMER queda FUERA: sólo accede al portal del cliente (/portal), con sus datos.
STAFF_ROLES = WRITER_ROLES | {"AUDITOR"}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Capacidades del sistema.
ALL_CAPS = {"staff", "write", "admin", "sign", "audit"}
_AUDIT_ROLES = {"SUPER_ADMIN", "OPERATIONS_MANAGER", "AUDITOR"}


def _fallback_caps(role: str) -> set[str]:
    """Capacidades por defecto (en código) cuando el rol no tiene fila editable."""
    caps: set[str] = set()
    if role in STAFF_ROLES:
        caps.add("staff")
    if role in WRITER_ROLES:
        caps.add("write")
    if role in ADMIN_ROLES:
        caps.add("admin")
    if role in SIGN_ROLES:
        caps.add("sign")
    if role in _AUDIT_ROLES:
        caps.add("audit")
    return caps


async def capabilities_for(session: AsyncSession, roles: list[str]) -> set[str]:
    """Capacidades efectivas de un conjunto de roles.

    SUPER_ADMIN siempre tiene poder total. Para el resto: si el rol tiene fila en
    role_privilege se usa esa configuración editable; si no, el fallback en código.
    """
    if "SUPER_ADMIN" in roles:
        return set(ALL_CAPS)
    from app.models.role_privilege import RolePrivilege  # import local: evita ciclos

    rows = await session.scalars(
        select(RolePrivilege).where(RolePrivilege.role_name.in_(list(roles) or [""]))
    )
    by_name = {r.role_name: r for r in rows}
    caps: set[str] = set()
    for role in roles:
        r = by_name.get(role)
        if r is not None:
            if r.is_staff:
                caps.add("staff")
            if r.can_write:
                caps.add("write")
            if r.can_admin:
                caps.add("admin")
            if r.can_sign:
                caps.add("sign")
            if r.can_audit:
                caps.add("audit")
        else:
            caps |= _fallback_caps(role)
    return caps


class Principal(BaseModel):
    """Identidad autenticada extraída del token."""

    subject: str
    username: str | None = None
    email: str | None = None
    roles: list[str] = []


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(settings.keycloak_jwks_url)


def _decode(token: str) -> dict:
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=settings.keycloak_issuer,
        options={"require": ["exp", "iss", "sub"], "verify_aud": False},
    )
    # Validación flexible de audiencia/azp.
    allowed = set(settings.allowed_audiences_list)
    aud = claims.get("aud", [])
    aud_set = {aud} if isinstance(aud, str) else set(aud or [])
    azp = claims.get("azp")
    if allowed and not (aud_set & allowed) and azp not in allowed:
        raise jwt.InvalidAudienceError("Audiencia no permitida")
    return claims


async def get_current_principal(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Principal:
    try:
        claims = _decode(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    roles = claims.get("realm_access", {}).get("roles", [])
    return Principal(
        subject=claims["sub"],
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        roles=roles,
    )


def require_roles(*required: str):
    """Dependencia que exige al menos uno de los roles indicados."""

    async def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if required and not set(required) & set(principal.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere uno de los roles: {', '.join(required)}",
            )
        return principal

    return _checker


async def rbac_guard(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    """RBAC transversal de la API operativa: exige rol de personal ('staff') y,
    en métodos de escritura, la capacidad 'write'. Las capacidades son editables
    (tabla role_privilege) con fallback en código y SUPER_ADMIN con poder total."""
    caps = await capabilities_for(session, principal.roles)
    if "staff" not in caps:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido al personal. Use el portal del cliente.",
        )
    if request.method in WRITE_METHODS and "write" not in caps:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere un rol con permisos de escritura para esta acción.",
        )
    return principal


def require_capability(cap: str, detail: str):
    """Dependencia que exige una capacidad específica (admin/sign/audit)."""

    async def _checker(
        principal: Principal = Depends(get_current_principal),
        session: AsyncSession = Depends(get_session),
    ) -> Principal:
        caps = await capabilities_for(session, principal.roles)
        if cap not in caps:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        return principal

    return _checker


require_admin = require_capability("admin", "Requiere rol de administración.")
require_sign = require_capability("sign", "La firma de la DAI requiere rol de agente afianzado.")
require_audit = require_capability("audit", "Requiere rol de auditoría.")


async def require_super_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Solo el super administrador (gestión de usuarios y privilegios)."""
    if "SUPER_ADMIN" not in principal.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el super administrador puede gestionar usuarios y privilegios.",
        )
    return principal
