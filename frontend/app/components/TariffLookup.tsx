"use client";

import { useState } from "react";

import { tariffCalculate, tariffDetail, tariffHistory } from "@/app/lib/actions";
import { SubpartidaInput } from "@/app/components/SubpartidaInput";

interface Tax { tax_type: string; percentage: string | number | null; verified: boolean; legal_source?: string | null }
interface CodeRef { code: string; description: string; ad_valorem?: string | number | null }
interface Detail {
  code: string; full_description?: string | null; description: string; physical_unit?: string | null;
  taxes: Tax[]; warnings: string[]; ancestors?: CodeRef[]; children?: CodeRef[];
}
interface HistoryRow {
  version: string | null; status: string; verification_status: string;
  ad_valorem: string | number | null; effective_from: string; effective_to: string | null;
}
interface CalcComp { tax_type: string; amount: number; rate_applied: number | null; verified: boolean }
interface Pref {
  agreement_code: string; agreement_name: string; liberation_pct: number;
  preferential_adval_pct: number; requires_certificate: boolean; verified: boolean;
  total_taxes: number; savings: number;
}
interface Calc {
  total_cif: number; total_taxes: number; complete: boolean; data_version: string | null;
  items: { components: CalcComp[]; warnings: string[]; missing_information: string[]; hs_validation: string; preference: Pref | null }[];
}

