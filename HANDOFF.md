# HANDOFF — CAOP / Panamerican Tracking Dispatch (panamtrack)

> Documento de continuidad entre sesiones. Última actualización: **2026-10-01**.

## Qué es
Plataforma de despacho aduanero (Ecuador). Backend FastAPI + Next.js 14, Keycloak (OIDC),
Postgres/Redis/MinIO, Docker Compose. Desplegado en **192.168.0.7** y publicado en
**https://www.panamtrack.com** (login en `auth.panamtrack.com`, Keycloak realm `caop`).

- Repo: `github.com/pablobaquerizodavila/caop` (rama `main`).
- SSH deploy: `ssh -i "C:\Users\Pablo B\.ssh\id_caop_deploy" pbaquerizo@192.168.0.7`, repo en `~/caop`.
- Proxy: nginx del host (sin sudo sin password). Cert Let's Encrypt (www + auth).

## Sesión 2026-10-01 — Auth / usuarios

### Hecho
1. **Super admin renombrado** `admin-caop` → **`pbaquerizo`** (rol SUPER_ADMIN), con su
   contraseña propia. Ajustados `UsersManager.tsx` (PROTECTED_USER) y el texto del panel admin.
2. **Fix del loop de login (causa raíz):** el backend devolvía **401** porque
   `KEYCLOAK_ISSUER` apuntaba a la IP (`http://192.168.0.7:8080/realms/caop`) y los tokens
   emitidos vía el dominio llevan `iss=https://auth.panamtrack.com/realms/caop` (por
   `KC_HOSTNAME`). Se corrigió `KEYCLOAK_ISSUER` en el **`.env` del servidor** (server-only,
   NO en git) → `https://auth.panamtrack.com/realms/caop` y se reinició el backend.
   Verificado end-to-end: login → `/panel` con datos reales; backend 200.
3. **Solo `pbaquerizo`**: eliminado el usuario de desarrollo `agente`. Verificado rechazado.
4. **Nuevo agente**: creado **`fcalderon`** (Flor María Calderón, rol CUSTOMS_AGENT),
   email `fcalderon@panamtrack.com`.

### Último commit
`ffba011` — realm: nombre completo de fcalderon (Flor Maria Calderon).

### Estado actual
- Usuarios Keycloak: `pbaquerizo` (SUPER_ADMIN), `fcalderon` (CUSTOMS_AGENT).
- Login operativo en https://www.panamtrack.com/login.

## Notas de despliegue críticas (leer antes de tocar Keycloak)
- **Keycloak corre en `start-dev --import-realm` con H2 efímero.** La **fuente de verdad**
  de usuarios/roles es `keycloak/realm-caop.json`. Para aplicar cambios:
  `git pull` en el server → `docker compose up -d --force-recreate keycloak` (reimporta el realm).
- **Cada recreate de Keycloak rota las llaves de firma** → **reiniciar el backend**
  (`docker compose restart backend`) para refrescar el JWKS cacheado, si no vuelve el 401.
- **Issuer:** `KEYCLOAK_ISSUER` (backend, en `~/caop/.env`) DEBE coincidir con `KC_HOSTNAME`
  (hoy `https://auth.panamtrack.com/realms/caop`). Ver `backend/app/core/security.py`.

## Pendientes / riesgos
- **Seguridad:** las contraseñas de usuario están en texto plano en `keycloak/realm-caop.json`
  (repo público). Recomendado: contraseñas **temporales** de primer ingreso (cada quien define
  la suya, nunca toca el repo), o pasar Keycloak a **modo producción con Postgres persistente**
  (elimina la reimportación por H2 efímero y la rotación de llaves en cada cambio).
- El commit de `realm-caop.json` lo debe hacer el usuario cuando contenga contraseñas nuevas
  (el asistente no sube credenciales en claro).

## Cómo cerrar sesión (este repo)
No hay script de backup ni ruta de NAS documentada para CAOP (la carpeta está bajo cloud sync).
Pasos reales de cierre: actualizar este HANDOFF, commit + push a `origin/main`.
