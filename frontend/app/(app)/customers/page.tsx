import Link from "next/link";

import { apiGet, type CustomerSummary } from "@/app/lib/api";

export const dynamic = "force-dynamic";

export default async function CustomersPage({
  searchParams,
}: {
  searchParams?: { q?: string };
}) {
  const q = (searchParams?.q ?? "").trim();
  const url = q ? `/customers?limit=200&q=${encodeURIComponent(q)}` : "/customers?limit=200";
  const customers = await apiGet<CustomerSummary[]>(url);

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
          <span className="count">{customers?.length ?? 0}</span>
        </div>
        {!customers || customers.length === 0 ? (
          <div className="empty">
            {customers === null
              ? "No se pudo conectar con el backend."
              : q
                ? "Sin coincidencias para la búsqueda."
                : "Aún no hay clientes."}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>RUC</th>
                  <th>Razón social</th>
                  <th>Email</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id} className="row">
                    <td>
                      <Link href={`/customers/${c.id}`} className="code">
                        {c.ruc}
                      </Link>
                    </td>
                    <td>
                      <Link href={`/customers/${c.id}`} style={{ color: "var(--text)" }}>
                        {c.legal_name}
                      </Link>
                    </td>
                    <td style={{ color: "var(--muted)" }}>{c.email ?? "—"}</td>
                    <td>
                      <span className="pill">{c.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