export function TariffLookup() {
  const [hs, setHs] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [fob, setFob] = useState("1000");
  const [origin, setOrigin] = useState("");
  const [cc, setCc] = useState("");
  const [calc, setCalc] = useState<Calc | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadDetail(code: string) {
    setBusy(true);
    setCalc(null);
    setHistory([]);
    try {
      const d = (await tariffDetail(code)) as Detail | null;
      setDetail(d);
      setNotFound(d === null);
      if (d) {
        setHs(d.code);
        setHistory((await tariffHistory(d.code)) as HistoryRow[]);
      }
    } finally {
      setBusy(false);
    }
  }

  async function runCalc() {
    if (!hs) return;
    setBusy(true);
    try {
      const c = (await tariffCalculate({
        items: [{
          hs_code: hs, invoice_value: Number(fob) || 0,
          origin_country: origin.trim().toUpperCase() || null,
          attributes: cc.trim() ? { CC: Number(cc) } : {},
        }],
      })) as Calc | null;
      setCalc(c);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <style>{`.tx-tbl td,.tx-tbl th{padding:6px 10px;border-bottom:1px solid var(--border);font-size:13px;text-align:left}`}</style>
      <div className="card rise section-gap">
        <div className="head"><h2>Consultar subpartida</h2></div>
        <div style={{ maxWidth: 460 }}>
          <SubpartidaInput
            value={hs}
            onChange={(v) => setHs(v)}
            onPick={(s) => loadDetail(s.code)}
            placeholder="Escribe descripción o código (p. ej. 8471 o 'portátil')"
          />
        </div>
        {hs && !detail ? (
          <button className="btn ghost" style={{ marginTop: 10 }} disabled={busy} onClick={() => loadDetail(hs)}>
            Consultar {hs}
          </button>
        ) : null}
      </div>

      {notFound ? (
        <div className="blocker-banner section-gap" style={{ borderColor: "rgba(248,113,113,0.4)", color: "var(--muted)" }}>
          La subpartida <b>{hs}</b> no está en el maestro arancelario vigente. Verifica el código.
          <b> No se asume 0%</b>: no hay dato para esa subpartida.
        </div>
      ) : null}

      {detail ? (
        <div className="card rise section-gap">
          <div className="head">
            <h2><span className="mono">{detail.code}</span></h2>
            {detail.physical_unit ? <span className="count">UF: {detail.physical_unit}</span> : null}
          </div>
          {detail.ancestors && detail.ancestors.length ? (
            <div style={{ fontSize: 12, color: "var(--muted-2)", marginBottom: 4 }}>
              {detail.ancestors.map((a) => (
                <span key={a.code}>
                  <span className="mono">{a.code}</span> {a.description}{" › "}
                </span>
              ))}
            </div>
          ) : null}
          <p style={{ color: "var(--muted)" }}>{detail.description || detail.full_description}</p>
          <table className="tx-tbl" style={{ width: "100%", marginTop: 8 }}>
            <thead><tr><th>Tributo</th><th>Tarifa</th><th>Estado</th><th>Base legal</th></tr></thead>
            <tbody>
              {detail.taxes.map((t) => (
                <tr key={t.tax_type}>
                  <td className="mono">{t.tax_type}</td>
                  <td>{t.percentage != null ? `${t.percentage}%` : "—"}</td>
                  <td>
                    <span className={`pill ${t.verified ? "ok" : "warn"}`}>
                      {t.verified ? "verificado" : "sin verificar"}
                    </span>
                  </td>
                  <td style={{ color: "var(--muted-2)", fontSize: 12 }}>{t.legal_source || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {detail.warnings?.length ? (
            <div style={{ marginTop: 10, color: "var(--warn, #b45309)", fontSize: 12.5 }}>
              {detail.warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
            </div>
          ) : null}

          {detail.children && detail.children.length ? (
            <div style={{ marginTop: 14 }}>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Subpartidas hijas</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {detail.children.map((c) => (
                  <button
                    key={c.code}
                    type="button"
                    className="btn ghost"
                    style={{ fontSize: 11.5 }}
                    onClick={() => loadDetail(c.code)}
                  >
                    <span className="mono">{c.code}</span> {c.description.slice(0, 26)}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {history.length ? (
            <div style={{ marginTop: 16 }}>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Historial de Ad-Valorem</div>
              <table className="tx-tbl" style={{ width: "100%" }}>
                <thead><tr><th>Versión</th><th>Tarifa</th><th>Vigencia</th><th>Estado</th></tr></thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={i}>
                      <td className="mono">{h.version || "—"}</td>
                      <td>{h.ad_valorem != null ? `${h.ad_valorem}%` : "—"}</td>
                      <td style={{ fontSize: 12 }}>
                        {h.effective_from}{h.effective_to ? ` → ${h.effective_to}` : " → vigente"}
                      </td>
                      <td><span className={`pill ${h.status === "ACTIVE" ? "ok" : ""}`}>{h.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          <div className="form-row" style={{ marginTop: 16, alignItems: "flex-end", gap: 10 }}>
            <label className="field"><span>Valor FOB (USD)</span>
              <input value={fob} onChange={(e) => setFob(e.target.value)} style={{ width: 120 }} />
            </label>
            <label className="field"><span>País de origen (ISO2)</span>
              <input value={origin} placeholder="p. ej. CO, CN, PE" maxLength={2}
                onChange={(e) => setOrigin(e.target.value)} style={{ width: 110 }} />
            </label>
            <label className="field"><span>Cilindraje cc (opc.)</span>
              <input value={cc} placeholder="vehículos" onChange={(e) => setCc(e.target.value)} style={{ width: 100 }} />
            </label>
            <button className="btn" disabled={busy} onClick={runCalc}>Calcular tributos</button>
          </div>
        </div>
      ) : null}

      {calc ? (
        <div className="card rise">
          <div className="head">
            <h2>Estimación de tributos</h2>
            <span className={`pill ${calc.complete ? "ok" : "warn"}`}>
              {calc.complete ? "completa" : "INCOMPLETA"}
            </span>
          </div>
          {calc.data_version ? (
            <div style={{ color: "var(--muted-2)", fontSize: 12 }}>Versión arancelaria: {calc.data_version}</div>
          ) : null}
          <table className="tx-tbl" style={{ width: "100%", marginTop: 8 }}>
            <tbody>
              {calc.items[0]?.components.map((c) => (
                <tr key={c.tax_type}>
                  <td className="mono">{c.tax_type}</td>
                  <td>{c.rate_applied != null ? `${c.rate_applied}%` : ""}</td>
                  <td style={{ textAlign: "right" }}>${c.amount.toFixed(2)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700 }}>
                <td>Total tributos</td><td></td>
                <td style={{ textAlign: "right" }}>${calc.total_taxes.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
          {!calc.complete ? (
            <div className="blocker-banner" style={{ marginTop: 12, borderColor: "rgba(180,83,9,0.4)", color: "var(--muted)" }}>
              <b>Estimación tributaria incompleta.</b> Falta información arancelaria verificada.
              {calc.items[0]?.warnings.map((w, i) => <div key={i} style={{ fontSize: 12, marginTop: 4 }}>⚠ {w}</div>)}
            </div>
          ) : null}

          {calc.items[0]?.preference ? (
            <div style={{ marginTop: 14, padding: "12px 16px", borderRadius: 10, background: "rgba(45,212,191,0.08)", border: "1px solid rgba(45,212,191,0.35)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <b>Con preferencia potencial · {calc.items[0].preference.agreement_name}</b>
                <span className="pill accent">ahorro ${calc.items[0].preference.savings.toFixed(2)}</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
                Ad-Valorem preferencial <b>{calc.items[0].preference.preferential_adval_pct}%</b>
                {" "}(liberación {calc.items[0].preference.liberation_pct}%) → total tributos{" "}
                <b>${calc.items[0].preference.total_taxes.toFixed(2)}</b>.
              </div>
              <div style={{ fontSize: 12, color: "var(--muted-2)", marginTop: 6 }}>
                {calc.items[0].preference.requires_certificate
                  ? "⚠ Requiere certificado de origen válido para aplicarse. Escenario estimado."
                  : "Sin requisito de certificado."}
                {!calc.items[0].preference.verified ? " · Preferencia sin verificar (revisar excepciones)." : ""}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
