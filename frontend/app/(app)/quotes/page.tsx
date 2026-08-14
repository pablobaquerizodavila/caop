import Link from "next/link";

import { apiGet, money, type QuoteSummary } from "@/app/lib/api";
import { QuoteActions } from "@/app/components/QuoteActions";

export const dynamic = "force-dynamic";

const STATUS_CLASS: Record<string, string> = {
  DRAFT: "",
  SENT: "accent",
  DELIVERED: "accent",
  READ: "accent",
  ACCEPTED: "ok",
  REJECTED: "crit",
  EXPIRED: "warn",
};

export default async function QuotesPage() {
  const quotes = await apiGet<QuoteSummary[]>("/quotes?limit=200");

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Comercial</div>
          <h1>Cotizaciones</h1>
        </div>
        <Link href="/quotes/new" className="btn">
          + Nueva cotización
        </Link>
      </div>

      <div className="card rise">
        <div className="head">
          <h2>Simulaciones de importación</h2>
          <span className="count">{quotes?.length ?? 0}</span>
        </div>
        {!quotes || quotes.length === 0 ? (
          <div className="empty">
            {quotes === null ? "No se pudo conectar con el backend." : "Aún no hay cotizaciones."}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Cotización</th>
                  <th>Expediente</th>
                  <th>Estado</th>
                  <th className="num">Tributos</th>
                  <th className="num">Landed cost</th>
                  <th className="num">Por unidad</th>
                  <th>Confianza</th>
                  <th>Válida hasta</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((q) => (
                  <tr key={q.id}>
                    <td className="code">
                      {q.quote_number}
                      <span style={{ color: "var(--muted-2)" }}> v{q.version}</span>
                    </td>
                    <td>
                      {q.case_number && q.case_id ? (
                        <Link href={`/cases/${q.case_id}`} className="code">
                          {q.case_number}
                        </Link>
                      ) : (
                        <span style={{ color: "var(--muted-2)" }}>—</span>
                      )}
                    </td>
                    <td>
                      <span className={`pill ${STATUS_CLASS[q.status] ?? ""}`}>{q.status}</span>
                    </td>
                    <td className="num">{money(q.total_taxes, q.currency)}</td>
                    <td className="num">{money(q.landed_cost_total, q.currency)}</td>
                    <td className="num">{money(q.landed_cost_per_unit, q.currency)}</td>
                    <td className="mono" style={{ color: "var(--muted)" }}>
                      {q.confidence != null ? `${Math.round(Number(q.confidence))}%` : "—"}
                    </td>
                    <td className="mono" style={{ color: "var(--muted)" }}>
                      {q.valid_until ?? "—"}
                    </td>
                    <td>
                      <QuoteActions quoteId={q.id} status={q.status} />
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
