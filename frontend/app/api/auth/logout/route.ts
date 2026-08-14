import { NextResponse } from "next/server";

import { APP_URL, CLIENT_ID, LOGOUT_URL } from "@/app/lib/auth";

export const runtime = "nodejs";

export async function GET() {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    post_logout_redirect_uri: `${APP_URL}/login`,
  });
  const res = NextResponse.redirect(`${LOGOUT_URL}?${params.toString()}`);
  res.cookies.delete("access_token");
  res.cookies.delete("refresh_token");
  res.cookies.delete("caop_user");
  return res;
}
