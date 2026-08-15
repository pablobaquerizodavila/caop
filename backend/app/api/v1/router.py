"""Router raíz de la API v1."""

from fastapi import APIRouter, Depends

from app.api import health
from app.api.v1 import (
    admin,
    alerts,
    analytics,
    audit,
    cases,
    customers,
    dai,
    einvoice,
    exports,
    documents,
    notifications,
    ocean,
    portal,
    quotes,
    retention,
    search,
    settlements,
    sla,
    suppliers,
    tax,
    tracking,
    vue,
    warehouse,
    waybill,
)
from app.core.security import (
    Principal,
    get_current_principal,
    rbac_guard,
    require_super_admin,
)

api_router = APIRouter()

# Salud: abierto (sin auth).
api_router.include_router(health.router)

# Track & Trace público: enlace con token, SIN auth (lo abre el cliente importador).
api_router.include_router(tracking.public_router)

# Portal del cliente: autenticado pero SIN require_staff; cada endpoint filtra por
# el cliente vinculado a la identidad (no expone datos de otros).
api_router.include_router(portal.router, dependencies=[Depends(get_current_principal)])

# Resto de la API: token Keycloak + RBAC transversal (personal + escritura),
# con capacidades editables desde role_privilege.
protected = [Depends(get_current_principal), Depends(rbac_guard)]
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
api_router.include_router(exports.router, dependencies=protected)
api_router.include_router(search.router, dependencies=protected)
api_router.include_router(ocean.router, dependencies=protected)
api_router.include_router(tracking.admin_router, dependencies=protected)
api_router.include_router(vue.router, dependencies=protected)
api_router.include_router(warehouse.router, dependencies=protected)
api_router.include_router(settlements.router, dependencies=protected)
api_router.include_router(einvoice.router, dependencies=protected)
api_router.include_router(retention.router, dependencies=protected)
api_router.include_router(waybill.router, dependencies=protected)
api_router.include_router(alerts.router, dependencies=protected)
api_router.include_router(audit.router, dependencies=protected)
# Administración: token + solo SUPER_ADMIN (gestión de usuarios y privilegios).
api_router.include_router(
    admin.router, dependencies=[Depends(get_current_principal), Depends(require_super_admin)]
)


@api_router.get("/me", tags=["identity"])
async def me(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Devuelve la identidad autenticada (token Keycloak válido requerido)."""
    return principal
