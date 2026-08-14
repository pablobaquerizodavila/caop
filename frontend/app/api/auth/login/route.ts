import { NextResponse } from "next/server";

import { AUTHORIZE_URL, CLIENT_ID, pkce, randomState, REDIRECT_URI } from "@/app/lib/auth";

export const runtime = "nodejs";

export async function GET() {
  const { verifier, challenge } = pkce();
  const state = randomState();

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: "openid profile email",
    code_challenge: challenge,
    code_challenge_method: "S256",
    state,
  });

  const res = NextResponse.redirect(`${AUTHORIZE_URL}?${params.toString()}`);
  const opts = { httpOnly: true, sameSite: "lax" as const, path: "/", maxAge: 600 };
  res.cookies.set("pkce_verifier", verifier, opts);
  res.cookies.set("oauth_state", state, opts);
  return res;
}
