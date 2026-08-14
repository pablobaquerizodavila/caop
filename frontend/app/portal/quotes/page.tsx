import Link from "next/link";

import { apiGet, money, type PortalQuote } from "@/app/lib/api";

export const dynamic = "force-dynamic";

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Borrador", SENT: "Enviada", DELIVERED: "Entregada",
  READ: "Leída", ACCEPTED: "Aceptada", REJECTED: "Rechazada", EXPIRED: "Vencida",
};

export default async function PortalQuotesPage() {
  const quotes = await apiGet<PortalQuote[]>("/portal/quotes");

  return (
    <>
      <Link href="/portal" className="trk-back">← Inicio</Link>
      <section className="trk-card">
        <h2>Mis cotizaciones</h2>
        {!quotes || quotes.length === 0 ? (
          <div style={{ padding: 12, color: "var(--muted)" }}>Aún no tienes cotizaciones.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="trk-table">
              <thead>
                <tr>
                  <th>Cotización</th><th>Estado</th>
                  <th className="num">Costo total (landed)</th><th>Válida hasta</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((q) => (
                  <tr key={q.id}>
                    <td className="mono">{q.quote_number} v{q.version}</td>
                    <td>{STATUS_LABEL[q.status] ?? q.status}</td>
                    <td className="num">{money(q.landed_cost_total, q.currency)}</td>
                    <td>{q.valid_until ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
