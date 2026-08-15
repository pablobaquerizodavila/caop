import { cookies } from "next/headers";
import Link from "next/link";

import {
  apiGet,
  type Consent,
  type CustomerDoc,
  type CustomerHistory,
  type CustomerRecord,
  money,
  stateLabel,
} from "@/app/lib/api";
import { capsFromRoles, parseRolesCookie } from "@/app/lib/rbac";
import { CustomerCrmPanels } from "@/app/components/CustomerCrmPanels";
import { CustomerDocuments } from "@/app/components/CustomerDocuments";
import { DeleteCustomerButton } from "@/app/components/DeleteCustomerButton";

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
  const record = await apiGet<CustomerRecord>(`/customers/${params.id}`);
  const consents = await apiGet<Consent[]>(`/customers/${params.id}/consents`);
  const docs = (await apiGet<CustomerDoc[]>(`/documents?customer_id=${params.id}`)) ?? [];
  const legalDocs = docs.filter(
    (d) => d.doc_type === "RUC" || d.doc_type === "CEDULA" || d.doc_type === "APPOINTMENT",
  );
  const caps = capsFromRoles(parseRolesCookie(cookies().get("caop_roles")?.value));

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
        <div className="head"><h2>Datos generales</h2></div>
        <div className="grid-2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 }}>
          <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>Tipo</span>
            <div>{record?.entity_type === "COMPANY" ? "Empresa / sociedad" : "Persona natural"}</div></div>
          <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>RUC</span>
            <div className="mono">{c.ruc}</div></div>
          <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>País</span>
            <div>{record?.country || "Ecuador"}</div></div>
          <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>Provincia</span>
            <div>{record?.province || <span style={{ color: "var(--muted-2)" }}>—</span>}</div></div>
          <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>Ciudad</span>
            <div>{record?.city || <span style={{ color: "var(--muted-2)" }}>—</span>}</div></div>
          <div className="field" style={{ gridColumn: "1 / -1" }}><span style={{ color: "var(--muted)", fontSize: 12 }}>Dirección (calle, número, referencia)</span>
            <div>{record?.address || <span style={{ color: "var(--muted-2)" }}>— no registrada —</span>}</div></div>
          <div className="field" style={{ gridColumn: "1 / -1" }}><span style={{ color: "var(--muted)", fontSize: 12 }}>Dirección de despacho</span>
            <div>
              {record?.dispatch_same_as_address
                ? <span style={{ color: "var(--muted-2)" }}>Misma que la dirección física</span>
                : ([record?.dispatch_address, record?.dispatch_city, record?.dispatch_province, record?.dispatch_country]
                    .filter(Boolean).join(", ") || <span style={{ color: "var(--muted-2)" }}>— no registrada —</span>)}
            </div></div>
          {record?.entity_type === "COMPANY" ? (
            <>
              <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>Representante legal</span>
                <div>{record?.legal_rep_name || <span style={{ color: "var(--muted-2)" }}>— no registrado —</span>}</div></div>
              <div className="field"><span style={{ color: "var(--muted)", fontSize: 12 }}>Cédula/RUC del representante</span>
                <div className="mono">{record?.legal_rep_id || "—"}</div></div>
            </>
          ) : null}
        </div>
        <div className="head" style={{ marginTop: 14 }}><h3>Documentos legales</h3></div>
        <CustomerDocuments docs={legalDocs} />

        {caps.canAdmin ? (
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
            <div className="eyebrow" style={{ color: "var(--muted-2)", marginBottom: 8 }}>Zona de riesgo</div>
            <DeleteCustomerButton customerId={params.id} />
          </div>
        ) : null}
      </div>

      <div className="section-gap">
        <CustomerCrmPanels
          customerId={params.id}
          contacts={record?.contacts ?? []}
          consents={consents ?? []}
        />
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
                  <th>Expediente</th><th>Cotización</th><th>Estado</th><th>Modalidad</th><th>Origen</th>
                  <th>Readiness</th><th>Creado</th>
                </tr>
              </thead>
              <tbody>
                {h.cases.map((x) => (
                  <tr key={x.id} className="row">
                    <td><Link href={`/cases/${x.id}`} className="code">{x.case_number}</Link></td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>{x.source_quote_number ?? "—"}</td>
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
                <tr><th>Cotización</th><th>Expediente</th><th>Estado</th><th className="num">Landed cost</th><th>Creada</th></tr>
              </thead>
              <tbody>
                {h.quotes.map((q) => (
                  <tr key={q.id}>
                    <td className="code">{q.quote_number}<span style={{ color: "var(--muted-2)" }}> v{q.version}</span></td>
                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>{q.case_number ?? "—"}</td>
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
