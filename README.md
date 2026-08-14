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

## Estado de S3 — Cotización + Landed Cost

- [x] Modelos Quote / QuoteItem / CostLine / QuoteStatusHistory + migración `0004`
- [x] Servicio de cotización: tributos **por ítem** (Tax Engine) + **landed cost** total y por unidad
- [x] Separación **precio cliente vs costo interno vs margen** (el cliente NO ve rentabilidad → vista pública)
- [x] Rubros de costo con **contingencia** y **confianza** (HIGH/MEDIUM/LOW) + exclusiones (NOT INCLUDED)
- [x] Prorrateo de flete/seguro por valor de línea
- [x] **PDF corporativo** (reportlab) almacenado en MinIO + descarga por URL prefirmada
- [x] Ciclo de estados con validación de transiciones e historial (DRAFT→SENT→…→ACCEPTED)
- [x] Versionamiento (revise = nueva versión sin sobrescribir la enviada)
- [x] API: `POST /quotes`, `GET /quotes[/{id}]`, `GET /quotes/{id}/public`, `recompute`, `status`, `pdf`, `pdf/download`, `revise`
- [x] Tests: 31 passed

## Estado de S4/S5 — Cotización → Expediente (flujo estrella)

- [x] Modelos Shipment, CustomsCase, CaseEvent, Requirement, ChecklistItem, SLAInstance + migración `0005`
- [x] **Conversión automática al ACEPTAR**: crea Shipment + CustomsCase + checklist + SLA + eventos, sin redigitar (idempotente)
- [x] Motor de checklist por requisitos (aplican según modalidad/acuerdo) + **readiness score**
- [x] Estados del expediente (CASE_CREATED → AWAITING_DOCUMENTS → READY_FOR_CUSTOMS) y `blocker` por documentos faltantes bloqueantes
- [x] SLA por hito (DOCUMENTS_COMPLETE) y **timeline** de eventos del caso
- [x] Requisitos base sembrables (factura, packing, BL/AWB, seguro, certificado de origen si hay acuerdo)
- [x] API: `/requirements`, `/cases`, `/cases/{id}` (checklist+eventos+SLA), PATCH checklist, `/quotes/{id}/convert`, `/quotes/{id}/case`
- [x] Tests: 35 passed

## Estado de S6 — Notificaciones (email + WhatsApp)

- [x] Modelos Notification + NotificationTemplate (plantillas versionadas) + migración `0006`
- [x] Servicio de notificaciones con render `{{placeholders}}` y dispatch (registra + envía)
- [x] **Email** vía SMTP (Mailpit en dev, mailcow en prod) con aiosmtplib
- [x] **WhatsApp**: conector propio sobre la WhatsApp Business Platform oficial; sin token → modo **SIMULADO** (no inventa credenciales/endpoints)
- [x] **Auto-notificación**: al crear el expediente se envía DOCUMENT_REQUIRED al cliente con los documentos bloqueantes faltantes (best-effort, registrado en el timeline)
- [x] Plantillas base sembrables (DOCUMENT_REQUIRED email/whatsapp, QUOTATION_SENT)
- [x] API: `/notifications/send`, `/notifications`, `/notifications/templates[/seed-defaults]`
- [x] Tests: 39 passed

## Estado de S8 — Auto-vínculo documento → checklist

- [x] Al subir/asociar un documento a un expediente con doc_type que calza, el ítem del checklist se marca **COMPLETE automáticamente**
- [x] Recalcula readiness y transiciona el estado del expediente sin intervención
- [x] Eventos en el timeline: DOCUMENT_RECEIVED + CHECKLIST_AUTO_COMPLETED
- [x] Subida acepta `customs_case_id`; endpoint `POST /documents/{id}/attach` para documentos existentes
- [x] Sin cambio de esquema (columnas ya existían); Tests: 43 passed

## Estado de S9 — SLA engine + Business Calendar + escalamiento

- [x] `BusinessCalendar` (horario por día, feriados, zona horaria) + aritmética de tiempo hábil
- [x] `SLAPolicy` por hito (minutos hábiles, calendario, severidad) — sembrable
- [x] Vencimientos calculados en **horas laborables** (no calendario), saltando fines de semana y feriados
- [x] Estado y **escalamiento** por umbrales: 70% AT_RISK · 85% CRITICAL · 100%/120% BREACHED (niveles 1–4)
- [x] `POST /sla/evaluate` (idempotente, llamable por cron) recalcula estado/escalamiento
- [x] SLA del expediente creado en la conversión con vencimiento hábil; se marca **MET** al llegar readiness 100
- [x] API: `/sla` (list), `/sla/seed-defaults`, `/sla/evaluate` · migración `0007` · dep `tzdata`
- [x] Tests: 51 passed

## Estado de S10 — Scheduler de SLA + riesgo SLA en la Torre de Control

- [x] Scheduler interno (asyncio en el backend) que corre `evaluate_all` cada N min (`SLA_EVALUATE_INTERVAL_MINUTES`, 0=off) — sin infra extra
- [x] Escalamiento automático sin intervención (el estado/nivel de los SLA se actualiza solo)
- [x] Torre de Control: KPI **"SLA en riesgo"** + sección con los SLA AT_RISK/CRITICAL/BREACHED enlazados a su expediente
- [x] Robustez de fechas UTC (naive/aware) en el motor SLA
- [x] Tests: 52 passed

