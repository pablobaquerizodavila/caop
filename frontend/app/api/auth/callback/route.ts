import { type NextRequest, NextResponse } from "next/server";

import {
  APP_URL,
  CLIENT_ID,
  REDIRECT_URI,
  rolesFromToken,
  TOKEN_URL,
  usernameFromToken,
} from "@/app/lib/auth";

export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const verifier = req.cookies.get("pkce_verifier")?.value;
  const savedState = req.cookies.get("oauth_state")?.value;

  if (!code || !verifier || !state || state !== savedState) {
    return NextResponse.redirect(`${APP_URL}/login?error=state`);
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: verifier,
  });

  const tokenRes = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    cache: "no-store",
  });

  if (!tokenRes.ok) {
    return NextResponse.redirect(`${APP_URL}/login?error=token`);
  }

  const tok = await tokenRes.json();
  const res = NextResponse.redirect(`${APP_URL}/`);
  const base = { httpOnly: true, sameSite: "lax" as const, path: "/" };

  res.cookies.set("access_token", tok.access_token, {
    ...base,
    maxAge: tok.expires_in ?? 300,
  });
  if (tok.refresh_token) {
    res.cookies.set("refresh_token", tok.refresh_token, {
      ...base,
      maxAge: tok.refresh_expires_in ?? 1800,
    });
  }
  // Cookies legibles por la UI: usuario y roles (para ocultar acciones por rol).
  const uiCookie = { httpOnly: false, sameSite: "lax" as const, path: "/", maxAge: tok.expires_in ?? 300 };
  res.cookies.set("caop_user", usernameFromToken(tok.access_token), uiCookie);
  res.cookies.set("caop_roles", rolesFromToken(tok.access_token).join(","), uiCookie);
  res.cookies.delete("pkce_verifier");
  res.cookies.delete("oauth_state");
  return res;
}
