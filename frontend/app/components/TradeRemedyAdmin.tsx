"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createTradeRemedy, deleteTradeRemedy } from "@/app/lib/actions";

interface Remedy {
  id: string; kind: string; hs_prefix: string; origin_country?: string | null;
  product?: string | null; method: string; ad_valorem_pct?: string | number | null;
  specific_rate?: string | number | null; effective_from: string; effective_to?: string | null;
  verification_status: string;
}

const KINDS: Record<string, string> = {
  ANTIDUMPING: "Antidumping", SAFEGUARD: "Salvaguardia", COMPENSATORY: "Compensatorio",
};

export function TradeRemedyAdmin({ remedies }: { remedies: Remedy[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nr, setNr] = useState({
    kind: "ANTIDUMPING", hs_prefix: "", origin_country: "", product: "",
    method: "AD_VALOREM", ad_valorem_pct: "", specific_rate: "",
    effective_from: "", effective_to: "",
  });

  async function add() {
    if (!nr.hs_prefix.trim() || !nr.effective_from) { alert("Indica prefijo HS y vigencia."); return; }
    setBusy(true);
    try {
      const r = await createTradeRemedy({
        kind: nr.kind, hs_prefix: nr.hs_prefix.trim(),
        origin_country: nr.origin_country.trim().toUpperCase() || null,
        product: nr.product || null, method: nr.method,
        ad_valorem_pct: nr.ad_valorem_pct ? Number(nr.ad_valorem_pct) : null,
        specific_rate: nr.specific_rate ? Number(nr.specific_rate) : null,
        effective_from: nr.effective_from, effective_to: nr.effective_to || null,
      });
      if (!r.ok) { alert(r.error); return; }
      setNr({ ...nr, hs_prefix: "", origin_country: "", product: "", ad_valorem_pct: "", specific_rate: "" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("¿Eliminar esta medida?")) return;
    setBusy(true);
    try { await deleteTradeRemedy(id); router.refresh(); }
    finally { setBusy(false); }
  }

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Defensa comercial (antidumping / salvaguardia)</h2>
        <span className="count">{remedies.length}</span>
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Derechos adicionales por resolución COMEX. Antidumping suele ser por país de origen;
        salvaguardia normalmente aplica a todo origen. Carga las tarifas oficiales vigentes.
      </p>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
        <label className="field"><span>Tipo</span>
          <select value={nr.kind} onChange={(e) => setNr((p) => ({ ...p, kind: e.target.value }))}>
            {Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="field"><span>Prefijo HS</span>
          <input value={nr.hs_prefix} onChange={(e) => setNr((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 110 }} />
        </label>
        <label className="field"><span>Origen (ISO2)</span>
          <input value={nr.origin_country} maxLength={2} placeholder="todos"
            onChange={(e) => setNr((p) => ({ ...p, origin_country: e.target.value }))} style={{ width: 90 }} />
        </label>
        <label className="field"><span>Método</span>
          <select value={nr.method} onChange={(e) => setNr((p) => ({ ...p, method: e.target.value }))}>
            <option value="AD_VALOREM">Ad valorem % (CIF)</option>
            <option value="SPECIFIC">Específico/unidad</option>
          </select>
        </label>
        <label className="field"><span>% Ad valorem</span>
          <input value={nr.ad_valorem_pct} onChange={(e) => setNr((p) => ({ ...p, ad_valorem_pct: e.target.value }))} style={{ width: 80 }} />
        </label>
        <label className="field"><span>Tarifa específica</span>
          <input value={nr.specific_rate} onChange={(e) => setNr((p) => ({ ...p, specific_rate: e.target.value }))} style={{ width: 90 }} />
        </label>
        <label className="field"><span>Desde</span>
          <input type="date" value={nr.effective_from} onChange={(e) => setNr((p) => ({ ...p, effective_from: e.target.value }))} />
        </label>
        <label className="field"><span>Hasta</span>
          <input type="date" value={nr.effective_to} onChange={(e) => setNr((p) => ({ ...p, effective_to: e.target.value }))} />
        </label>
        <button className="btn" disabled={busy || !nr.hs_prefix.trim()} onClick={add}>Agregar</button>
      </div>

      {remedies.length ? (
        <div style={{ marginTop: 14, overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead><tr><th>Tipo</th><th>Prefijo</th><th>Origen</th><th className="num">Tarifa</th>
              <th>Vigencia</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {remedies.map((r) => (
                <tr key={r.id}>
                  <td>{KINDS[r.kind] ?? r.kind}</td>
                  <td className="mono">{r.hs_prefix}</td>
                  <td>{r.origin_country || "todos"}</td>
                  <td className="num">{r.ad_valorem_pct != null ? `${r.ad_valorem_pct}%` : (r.specific_rate != null ? `${r.specific_rate}/u` : "—")}</td>
                  <td style={{ fontSize: 12 }}>{r.effective_from}{r.effective_to ? ` → ${r.effective_to}` : " → vigente"}</td>
                  <td><span className={`pill ${r.verification_status === "VERIFIED" ? "ok" : "warn"}`}>{r.verification_status}</span></td>
                  <td><button className="btn ghost" disabled={busy} onClick={() => remove(r.id)}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
