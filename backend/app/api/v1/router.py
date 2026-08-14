"""Router raíz de la API v1."""

from fastapi import APIRouter, Depends

from app.api import health
from app.api.v1 import (
    alerts,
    analytics,
    cases,
    customers,
    dai,
    documents,
    notifications,
    ocean,
    quotes,
    settlements,
    sla,
    suppliers,
    tax,
    tracking,
    vue,
    warehouse,
)
from app.core.security import Principal, get_current_principal, require_write

api_router = APIRouter()

# Salud: abierto (sin auth).
api_router.include_router(health.router)

# Track & Trace público: enlace con token, SIN auth (lo abre el cliente importador).
api_router.include_router(tracking.public_router)

# Resto de la API: token Keycloak + RBAC (escritura exige rol de escritura).
protected = [Depends(get_current_principal), Depends(require_write)]
api_router.include_router(customers.router, dependencies=protected)
api_router.include_router(suppliers.router, dependencies=protected)
api_router.include_router(documents.router, dependencies=protected)
api_router.include_router(tax.router, dependencies=protected)
api_router.include_router(quotes.router, dependencies=protected)
api_router.include_router(cases.router, dependencies=protected)
api_router.include_router(dai.router, dependencies=protected)
api_router.include_router(notifications.router, dependencies=protected)
api_router.include_router(sla.router, dependencies=protected)
api_router.include_router(analytics.router, dependencies=protected)
api_router.include_router(ocean.router, dependencies=protected)
api_router.include_router(tracking.admin_router, dependencies=protected)
api_router.include_router(vue.router, dependencies=protected)
api_router.include_router(warehouse.router, dependencies=protected)
api_router.include_router(settlements.router, dependencies=protected)
api_router.include_router(alerts.router, dependencies=protected)


@api_router.get("/me", tags=["identity"])
async def me(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Devuelve la identidad autenticada (token Keycloak válido requerido)."""
    return principal
