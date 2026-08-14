import Link from "next/link";

import { apiGet, type CustomerHistory, money, stateLabel } from "@/app/lib/api";

export const dynamic = "force-dynamic";

const STATE_CLASS: Record<string, string> = {
  READY_FOR_CUSTOMS: "ok",
  AWAITING_DOCUMENTS: "warn",
  RELEASED: "ok",
  OBSERVED: "risk",
  REJECTED: "crit",
};

export default async function CustomerDetailPage({ params }: { params: { id: string } }) {
  const h = await apiGet<CustomerHistory>(`/customers/${params.id}/history`);

  if (!h) {
    return (
      <>
        <div className="topbar"><h1>Cliente</h1></div>
        <div className="card"><div className="empty">Cliente no encontrado.</div></div>
      </>
    );
  }

  const c = h.customer;
  return (
    <>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        <Link href="/customers" style={{ color: "var(--accent)" }}>← Clientes</Link>
      </div>
      <div className="topbar">
        <div>
          <div className="eyebrow">CRM · Importador recurrente</div>
          <h1>{c.trade_name || c.legal_name}</h1>
          <div className="meta" style={{ display: "flex", gap: 18, color: "var(--muted)", marginTop: 6, fontSize: 13 }}>
            <span className="mono">RUC {c.ruc}</span>
            <span>{c.legal_name}</span>
            {c.email ? <span className="mono">{c.email}</span> : null}
          </div>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi accent"><div className="k-label">Importaciones</div><div className="k-value">{h.stats.total_cases}</div></div>
        <div className="kpi ok"><div className="k-label">Listas para aduana</div><div className="k-value">{h.stats.ready_for_customs}</div></div>
        <div className="kpi"><div className="k-label">Cotizaciones</div><div className="k-value">{h.stats.total_quotes}</div></div>
      </div>

      <div className="card section-gap rise">
        <div className="head">
          <h2>Historial de importaciones</h2>
          <span className="count">{h.cases.length}</span>
        </div>
        {h.cases.length === 0 ? (
          <div className="empty">Este cliente aún no tiene expedientes.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Expediente</th><th>Estado</th><th>Modalidad</th><th>Origen</th>
                  <th>Readiness</th><th>Creado</th>
                </tr>
              </thead>
              <tbody>
                {h.cases.map((x) => (
                  <tr key={x.id} className="row">
                    <td><Link href={`/cases/${x.id}`} className="code">{x.case_number}</Link></td>
                    <td><span className={`pill ${STATE_CLASS[x.current_state] ?? ""}`}>{stateLabel(x.current_state)}</span></td>
                    <td className="mono">{x.transport_mode ?? "—"}</td>
                    <td className="mono">{x.origin_country ?? "—"}</td>
                    <td className="num">{Math.round(x.customs_readiness_score)}%</td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                      {x.created_at ? new Date(x.created_at).toLocaleDateString("es-EC") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Cotizaciones</h2>
          <span className="count">{h.quotes.length}</span>
        </div>
        {h.quotes.length === 0 ? (
          <div className="empty">Sin cotizaciones.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr><th>Cotización</th><th>Estado</th><th className="num">Landed cost</th><th>Creada</th></tr>
              </thead>
              <tbody>
                {h.quotes.map((q) => (
                  <tr key={q.id}>
                    <td className="code">{q.quote_number}<span style={{ color: "var(--muted-2)" }}> v{q.version}</span></td>
                    <td><span className="pill">{q.status}</span></td>
                    <td className="num">{money(q.landed_cost_total, q.currency)}</td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                      {q.created_at ? new Date(q.created_at).toLocaleDateString("es-EC") : "—"}
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
