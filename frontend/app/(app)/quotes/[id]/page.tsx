import Link from "next/link";

import { apiGet, money } from "@/app/lib/api";
import { CertificatesPanel } from "@/app/components/CertificatesPanel";
import { QuoteActions } from "@/app/components/QuoteActions";

export const dynamic = "force-dynamic";

interface Pref {
  agreement_code: string; agreement_name: string; preferential_adval_pct: number;
  preferential_taxes: number; savings: number; requires_certificate: boolean;
  certificate_present: boolean; verified: boolean;
}
interface Item {
  id: string; line_no: number; description?: string | null; hs_code?: string | null;
  hs_validation: string; cif_value: number | string; taxes_total: number | string;
  tax_complete: boolean; preference?: Pref | null; origin_country?: string | null;
}
interface Quote {
  id: string; quote_number: string; version: number; status: string; currency: string;
  origin_country?: string | null; total_cif: number | string; total_taxes: number | string;
  customer_price_total: number | string; landed_cost_total: number | string;
  confidence?: number | string | null; items: Item[];
}
interface Cert {
  id: string; cert_type: string; number?: string | null; issuing_country?: string | null;
  organism?: string | null; issue_date?: string | null; valid_until?: string | null; validation_status: string;
}

export default async function QuoteDetailPage({ params }: { params: { id: string } }) {
  const quote = await apiGet<Quote>(`/quotes/${params.id}`);
  if (!quote) {
    return (
      <div className="topbar"><div><h1>Cotización no encontrada</h1>
        <Link href="/quotes" className="btn ghost">← Cotizaciones</Link></div></div>
    );
  }
  const certificates = (await apiGet<Cert[]>(`/quotes/${params.id}/certificates`)) ?? [];
  const cur = quote.currency;
  const fmt = (v: number | string) => money(v, cur);
  const withPref = quote.items.filter((i) => i.preference);
  const prefTotal = withPref.reduce((s, i) => s + (i.preference?.preferential_taxes ?? 0), 0);
  const prefNormal = withPref.reduce((s, i) => s + Number(i.taxes_total || 0), 0);
  const savings = prefNormal - prefTotal;
  const applied = withPref.length > 0 && withPref.every((i) => i.preference?.certificate_present);

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Cotización · v{quote.version} · {quote.status}</div>
          <h1>{quote.quote_number}</h1>
        </div>
        <div className="actions">
          <Link href="/quotes" className="btn ghost">← Cotizaciones</Link>
          <QuoteActions quoteId={quote.id} status={quote.status} />
        </div>
      </div>

      <div className="card rise section-gap">
        <div className="head"><h2>Ítems y tributos</h2>
          {quote.origin_country ? <span className="count">Origen {quote.origin_country}</span> : null}
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>#</th><th>Descripción</th><th>Subpartida</th>
                <th className="num">CIF</th><th className="num">Tributos (normal)</th>
                <th className="num">Con preferencia</th><th className="num">Ahorro</th>
              </tr>
            </thead>
            <tbody>
              {quote.items.map((it) => (
                <tr key={it.id}>
                  <td>{it.line_no}</td>
                  <td>{it.description || "—"}
                    {!it.tax_complete ? <span className="pill warn" style={{ marginLeft: 6 }}>incompleta</span> : null}
                  </td>
                  <td className="mono">
                    {it.hs_code || "—"}
                    {it.hs_validation === "NOT_FOUND" ? <span className="pill crit" style={{ marginLeft: 4 }}>no en maestro</span> : null}
                  </td>
                  <td className="num">{fmt(it.cif_value)}</td>
                  <td className="num">{fmt(it.taxes_total)}</td>
                  <td className="num">
                    {it.preference ? fmt(it.preference.preferential_taxes) : "—"}
                    {it.preference ? (
                      <div style={{ fontSize: 10.5, color: "var(--muted-2)" }}>
                        {it.preference.agreement_code} · {it.preference.certificate_present ? "aplicable" : "potencial"}
                      </div>
                    ) : null}
                  </td>
                  <td className="num">{it.preference ? fmt(it.preference.savings) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {withPref.length ? (
          <div style={{ marginTop: 14, padding: "12px 16px", borderRadius: 10, background: "rgba(45,212,191,0.08)", border: "1px solid rgba(45,212,191,0.35)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <b>Escenario con preferencia arancelaria</b>
              <span className={`pill ${applied ? "ok" : "warn"}`}>{applied ? "APLICABLE (certificado presentado)" : "POTENCIAL (requiere certificado)"}</span>
            </div>
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
              Tributos con preferencia <b>{fmt(prefTotal)}</b> · ahorro estimado <b>{fmt(savings)}</b>{" "}
              vs. tributos normales de esos ítems ({fmt(prefNormal)}).
            </div>
          </div>
        ) : null}
      </div>

      <div className="card rise section-gap">
        <div className="head"><h2>Resumen</h2></div>
        <table className="tbl" style={{ width: "100%", maxWidth: 480 }}>
          <tbody>
            <tr><td>Valor mercancía (CIF)</td><td className="num">{fmt(quote.total_cif)}</td></tr>
            <tr><td>Tributos estimados (normal)</td><td className="num">{fmt(quote.total_taxes)}</td></tr>
            <tr><td>Servicios y gastos</td><td className="num">{fmt(quote.customer_price_total)}</td></tr>
            <tr style={{ fontWeight: 700 }}><td>Costo total (landed)</td><td className="num">{fmt(quote.landed_cost_total)}</td></tr>
          </tbody>
        </table>
      </div>

      <CertificatesPanel quoteId={quote.id} certificates={certificates} />
    </>
  );
}
