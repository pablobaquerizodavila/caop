"""Fixtures de test. Usa SQLite async en memoria y un almacenamiento falso."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.audit.listener import register_audit_listeners
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.services.storage import get_storage

# Registrar la auditoría también en tests (bajo ASGITransport no corre el lifespan),
# para ejercitar la serialización de auditoría contra SQLite y detectar regresiones.
register_audit_listeners()


class FakeStorage:
    """StorageService en memoria para tests (sin MinIO)."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.bucket_ready = False

    def ensure_bucket(self) -> None:
        self.bucket_ready = True

    def put_object(self, key: str, data: bytes, content_type: str | None) -> None:
        self.objects[key] = data

    def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        return f"https://fake-storage.local/{key}?exp={expires_seconds}"


@pytest_asyncio.fixture
async def db_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest_asyncio.fixture
async def client(db_sessionmaker, storage) -> AsyncClient:
    async def _override_get_session():
        async with db_sessionmaker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_storage] = lambda: storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
