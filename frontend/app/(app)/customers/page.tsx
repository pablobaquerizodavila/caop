import Link from "next/link";

import { apiGet, type CustomerSummary } from "@/app/lib/api";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 50;

export default async function CustomersPage({
  searchParams,
}: {
  searchParams?: { q?: string; page?: string };
}) {
  const q = (searchParams?.q ?? "").trim();
  const page = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  // Pide uno de más (51) para saber si hay página siguiente sin un conteo aparte.
  const params = new URLSearchParams({ limit: String(PAGE_SIZE + 1), offset: String(offset) });
  if (q) params.set("q", q);
  const fetched = await apiGet<CustomerSummary[]>(`/customers?${params.toString()}`);

  const rows = (fetched ?? []).slice(0, PAGE_SIZE);
  const hasNext = (fetched?.length ?? 0) > PAGE_SIZE;
  const hasPrev = page > 1;

  const pageHref = (p: number) => {
    const sp = new URLSearchParams();
    if (q) sp.set("q", q);
    if (p > 1) sp.set("page", String(p));
    const qs = sp.toString();
    return qs ? `/customers?${qs}` : "/customers";
  };

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">CRM</div>
          <h1>Clientes</h1>
        </div>
        <Link href="/customers/new" className="btn">
          + Nuevo cliente
        </Link>
      </div>

      <form method="GET" className="card rise section-gap" style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
        <label className="field" style={{ flex: 1, minWidth: 220 }}>
          <span>Buscar por nombres, apellidos, razón social o RUC</span>
          <input type="text" name="q" defaultValue={q} placeholder="Ej: Pérez, García, ANDINA, 1790…" />
        </label>
        <button className="btn" type="submit">Buscar</button>
        {q ? <Link href="/customers" className="btn ghost">Limpiar</Link> : null}
      </form>

      <div className="card rise">
        <div className="head">
          <h2>{q ? `Resultados para “${q}”` : "Clientes registrados"}</h2>
          <span className="count">{rows.length}</span>
        </div>
        {rows.length === 0 ? (
          <div className="empty">
            {fetched === null
              ? "No se pudo conectar con el backend."
              : q
                ? "Sin coincidencias para la búsqueda."
                : "Aún no hay clientes."}
          </div>
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>RUC</th>
                    <th>Razón social / Nombre</th>
                    <th>Tipo</th>
                    <th>Representante legal</th>
                    <th>Email</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.id} className="row">
                      <td>
                        <Link href={`/customers/${c.id}`} className="code">{c.ruc}</Link>
                      </td>
                      <td>
                        <Link href={`/customers/${c.id}`} style={{ color: "var(--text)" }}>{c.legal_name}</Link>
                      </td>
                      <td>
                        <span className="pill">{c.entity_type === "COMPANY" ? "Empresa" : "Natural"}</span>
                      </td>
                      <td style={{ color: "var(--muted)" }}>{c.legal_rep_name || "—"}</td>
                      <td style={{ color: "var(--muted)" }}>{c.email ?? "—"}</td>
                      <td>
                        <span className="pill">{c.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
              <span style={{ color: "var(--muted)", fontSize: 12.5 }}>
                Página {page} · mostrando {rows.length} de a {PAGE_SIZE}
              </span>
              <div style={{ display: "flex", gap: 8 }}>
                {hasPrev ? (
                  <Link href={pageHref(page - 1)} className="btn ghost">← Anteriores</Link>
                ) : (
                  <span className="btn ghost" aria-disabled style={{ opacity: 0.5, pointerEvents: "none" }}>← Anteriores</span>
                )}
                {hasNext ? (
                  <Link href={pageHref(page + 1)} className="btn ghost">Siguientes →</Link>
                ) : (
                  <span className="btn ghost" aria-disabled style={{ opacity: 0.5, pointerEvents: "none" }}>Siguientes →</span>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
