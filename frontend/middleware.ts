import { type NextRequest, NextResponse } from "next/server";

// Protege todas las páginas. Si no hay access_token pero sí refresh_token,
// intenta refrescar la sesión en silencio (sin re-login) y reintenta la misma URL.
// Excluye /login, /api/auth/*, assets de _next y el favicon.

const KC_INTERNAL = process.env.KEYCLOAK_INTERNAL_URL ?? "http://keycloak:8080";
const REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "caop";
const CLIENT_ID = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "caop-frontend";
const TOKEN_URL = `${KC_INTERNAL}/realms/${REALM}/protocol/openid-connect/token`;

function loginRedirect(req: NextRequest): NextResponse {
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  const res = NextResponse.redirect(url);
  res.cookies.delete("access_token");
  res.cookies.delete("refresh_token");
  res.cookies.delete("caop_user");
  res.cookies.delete("caop_roles");
  return res;
}

function claimsFromJWT(token: string): { username: string; roles: string[] } {
  try {
    const seg = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(seg));
    const roles = payload?.realm_access?.roles;
    return {
      username: payload.preferred_username ?? payload.name ?? "usuario",
      roles: Array.isArray(roles) ? roles : [],
    };
  } catch {
    return { username: "usuario", roles: [] };
  }
}

export async function middleware(req: NextRequest) {
  const at = req.cookies.get("access_token")?.value;
  if (at) {
    // Backfill de cookies de UI (roles) para sesiones abiertas antes del RBAC.
    if (!req.cookies.get("caop_roles")) {
      const { username, roles } = claimsFromJWT(at);
      const res = NextResponse.next();
      const uiCookie = { httpOnly: false, sameSite: "lax" as const, path: "/" };
      res.cookies.set("caop_user", username, uiCookie);
      res.cookies.set("caop_roles", roles.join(","), uiCookie);
      return res;
    }
    return NextResponse.next();
  }

  const refresh = req.cookies.get("refresh_token")?.value;
  if (!refresh) {
    return loginRedirect(req);
  }

  // Refresco silencioso
  let tok: Record<string, string | number> | null = null;
  try {
    const r = await fetch(TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        client_id: CLIENT_ID,
        refresh_token: refresh,
      }),
      cache: "no-store",
    });
    if (r.ok) tok = await r.json();
  } catch {
    tok = null;
  }

  if (!tok || !tok.access_token) {
    return loginRedirect(req);
  }

  // Cookies nuevas + reintento de la misma URL (para que la página vea el token).
  const res = NextResponse.redirect(req.nextUrl);
  const base = { httpOnly: true, sameSite: "lax" as const, path: "/" };
  res.cookies.set("access_token", String(tok.access_token), {
    ...base,
    maxAge: Number(tok.expires_in ?? 300),
  });
  if (tok.refresh_token) {
    res.cookies.set("refresh_token", String(tok.refresh_token), {
      ...base,
      maxAge: Number(tok.refresh_expires_in ?? 1800),
    });
  }
  const { username, roles } = claimsFromJWT(String(tok.access_token));
  const uiCookie = {
    httpOnly: false,
    sameSite: "lax" as const,
    path: "/",
    maxAge: Number(tok.expires_in ?? 300),
  };
  res.cookies.set("caop_user", username, uiCookie);
  res.cookies.set("caop_roles", roles.join(","), uiCookie);
  return res;
}

export const config = {
  // /track/* es público (portal del cliente); se excluye junto con login y assets.
  matcher: ["/((?!login|track|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
