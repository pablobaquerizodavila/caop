"""Servicio de almacenamiento de objetos (MinIO/S3) con abstracción para tests."""

from __future__ import annotations

import hashlib
import io
from typing import Protocol

from minio import Minio

from app.core.config import settings


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StorageService(Protocol):
    def ensure_bucket(self) -> None: ...
    def put_object(self, key: str, data: bytes, content_type: str | None) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...
    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str: ...


class MinioStorage:
    """Implementación real sobre MinIO. Las llamadas son bloqueantes: los
    endpoints las ejecutan en un threadpool (fastapi.concurrency.run_in_threadpool)."""

    def __init__(self) -> None:
        creds = dict(
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        # Cliente interno: operaciones put/get (contenedor -> contenedor).
        self._client = Minio(self._host(settings.minio_endpoint), **creds)
        # Cliente público: SOLO para firmar URLs alcanzables por el navegador.
        # presigned_get_object no hace peticiones de red; firma localmente para ese host.
        self._public_client = Minio(self._host(settings.minio_public_endpoint), **creds)
        self._bucket = settings.minio_bucket

    @staticmethod
    def _host(url: str) -> str:
        return url.replace("http://", "").replace("https://", "")

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_object(self, key: str, data: bytes, content_type: str | None) -> None:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )

    def get_bytes(self, key: str) -> bytes:
        resp = self._client.get_object(self._bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta

        return self._public_client.presigned_get_object(
            self._bucket, key, expires=timedelta(seconds=expires_seconds)
        )


_storage: MinioStorage | None = None


def get_storage() -> StorageService:
    """Dependencia FastAPI. Se sobreescribe en tests por un fake en memoria."""
    global _storage
    if _storage is None:
        _storage = MinioStorage()
    return _storage
