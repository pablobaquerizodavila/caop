"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { authorizeRetention, createRetention, getRetentionXml } from "@/app/lib/actions";
import { einvoiceStatusClass, money, type Retention } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

const ID_TYPES = [
  { v: "04", label: "RUC" },
  { v: "05", label: "Cédula" },
  { v: "06", label: "Pasaporte" },
];
const TAX_TYPES = [
  { v: "1", label: "Renta" },
  { v: "2", label: "IVA" },
];

interface LineForm {
  tax_type: string;
  codigo_retencion: string;
  base_imponible: string;
  percentage: string;
}

const today = () => new Date().toISOString().slice(0, 10);

export function RetentionsManager({ retentions }: { retentions: Retention[] }) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [h, setH] = useState({
    subject_name: "", subject_id: "", subject_id_type: "04",
    period: "", doc_sustento_number: "", doc_sustento_date: today(),
  });
  const [lines, setLines] = useState<LineForm[]>([
    { tax_type: "2", codigo_retencion: "", base_imponible: "0", percentage: "0" },
  ]);

  const setLine = (i: number, k: keyof LineForm, v: string) =>
    setLines((p) => p.map((l, idx) => (idx === i ? { ...l, [k]: v } : l)));

  async function act(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setBusy(true);
    try {
      const r = await fn();
      if (!r.ok) alert(r.error ?? "No se pudo completar");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function create() {
    if (!h.subject_name || !h.subject_id || !h.period || !h.doc_sustento_number) {
      return alert("Completa sujeto, período y documento de sustento");
    }
    await act(() => createRetention({
      ...h,
      lines: lines.map((l) => ({
        tax_type: l.tax_type, codigo_retencion: l.codigo_retencion,
        base_imponible: Number(l.base_imponible) || 0, percentage: Number(l.percentage) || 0,
      })),
    }));
    setOpen(false);
    setH({ subject_name: "", subject_id: "", subject_id_type: "04", period: "", doc_sustento_number: "", doc_sustento_date: today() });
    setLines([{ tax_type: "2", codigo_retencion: "", base_imponible: "0", percentage: "0" }]);
  }

  async function xml(r: Retention) {
    setBusy(true);
    try {
      const txt = await getRetentionXml(r.id);
      if (!txt) return alert("No se pudo obtener el XML");
      const blob = new Blob([txt], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${r.access_key}.xml`; a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {canWrite ? (
        <div className="card rise section-gap">
          <div className="head">
            <h2>Nueva retención</h2>
            <button className="btn ghost" onClick={() => setOpen((o) => !o)}>{open ? "Cerrar" : "Emitir retención"}</button>
          </div>
          {open ? (
            <div className="card-pad stack">
              <div className="grid-2">
                <label className="field"><span>Razón social del sujeto retenido</span>
                  <input value={h.subject_name} onChange={(e) => setH((p) => ({ ...p, subject_name: e.target.value }))} /></label>
                <label className="field"><span>Identificación</span>
                  <input className="mono" value={h.subject_id} onChange={(e) => setH((p) => ({ ...p, subject_id: e.target.value }))} /></label>
                <label className="field"><span>Tipo ID</span>
                  <select value={h.subject_id_type} onChange={(e) => setH((p) => ({ ...p, subject_id_type: e.target.value }))}>
                    {ID_TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
                  </select></label>
                <label className="field"><span>Período fiscal (MM/AAAA)</span>
                  <input className="mono" placeholder="08/2026" value={h.period} onChange={(e) => setH((p) => ({ ...p, period: e.target.value }))} /></label>
                <label className="field"><span>Doc. sustento (001-001-000000001)</span>
                  <input className="mono" value={h.doc_sustento_number} onChange={(e) => setH((p) => ({ ...p, doc_sustento_number: e.target.value }))} /></label>
                <label className="field"><span>Fecha del documento</span>
                  <input type="date" value={h.doc_sustento_date} onChange={(e) => setH((p) => ({ ...p, doc_sustento_date: e.target.value }))} /></label>
              </div>

              <div className="subhead"><h3>Líneas de retención</h3>
                <button type="button" className="btn ghost" onClick={() => setLines((p) => [...p, { tax_type: "1", codigo_retencion: "", base_imponible: "0", percentage: "0" }])}>+ Línea</button>
              </div>
              {lines.map((l, i) => {
                const val = ((Number(l.base_imponible) || 0) * (Number(l.percentage) || 0) / 100).toFixed(2);
                return (
                  <div className="form-row" key={i} style={{ flexWrap: "wrap", paddingLeft: 0 }}>
                    <select value={l.tax_type} onChange={(e) => setLine(i, "tax_type", e.target.value)}>
                      {TAX_TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
                    </select>
                    <input type="text" placeholder="Cód. retención" value={l.codigo_retencion} onChange={(e) => setLine(i, "codigo_retencion", e.target.value)} style={{ width: 110 }} />
                    <input type="text" placeholder="Base" value={l.base_imponible} onChange={(e) => setLine(i, "base_imponible", e.target.value)} style={{ width: 90 }} />
                    <input type="text" placeholder="%" value={l.percentage} onChange={(e) => setLine(i, "percentage", e.target.value)} style={{ width: 60 }} />
                    <span className="tag mono">= {val}</span>
                    {lines.length > 1 ? <button type="button" className="btn ghost" onClick={() => setLines((p) => p.filter((_, idx) => idx !== i))}>✕</button> : null}
                  </div>
                );
              })}
              <div><button className="btn" disabled={busy} onClick={create}>Emitir</button></div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="card rise">
        <div className="head"><h2>Retenciones</h2><span className="count">{retentions.length}</span></div>
        {retentions.length === 0 ? (
          <div className="empty">Sin retenciones emitidas.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr><th>N.º</th><th>Sujeto retenido</th><th>Período</th><th className="num">Retenido</th><th>Estado</th><th></th></tr>
              </thead>
              <tbody>
                {retentions.map((r) => (
                  <tr key={r.id}>
                    <td className="mono" style={{ fontSize: 12 }}>{r.estab}-{r.pto_emi}-{r.secuencial}</td>
                    <td>{r.subject_name}<div className="tag mono">{r.subject_id}</div></td>
                    <td className="mono">{r.period}</td>
                    <td className="num">{money(r.total_retained)}</td>
                    <td><span className={`pill ${einvoiceStatusClass(r.status)}`}>{r.status}</span></td>
                    <td>
                      <div className="actions">
                        {r.status !== "AUTHORIZED" && canWrite ? (
                          <button className="btn" disabled={busy} onClick={() => act(() => authorizeRetention(r.id, "AUTHORIZE"))}>Autorizar</button>
                        ) : null}
                        <button className="btn ghost" disabled={busy} onClick={() => xml(r)}>XML</button>
                      </div>
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
