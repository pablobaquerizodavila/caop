"""Router raíz de la API v1."""

from fastapi import APIRouter, Depends

from app.api import health
from app.api.v1 import cases, customers, documents, quotes, suppliers, tax
from app.core.security import Principal, get_current_principal

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(customers.router)
api_router.include_router(suppliers.router)
api_router.include_router(documents.router)
api_router.include_router(tax.router)
api_router.include_router(quotes.router)
api_router.include_router(cases.router)


@api_router.get("/me", tags=["identity"])
async def me(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Devuelve la identidad autenticada (token Keycloak válido requerido)."""
    return principal
