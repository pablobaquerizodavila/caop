"""Punto de entrada de la aplicación FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.audit.listener import register_audit_listeners
from app.core.config import settings
from app.core.correlation import CorrelationIdMiddleware
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    register_audit_listeners()
    yield


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
    return app


app = create_app()
