"use client";

import { useState } from "react";

import { tariffCalculate, tariffDetail } from "@/app/lib/actions";
import { SubpartidaInput } from "@/app/components/SubpartidaInput";

interface Tax { tax_type: string; percentage: string | number | null; verified: boolean; legal_source?: string | null }
interface Detail { code: string; full_description?: string | null; description: string; physical_unit?: string | null; taxes: Tax[]; warnings: string[] }
interface CalcComp { tax_type: string; amount: number; rate_applied: number | null; verified: boolean }
interface Calc { total_cif: number; total_taxes: number; complete: boolean; data_version: string | null; items: { components: CalcComp[]; warnings: string[]; missing_information: string[]; hs_validation: string }[] }

export function TariffLookup() {
  const [hs, setHs] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [fob, setFob] = useState("1000");
  const [calc, setCalc] = useState<Calc | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadDetail(code: string) {
    setBusy(true);
    setCalc(null);
    try {
      const d = (await tariffDetail(code)) as Detail | null;
      setDetail(d);
      setNotFound(d === null);
    } finally {
      setBusy(false);
    }
  }

  async function runCalc() {
    if (!hs) return;
    setBusy(true);
    try {
      const c = (await tariffCalculate({
        items: [{ hs_code: hs, invoice_value: Number(fob) || 0 }],
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
          <p style={{ color: "var(--muted)" }}>{detail.full_description || detail.description}</p>
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

          <div className="form-row" style={{ marginTop: 16, alignItems: "flex-end", gap: 10 }}>
            <label className="field"><span>Valor FOB (USD)</span>
              <input value={fob} onChange={(e) => setFob(e.target.value)} style={{ width: 120 }} />
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
        </div>
      ) : null}
    </>
  );
}
