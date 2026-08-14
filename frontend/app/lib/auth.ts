// Configuración y utilidades OIDC (Keycloak) para el frontend.
import crypto from "node:crypto";

export const KC_PUBLIC = process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://192.168.0.7:8080";
export const KC_INTERNAL = process.env.KEYCLOAK_INTERNAL_URL ?? "http://keycloak:8080";
export const REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "caop";
export const CLIENT_ID = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "caop-frontend";
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://192.168.0.7:3000";
export const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

export const AUTHORIZE_URL = `${KC_PUBLIC}/realms/${REALM}/protocol/openid-connect/auth`;
export const TOKEN_URL = `${KC_INTERNAL}/realms/${REALM}/protocol/openid-connect/token`;
export const LOGOUT_URL = `${KC_PUBLIC}/realms/${REALM}/protocol/openid-connect/logout`;

export function pkce(): { verifier: string; challenge: string } {
  const verifier = crypto.randomBytes(32).toString("base64url");
  const challenge = crypto.createHash("sha256").update(verifier).digest("base64url");
  return { verifier, challenge };
}

export function randomState(): string {
  return crypto.randomBytes(16).toString("base64url");
}

export function usernameFromToken(accessToken: string): string {
  try {
    const payload = JSON.parse(
      Buffer.from(accessToken.split(".")[1], "base64url").toString("utf-8"),
    );
    return payload.preferred_username ?? payload.name ?? "usuario";
  } catch {
    return "usuario";
  }
}
