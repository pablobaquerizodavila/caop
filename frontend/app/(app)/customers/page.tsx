import Link from "next/link";

import { apiGet, type CustomerSummary } from "@/app/lib/api";

export const dynamic = "force-dynamic";

export default async function CustomersPage() {
  const customers = await apiGet<CustomerSummary[]>("/customers?limit=200");

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

      <div className="card rise">
        <div className="head">
          <h2>Clientes registrados</h2>
          <span className="count">{customers?.length ?? 0}</span>
        </div>
        {!customers || customers.length === 0 ? (
          <div className="empty">
            {customers === null ? "No se pudo conectar con el backend." : "Aún no hay clientes."}
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
                  <tr key={c.id}>
                    <td className="code">{c.ruc}</td>
                    <td>{c.legal_name}</td>
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
