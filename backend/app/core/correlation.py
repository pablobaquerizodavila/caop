"""Middleware de correlation_id para trazabilidad extremo a extremo."""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Correlation-ID"

# Disponible para logging y para el listener de auditoría.
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
        token = correlation_id_ctx.set(cid)
        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)
        response.headers[HEADER_NAME] = cid
        return response
