"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createBandPeriod,
  createPriceBand,
  deleteBandPeriod,
  deletePriceBand,
  listBandPeriods,
} from "@/app/lib/actions";

interface Measure { id: string; hs_prefix: string; product: string; is_marker: boolean }
interface Period {
  id: string; period_start: string; period_end: string; reference_price?: string | number | null;
  floor_price?: string | number | null; ceiling_price?: string | number | null;
  variable_method: string; variable_value: string | number; verification_status: string;
}

function MeasureRow({ m }: { m: Measure }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [busy, setBusy] = useState(false);
  const [np, setNp] = useState({
    period_start: "", period_end: "", reference_price: "", floor_price: "", ceiling_price: "",
    variable_method: "AD_VALOREM", variable_value: "",
  });

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) setPeriods((await listBandPeriods(m.id)) as Period[]);
  }

  async function addPeriod() {
    if (!np.period_start || !np.period_end) { alert("Indica el periodo (desde/hasta)."); return; }
    setBusy(true);
    try {
      const r = await createBandPeriod(m.id, {
        period_start: np.period_start, period_end: np.period_end,
        reference_price: np.reference_price ? Number(np.reference_price) : null,
        floor_price: np.floor_price ? Number(np.floor_price) : null,
        ceiling_price: np.ceiling_price ? Number(np.ceiling_price) : null,
        variable_method: np.variable_method, variable_value: Number(np.variable_value) || 0,
      });
      if (!r.ok) { alert(r.error); return; }
      setNp({ ...np, reference_price: "", floor_price: "", ceiling_price: "", variable_value: "" });
      setPeriods((await listBandPeriods(m.id)) as Period[]);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function removePeriod(id: string) {
    setBusy(true);
    try { await deleteBandPeriod(id); setPeriods((await listBandPeriods(m.id)) as Period[]); router.refresh(); }
    finally { setBusy(false); }
  }

  async function removeMeasure() {
    if (!confirm(`¿Eliminar la franja de ${m.product} y sus periodos?`)) return;
    setBusy(true);
    try { await deletePriceBand(m.id); router.refresh(); }
    finally { setBusy(false); }
  }

  return (
    <>
      <tr>
        <td className="mono">{m.hs_prefix}</td>
        <td>{m.product}</td>
        <td>{m.is_marker ? "marcador" : "vinculado"}</td>
        <td>
          <div className="actions">
            <button className="btn ghost" onClick={toggle}>{open ? "Cerrar" : "Periodos"}</button>
            <button className="btn ghost" disabled={busy} onClick={removeMeasure}>✕</button>
          </div>
        </td>
      </tr>
      {open ? (
        <tr>
          <td colSpan={4} style={{ background: "var(--surface-2)" }}>
            <div style={{ padding: "10px 4px" }}>
              <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 8 }}>
                <label className="field"><span>Desde</span><input type="date" value={np.period_start} onChange={(e) => setNp((p) => ({ ...p, period_start: e.target.value }))} /></label>
                <label className="field"><span>Hasta</span><input type="date" value={np.period_end} onChange={(e) => setNp((p) => ({ ...p, period_end: e.target.value }))} /></label>
                <label className="field"><span>P. ref.</span><input value={np.reference_price} style={{ width: 80 }} onChange={(e) => setNp((p) => ({ ...p, reference_price: e.target.value }))} /></label>
                <label className="field"><span>Piso</span><input value={np.floor_price} style={{ width: 80 }} onChange={(e) => setNp((p) => ({ ...p, floor_price: e.target.value }))} /></label>
                <label className="field"><span>Techo</span><input value={np.ceiling_price} style={{ width: 80 }} onChange={(e) => setNp((p) => ({ ...p, ceiling_price: e.target.value }))} /></label>
                <label className="field"><span>Método</span>
                  <select value={np.variable_method} onChange={(e) => setNp((p) => ({ ...p, variable_method: e.target.value }))}>
                    <option value="AD_VALOREM">Ad valorem %</option>
                    <option value="SPECIFIC">Específico/unidad</option>
                  </select>
                </label>
                <label className="field"><span>Derecho variable (±)</span><input value={np.variable_value} style={{ width: 100 }} onChange={(e) => setNp((p) => ({ ...p, variable_value: e.target.value }))} /></label>
                <button className="btn" disabled={busy} onClick={addPeriod}>Agregar periodo</button>
              </div>
              {periods.length ? (
                <table className="tbl" style={{ width: "100%", marginTop: 8 }}>
                  <thead><tr><th>Periodo</th><th className="num">P.ref</th><th className="num">Piso</th><th className="num">Techo</th><th className="num">Derecho</th><th></th></tr></thead>
                  <tbody>
                    {periods.map((p) => (
                      <tr key={p.id}>
                        <td style={{ fontSize: 12 }}>{p.period_start} → {p.period_end}</td>
                        <td className="num">{p.reference_price ?? "—"}</td>
                        <td className="num">{p.floor_price ?? "—"}</td>
                        <td className="num">{p.ceiling_price ?? "—"}</td>
                        <td className="num">{String(p.variable_value)}{p.variable_method === "AD_VALOREM" ? "%" : "/u"}</td>
                        <td><button className="btn ghost" disabled={busy} onClick={() => removePeriod(p.id)}>✕</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="empty" style={{ marginTop: 8 }}>Sin periodos cargados.</div>}
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function PriceBandAdmin({ measures }: { measures: Measure[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [nm, setNm] = useState({ hs_prefix: "", product: "", is_marker: false });

  async function add() {
    if (!nm.hs_prefix.trim() || !nm.product.trim()) { alert("Indica prefijo HS y producto."); return; }
    setBusy(true);
    try {
      const r = await createPriceBand({ hs_prefix: nm.hs_prefix.trim(), product: nm.product.trim(), is_marker: nm.is_marker });
      if (!r.ok) { alert(r.error); return; }
      setNm({ hs_prefix: "", product: "", is_marker: false });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Franja de precios (SAFP)</h2><span className="count">{measures.length}</span></div>
      <p style={{ color: "var(--muted)", fontSize: 12.5 }}>
        Productos sujetos al Sistema Andino de Franja de Precios. Carga el derecho variable
        publicado por la CAN por periodo (quincenal). Sin periodo vigente → estimación incompleta.
      </p>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
        <label className="field"><span>Prefijo HS</span><input value={nm.hs_prefix} placeholder="p. ej. 1511" onChange={(e) => setNm((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 110 }} /></label>
        <label className="field" style={{ minWidth: 200 }}><span>Producto</span><input value={nm.product} placeholder="p. ej. Aceite crudo de palma" onChange={(e) => setNm((p) => ({ ...p, product: e.target.value }))} /></label>
        <label className="field" style={{ alignItems: "center" }}><span>Marcador</span><input type="checkbox" checked={nm.is_marker} onChange={(e) => setNm((p) => ({ ...p, is_marker: e.target.checked }))} /></label>
        <button className="btn" disabled={busy || !nm.hs_prefix.trim()} onClick={add}>Agregar producto</button>
      </div>
      {measures.length ? (
        <div style={{ marginTop: 14, overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead><tr><th>Prefijo</th><th>Producto</th><th>Tipo</th><th></th></tr></thead>
            <tbody>{measures.map((m) => <MeasureRow key={m.id} m={m} />)}</tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
