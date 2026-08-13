# CAOP — Customs Autonomous Operations Platform

Monorepo de la plataforma. **Sprint S0 — Fundaciones.**

Stack: **FastAPI** (backend) · **Next.js/TS** (frontend) · PostgreSQL · Redis · MinIO · Keycloak · Temporal · Mailpit (correo de desarrollo; en producción → mailcow).

> Decisiones: MVP = Cotización→Expediente · Backend FastAPI (ADR-001) · La empresa ya opera con ECUAPASS (integración oficial fuera del MVP).
> Regla de oro: no se inventan mecanismos/estados/tributos de SENAE/ECUAPASS/VUE/SRI.

## Estructura

```
caop/
├── backend/          # API FastAPI (Pydantic v2, SQLAlchemy 2 async, Alembic)
├── frontend/         # Next.js (App Router, TypeScript)
├── keycloak/         # Import de realm de desarrollo
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Requisitos

- Docker + Docker Compose v2
- (Opcional para desarrollo local del backend) Python 3.12+

## Puesta en marcha (desarrollo)

```bash
cp .env.example .env
docker compose up -d --build
```

Servicios expuestos:

| Servicio | URL |
|---|---|
| Backend API (OpenAPI) | http://localhost:8000/docs |
| Backend health | http://localhost:8000/api/v1/health |
| Frontend | http://localhost:3000 |
| Keycloak (admin) | http://localhost:8080 |
| Temporal UI | http://localhost:8081 |
| MinIO consola | http://localhost:9001 |
| Mailpit (correo dev) | http://localhost:8025 |

## Migraciones (Alembic)

```bash
make migrate            # aplica migraciones
make revision m="msg"   # crea una nueva revisión autogenerada
```

## Tests

```bash
make test
```

## Estado de S0

- [x] Estructura de monorepo
- [x] docker-compose con toda la infraestructura de desarrollo
- [x] Esqueleto FastAPI con OpenAPI, healthchecks y `correlation_id`
- [x] SQLAlchemy 2 async + Alembic + migración inicial (Organization, User, Role, AuditEvent)
- [x] Auditoría base (listener de cambios)
- [x] Validación de JWT contra Keycloak (endpoint protegido `/api/v1/me`)
- [x] Frontend Next.js mínimo
- [x] Suite de tests (health) como base de CI

Siguiente: **S1** — Clientes (KYC/LOPDP) + documentos (subida + versionado + SHA-256).
