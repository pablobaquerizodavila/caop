"""Validación de tokens JWT emitidos por Keycloak (OIDC).

Verifica firma (RS256), issuer y expiración contra el JWKS de Keycloak. La
audiencia se valida de forma flexible (azp/aud dentro de una lista permitida),
porque los tokens emitidos al cliente del frontend no llevan aud=caop-backend.
El JWKS se descarga por la red interna (keycloak:8080); el issuer se compara
contra la URL pública que aparece en el token.
"""

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)


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
