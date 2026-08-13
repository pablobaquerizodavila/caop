"""Configuración central, cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"

    # Base de datos
    database_url: str = Field(
        default="postgresql+asyncpg://caop:caop_dev_password@postgres:5432/caop"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://caop:caop_dev_password@postgres:5432/caop"
    )

    # CORS (lista separada por comas)
    backend_cors_origins: str = "http://localhost:3000"

    # Keycloak / OIDC
    keycloak_issuer: str = "http://localhost:8080/realms/caop"
    keycloak_audience: str = "caop-backend"

    # Infra auxiliar
    redis_url: str = "redis://redis:6379/0"
    # Endpoint interno para operaciones (put/get) contenedor->contenedor.
    minio_endpoint: str = "http://minio:9000"
    # Endpoint público usado SOLO para firmar URLs (debe ser alcanzable por el navegador).
    minio_public_endpoint: str = "http://192.168.0.7:9000"
    minio_bucket: str = "caop-documents"
    minio_access_key: str = "caop_minio"
    minio_secret_key: str = "caop_minio_dev_password"
    minio_secure: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
