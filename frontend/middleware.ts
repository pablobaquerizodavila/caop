import { type NextRequest, NextResponse } from "next/server";

// Protege todas las páginas: sin access_token -> /login.
// Excluye /login, /api/auth/*, assets de _next y el favicon.
export function middleware(req: NextRequest) {
  const token = req.cookies.get("access_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
