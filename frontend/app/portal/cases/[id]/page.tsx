import Link from "next/link";

import { TrackDetail } from "@/app/components/TrackDetail";
import { apiGet, money, type PortalCaseDetail, settleCatLabel } from "@/app/lib/api";

export const dynamic = "force-dynamic";

export default async function PortalCasePage({ params }: { params: { id: string } }) {
  const d = await apiGet<PortalCaseDetail>(`/portal/cases/${params.id}`);

  if (!d) {
    return (
      <section className="trk-card">
        <Link href="/portal" className="trk-back">← Mis importaciones</Link>
        <div style={{ padding: 12, color: "var(--muted)" }}>Expediente no encontrado.</div>
      </section>
    );
  }

  const s = d.settlement;

  return (
    <>
      <Link href="/portal" className="trk-back">← Mis importaciones</Link>
      <TrackDetail v={d.track} />

      {s ? (
        <section className="trk-card">
          <h2>Liquidación · {s.settlement_number}</h2>
          {s.lines.map((ln) => (
            <div className="trk-settle-row" key={ln.id}>
              <span>
                {ln.description || settleCatLabel(ln.category)}
                <span style={{ color: "var(--muted-2)", fontSize: 11 }}>
                  {" "}· {ln.kind === "FEE" ? "honorario" : "desembolso"}
                </span>
              </span>
              <span className="mono">{money(ln.amount, s.currency)}</span>
            </div>
          ))}
          <div className="trk-settle-row">
            <span>IVA ({s.iva_rate}%)</span>
            <span className="mono">{money(s.tax_amount, s.currency)}</span>
          </div>
          <div className="trk-settle-total">
            <span>Total a pagar</span>
            <span className="mono">{money(s.total, s.currency)}</span>
          </div>
        </section>
      ) : null}
    </>
  );
}
