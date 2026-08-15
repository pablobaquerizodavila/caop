"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { setReconciliation } from "@/app/lib/actions";

export interface RecData {
  estimated: Record<string, number>;
  estimated_total: number;
  actual: Record<string, number> | null;
  actual_total: number | null;
  difference: number | null;
  difference_pct: number | null;
  reason: string | null;
  recorded_at: string | null;
}

const ORDER = ["AD_VALOREM", "FODINFA", "ICE", "SAFEGUARD", "ANTIDUMPING", "IVA"];

export function ReconciliationPanel({ caseId, data }: { caseId: string; data: RecData }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const types = Array.from(
    new Set([...ORDER.filter((t) => t in data.estimated), ...Object.keys(data.estimated),
             ...Object.keys(data.actual ?? {})]),
  );
  const [actual, setActual] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const t of types) {
      const v = data.actual?.[t] ?? data.estimated[t] ?? 0;
      init[t] = String(v);
    }
    return init;
  });
  const [reason, setReason] = useState(data.reason ?? "");

  const money = (v: number) => `$${v.toFixed(2)}`;
  const actualTotal = Object.values(actual).reduce((s, v) => s + (Number(v) || 0), 0);
  const diff = actualTotal - data.estimated_total;
  const diffPct = data.estimated_total ? (diff / data.estimated_total) * 100 : 0;

  async function save() {
    setBusy(true);
    try {
      const payload: Record<string, number> = {};
      for (const [k, v] of Object.entries(actual)) payload[k] = Number(v) || 0;
      const r = await setReconciliation(caseId, payload, reason);
      if (!r.ok) alert(r.error ?? "No se pudo guardar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card rise section-gap">
      <div className="head">
        <h2>Reconciliación tributaria</h2>
        {data.recorded_at ? <span className="count">registrada</span> : null}
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Compara el <b>estimado del motor</b> (de la cotización) con la <b>liquidación real</b> de
        SENAE. Ingresa los montos reales por tributo para medir la precisión.
      </p>

      {data.estimated_total === 0 ? (
        <div className="empty">Este expediente no tiene una cotización de origen con tributos estimados.</div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl" style={{ width: "100%", maxWidth: 560 }}>
              <thead>
                <tr><th>Tributo</th><th className="num">Estimado</th><th className="num">Real (SENAE)</th></tr>
              </thead>
              <tbody>
                {types.map((t) => (
                  <tr key={t}>
                    <td className="mono">{t}</td>
                    <td className="num">{money(data.estimated[t] ?? 0)}</td>
                    <td className="num">
                      <input value={actual[t] ?? ""} inputMode="decimal" style={{ width: 100, textAlign: "right" }}
                        onChange={(e) => setActual((p) => ({ ...p, [t]: e.target.value }))} />
                    </td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 700 }}>
                  <td>TOTAL</td>
                  <td className="num">{money(data.estimated_total)}</td>
                  <td className="num">{money(actualTotal)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: 10, fontSize: 13 }}>
            Diferencia: <b style={{ color: Math.abs(diffPct) <= 1 ? "var(--ok, #15803d)" : "var(--warn, #b45309)" }}>
              {money(diff)} ({diffPct.toFixed(2)}%)
            </b>
            {data.recorded_at ? <span style={{ color: "var(--muted-2)" }}> · última: {new Date(data.recorded_at).toLocaleString()}</span> : null}
          </div>

          <div className="form-row" style={{ marginTop: 10, alignItems: "flex-end", gap: 10 }}>
            <label className="field" style={{ flex: 1, minWidth: 220 }}>
              <span>Motivo de la diferencia (opcional)</span>
              <input value={reason} placeholder="p. ej. reclasificación, tipo de cambio, ajuste de base"
                onChange={(e) => setReason(e.target.value)} />
            </label>
            <button className="btn" disabled={busy} onClick={save}>Guardar reconciliación</button>
          </div>
        </>
      )}
    </div>
  );
}
