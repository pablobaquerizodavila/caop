"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { createTariffTier, deleteTariffTier } from "@/app/lib/actions";

interface TierRow { min?: number | null; max?: number | null; adval_pct?: number | null; specific_rate?: number | null }
interface Tier {
  id: string; hs_prefix: string; applies_to: string; attribute: string;
  description?: string | null; tiers: TierRow[]; verification_status: string;
}

const ATTRS = ["CC", "UNIT_VALUE", "WEIGHT", "QUANTITY"];

export function TariffTierAdmin({ tiers }: { tiers: Tier[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [head, setHead] = useState({
    hs_prefix: "", applies_to: "AD_VALOREM", attribute: "CC", description: "", effective_from: "",
  });
  const [rows, setRows] = useState<{ min: string; max: string; adval_pct: string; specific_rate: string }[]>([
    { min: "", max: "", adval_pct: "", specific_rate: "" },
  ]);

  const setRow = (i: number, k: string, v: string) =>
    setRows((p) => p.map((r, idx) => (idx === i ? { ...r, [k]: v } : r)));

  async function add() {
    if (!head.hs_prefix.trim() || !head.effective_from) { alert("Indica prefijo HS y vigencia."); return; }
    const tierRows = rows
      .filter((r) => r.min || r.max || r.adval_pct || r.specific_rate)
      .map((r) => ({
        min: r.min ? Number(r.min) : null, max: r.max ? Number(r.max) : null,
        adval_pct: r.adval_pct ? Number(r.adval_pct) : null,
        specific_rate: r.specific_rate ? Number(r.specific_rate) : null,
      }));
    if (!tierRows.length) { alert("Agrega al menos un tramo."); return; }
    setBusy(true);
    try {
      const r = await createTariffTier({
        hs_prefix: head.hs_prefix.trim(), applies_to: head.applies_to, attribute: head.attribute,
        description: head.description || null, tiers: tierRows, effective_from: head.effective_from,
      });
      if (!r.ok) { alert(r.error); return; }
      setHead({ ...head, hs_prefix: "", description: "" });
      setRows([{ min: "", max: "", adval_pct: "", specific_rate: "" }]);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("¿Eliminar esta tarifa por tramos?")) return;
    setBusy(true);
    try { await deleteTariffTier(id); router.refresh(); }
    finally { setBusy(false); }
  }

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Tarifas por tramos (vehículos / condicionales)</h2>
        <span className="count">{tiers.length}</span>
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Ad-Valorem o ICE que depende de un atributo del ítem (cilindraje, valor unitario, peso).
        Se elige el tramo donde <b>min ≤ valor &lt; max</b>. Requiere que el ítem traiga el atributo.
      </p>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
        <label className="field"><span>Prefijo HS</span><input value={head.hs_prefix} placeholder="p. ej. 8703" onChange={(e) => setHead((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 110 }} /></label>
        <label className="field"><span>Aplica a</span>
          <select value={head.applies_to} onChange={(e) => setHead((p) => ({ ...p, applies_to: e.target.value }))}>
            <option value="AD_VALOREM">Ad-Valorem</option><option value="ICE">ICE</option>
          </select>
        </label>
        <label className="field"><span>Atributo</span>
          <select value={head.attribute} onChange={(e) => setHead((p) => ({ ...p, attribute: e.target.value }))}>
            {ATTRS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        <label className="field" style={{ minWidth: 160 }}><span>Descripción</span><input value={head.description} onChange={(e) => setHead((p) => ({ ...p, description: e.target.value }))} /></label>
        <label className="field"><span>Vigente desde</span><input type="date" value={head.effective_from} onChange={(e) => setHead((p) => ({ ...p, effective_from: e.target.value }))} /></label>
      </div>

      <div style={{ marginTop: 8 }}>
        <div className="eyebrow" style={{ marginBottom: 4 }}>Tramos</div>
        {rows.map((r, i) => (
          <div key={i} className="form-row" style={{ alignItems: "flex-end", gap: 8, marginBottom: 4 }}>
            <label className="field"><span>Min</span><input value={r.min} onChange={(e) => setRow(i, "min", e.target.value)} style={{ width: 90 }} /></label>
            <label className="field"><span>Max</span><input value={r.max} onChange={(e) => setRow(i, "max", e.target.value)} style={{ width: 90 }} /></label>
            <label className="field"><span>Ad-Val %</span><input value={r.adval_pct} onChange={(e) => setRow(i, "adval_pct", e.target.value)} style={{ width: 80 }} /></label>
            <label className="field"><span>Específico/u</span><input value={r.specific_rate} onChange={(e) => setRow(i, "specific_rate", e.target.value)} style={{ width: 90 }} /></label>
            <button className="btn ghost" onClick={() => setRows((p) => p.filter((_, idx) => idx !== i))} disabled={rows.length === 1}>✕</button>
          </div>
        ))}
        <button className="btn ghost" onClick={() => setRows((p) => [...p, { min: "", max: "", adval_pct: "", specific_rate: "" }])}>+ Tramo</button>
        <button className="btn" disabled={busy || !head.hs_prefix.trim()} onClick={add} style={{ marginLeft: 8 }}>Guardar tarifa</button>
      </div>

      {tiers.length ? (
        <div style={{ marginTop: 14, overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead><tr><th>Prefijo</th><th>Aplica</th><th>Atributo</th><th>Tramos</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {tiers.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.hs_prefix}</td>
                  <td>{t.applies_to}</td>
                  <td>{t.attribute}</td>
                  <td style={{ fontSize: 11.5 }}>
                    {(t.tiers || []).map((r, i) => (
                      <div key={i}>{r.min ?? "−∞"}–{r.max ?? "∞"}: {r.adval_pct != null ? `${r.adval_pct}%` : `${r.specific_rate}/u`}</div>
                    ))}
                  </td>
                  <td><span className={`pill ${t.verification_status === "VERIFIED" ? "ok" : "warn"}`}>{t.verification_status}</span></td>
                  <td><button className="btn ghost" disabled={busy} onClick={() => remove(t.id)}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