## Estado de S11 — Autenticación Keycloak (frontend + backend)

- [x] **Backend protegido**: todos los endpoints de negocio requieren token Keycloak (health abierto)
- [x] Validación JWT: firma RS256 + issuer + expiración; JWKS por red interna, issuer público; audiencia flexible (azp/aud)
- [x] **Frontend con login OIDC** (Authorization Code + PKCE), cookies httpOnly, SSR reenvía el bearer, 401 → /login
- [x] Middleware protege todas las páginas; `/login`, callback y logout; usuario + "Salir" en la barra
- [x] Keycloak con hostname fijo (issuer estable) + backchannel dinámico (token exchange interno)
- [x] Route group `(app)` (login sin el shell); tests backend con bypass de auth: 52 passed; build frontend OK

## Estado de S12 — Refresh token automático

- [x] Middleware refresca la sesión en silencio con el refresh_token cuando el access_token expira (sin re-login)
- [x] Rotación de cookies (access/refresh/usuario) + reintento de la misma URL; si el refresh falla → /login
- [x] Edge-safe (fetch + atob, sin node:crypto en el middleware); build OK

## Estado de S13 — UI operativa (Server Actions)

- [x] Subir documentos al expediente desde la UI (auto-vincula checklist y sube readiness)
- [x] Acciones de cotización: Enviar (DRAFT→SENT), Aceptar (→ crea expediente), generar/abrir PDF
- [x] Server Actions leen la cookie httpOnly y reenvían el token (el navegador nunca ve el access_token)
- [x] Helpers de presentación separados a `lib/format.ts` (seguro en Client Components)
- [x] Build OK

## Estado de S14 — Alta de cliente y cotización desde la UI

- [x] Nueva cotización desde la interfaz: cliente, cabecera, ítems dinámicos, rubros de costo → calcula tributos/landed cost
- [x] Alta de cliente (RUC validado, email, contacto) desde la UI
- [x] Nav "Clientes"; botones "+ Nueva cotización" / "+ Nuevo cliente"; Server Actions con reenvío de token
- [x] Ciclo comercial 100% en la interfaz: crear cliente → crear cotización → enviar → aceptar → expediente
- [x] Build OK

## Estado de S15 — Reportes / Analytics

- [x] Endpoint `/analytics/overview` con KPIs calculados sobre datos reales
- [x] KPIs del prompt: **Human Touches per Shipment**, **Straight-Through Rate**, **Automation Rate**
- [x] Conversión de cotizaciones, expedientes por estado, tiempo de preparación, SLA, notificaciones
- [x] Página **Reportes** en la UI (tiles + barras de desglose), nav "Reportes"
- [x] Tests: 54 passed

## Estado de S16 — Simulador del SENAE Connector (DAI, Fase 2)

- [x] Conector SENAE con **contrato común** (Protocol) + **simulador** (adapter real enchufable)
- [x] Modelo `CustomsDeclaration` (DAI) con `raw_sent`/`raw_response` y mapping EXTERNAL→INTERNAL
- [x] Ciclo: preparar (readiness 100) → **firmar** (humano, invariante) → transmitir → liquidación → pago → aforo → levante
- [x] Escenarios de prueba: ACCEPT / REJECT / **SENAE no disponible** (retry); aforo AUTOMATICO/DOCUMENTAL/FISICO/NO_INTRUSIVO; observación
- [x] **Idempotencia**: la DAI no se transmite dos veces; estados internos = placeholders (no ECUAPASS literal)
- [x] Panel DAI operable en el detalle del expediente (UI)
- [x] Migración `0008`; Tests: 61 passed

> Todo marcado `is_simulated=True`. El adapter real reemplaza el simulador cuando exista documentación oficial, sin reescribir el flujo.

## Estado de S17 — Vincular cliente + Historial de importaciones

- [x] Vincular/reasignar cliente a una cotización (`POST /quotes/{id}/link-customer`), propaga al expediente
- [x] **Panel del cliente** (`/customers/{id}`): historial de importaciones (expedientes) + cotizaciones + stats
- [x] Clic en RUC/nombre en el listado de clientes → panel del cliente
- [x] **Bugfix real**: cotización con `cost_lines` vacío daba 500 (lazy-load de relación no cargada); también en Postgres
- [x] Tests: 66 passed

## Estado de S18 — Correlación visual cotización ↔ expediente

- [x] La cotización muestra su nº de **expediente** (`case_number`, enlazado) en el listado y en el detalle
- [x] El expediente muestra su **cotización de origen** (`source_quote_number`) en el detalle y en el listado
- [x] Panel del cliente: ambas tablas correlacionan (expediente↔cotización)
- [x] Backend: enriquecimiento por join en `/quotes`, `/cases`, `/customers/{id}/history`
- [x] Tests: 66 passed

Pendientes (requieren terceros): integración real SENAE/ECUAPASS (doc del usuario); WhatsApp real (credenciales Meta).
