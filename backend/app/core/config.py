"""Configuración central, cargada desde variables de entorno (.env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"

    # Scheduler interno: cada cuántos minutos evaluar SLA (0 = desactivado)
    sla_evaluate_interval_minutes: int = 10

    # OCR (Tesseract). Si el binario/librerías no están, degrada sin fallar.
    ocr_enabled: bool = True
    ocr_languages: str = "spa+eng"

    # SRI — facturación electrónica (datos del emisor). PLACEHOLDERS: reemplazar por
    # los datos reales de la empresa. ambiente: 1=pruebas, 2=producción.
    sri_ambiente: str = "1"
    sri_ruc: str = "9999999999001"
    sri_razon_social: str = "CAOP AGENCIA DE ADUANAS S.A."
    sri_nombre_comercial: str = "CAOP"
    sri_dir_matriz: str = "S/N"
    sri_dir_establecimiento: str = "S/N"
    sri_obligado_contabilidad: str = "SI"
    sri_estab: str = "001"
    sri_pto_emi: str = "001"

    # Alertas proactivas: digest de excepciones por email.
    # Destinatarios separados por coma; intervalo en minutos (0 = desactivado, 1440 = diario).
    alerts_recipients: str = ""
    alerts_digest_interval_minutes: int = 0

    @property
    def alerts_recipients_list(self) -> list[str]:
        return [e.strip() for e in self.alerts_recipients.split(",") if e.strip()]

    # Base de datos
    database_url: str = Field(
        default="postgresql+asyncpg://caop:caop_dev_password@postgres:5432/caop"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://caop:caop_dev_password@postgres:5432/caop"
    )

    # CORS (lista separada por comas)
    backend_cors_origins: str = "http://localhost:3000"

    # URL pública del frontend (para construir enlaces compartibles, p. ej. Track & Trace).
    public_app_url: str = "http://192.168.0.7:3000"

    # Keycloak / OIDC
    # issuer: el que aparece en el token (URL pública, vista por el navegador).
    keycloak_issuer: str = "http://localhost:8080/realms/caop"
    # jwks: URL desde donde el backend descarga las llaves (red interna del contenedor).
    keycloak_jwks_url: str = "http://keycloak:8080/realms/caop/protocol/openid-connect/certs"
    keycloak_audience: str = "caop-backend"
    # Audiencias/azp aceptadas (el token del frontend no lleva aud=caop-backend por defecto).
    keycloak_allowed_audiences: str = "caop-backend,caop-frontend,account"

    @property
    def allowed_audiences_list(self) -> list[str]:
        return [a.strip() for a in self.keycloak_allowed_audiences.split(",") if a.strip()]

    # Email (mailpit en dev, mailcow en prod)
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@caop.local"
    smtp_use_tls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None

    # WhatsApp Business Platform (oficial). Sin token -> modo simulado.
    whatsapp_enabled: bool = False
    whatsapp_api_url: str = "https://graph.facebook.com/v21.0"
    whatsapp_phone_id: str | None = None
    whatsapp_token: str | None = None

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
    # Fijar la región evita que minio-py haga GetBucketLocation por red al firmar.
    minio_region: str = "us-east-1"

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
