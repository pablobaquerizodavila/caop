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

## Estado de S1 — Clientes (KYC/LOPDP) + Documentos

- [x] Modelos: Customer, Contact, ConsentRecord (LOPDP), Supplier, Document, DocumentVersion, DocumentExtraction
- [x] Migración Alembic `0002`
- [x] Validador de RUC ecuatoriano (provincia + tipo + dígito verificador, módulo 10/11)
- [x] API de Clientes: CRUD, contactos y consentimientos
- [x] API de Proveedores
- [x] API de Documentos: subida a MinIO, **versionado** e integridad **SHA-256**, descarga por URL prefirmada
- [x] Servicio de almacenamiento abstracto (MinIO en prod, fake en memoria en tests)
- [x] Tests: 19 passed (RUC, clientes, consentimiento, documentos)

Endpoints nuevos: `/api/v1/customers`, `/api/v1/suppliers`, `/api/v1/documents`.

## Estado de S2 — Tax Rule Engine + Extracción de proforma

- [x] Modelo `TaxRule` versionado (fecha de vigencia, versión, estado, fuente legal) + migración `0003`
- [x] Motor de cálculo **por ítem** y **en cadena** por dependencias (CIF → AD_VALOREM → FODINFA → ICE → IVA)
- [x] Selección de regla por **especificidad** (HS > origen/acuerdo; a igualdad, mayor versión) — soporta arancel preferencial
- [x] Reglas base de Ecuador sembrables (FODINFA, IVA) marcadas **NO verificadas** (pendiente fuente oficial)
- [x] API: `POST /tax/rules`, `GET /tax/rules`, `POST /tax/rules/seed-ecuador-defaults`, `POST /tax/simulate`
- [x] Pipeline de **extracción de proforma**: interfaz `Extractor` + extractor heurístico (texto/CSV y PDF con capa de texto); OCR/Document AI real como adapter enchufable
- [x] API: `POST /documents/{id}/versions/{n}/extract`, `GET .../extractions` (cada dato con `confidence_score`)
- [x] Tests: 26 passed

> Los porcentajes tributarios NO están en el código: viven en `tax_rule` (versionados). Las reglas sembradas requieren verificación oficial (SENAE/COMEX/SRI) antes de producción.

Siguiente: **S3** — Cotización + Landed Cost (Quote/QuoteItem/QuoteScenario) que consume el Tax Engine, PDF y estados de envío.
