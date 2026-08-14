// Cliente de API del backend CAOP (server-side fetch).
// En SSR (dentro del contenedor) se usa la red interna de compose (backend:8000);
// NEXT_PUBLIC_API_URL (host público) queda para peticiones desde el navegador.
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export * from "./format";

export const API =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://backend:8000";

export async function apiGet<T>(path: string): Promise<T | null> {
  const token = cookies().get("access_token")?.value;
  let res: Response;
  try {
    res = await fetch(`${API}/api/v1${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
  } catch {
    return null;
  }
  // Token ausente/expirado -> reautenticar (redirect fuera del try/catch).
  if (res.status === 401) redirect("/login");
  if (!res.ok) return null;
  return (await res.json()) as T;
}
