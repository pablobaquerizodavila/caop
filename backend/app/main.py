"""Punto de entrada de la aplicación FastAPI."""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router
from app.audit.listener import register_audit_listeners
from app.core.config import settings
from app.core.correlation import CorrelationIdMiddleware
from app.core.logging import configure_logging
from app.services.dai_service import DAIError
from app.services.scheduler import sla_scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    register_audit_listeners()

    task: asyncio.Task | None = None
    if settings.sla_evaluate_interval_minutes > 0:
        task = asyncio.create_task(sla_scheduler_loop(settings.sla_evaluate_interval_minutes))

    yield

    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    app = FastAPI(
        title="CAOP API",
        version=__version__,
        description="Customs Autonomous Operations Platform — API",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(DAIError)
    async def _dai_error(request: Request, exc: DAIError):  # noqa: ARG001
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return app


app = create_app()
