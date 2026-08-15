"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { authorizeWaybill, createWaybill, getWaybillXml } from "@/app/lib/actions";
import { einvoiceStatusClass, type Waybill } from "@/app/lib/format";
import { useCaps } from "@/app/lib/useCaps";

const ID_TYPES = [
  { v: "04", label: "RUC" },
  { v: "05", label: "Cédula" },
  { v: "06", label: "Pasaporte" },
];
const today = () => new Date().toISOString().slice(0, 10);

interface ItemForm { description: string; quantity: string }

export function WaybillsManager({ waybills }: { waybills: Waybill[] }) {
  const router = useRouter();
  const { canWrite } = useCaps();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [h, setH] = useState({
    transporter_name: "", transporter_id: "", transporter_id_type: "04", placa: "",
    dir_partida: "", fecha_ini_transporte: today(), fecha_fin_transporte: today(),
    dest_name: "", dest_id: "", dest_address: "",
    motivo_traslado: "Entrega de mercancía importada",
    num_doc_sustento: "", fecha_doc_sustento: "",
  });
  const [items, setItems] = useState<ItemForm[]>([{ description: "", quantity: "1" }]);

  const setItem = (i: number, k: keyof ItemForm, v: string) =>
    setItems((p) => p.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

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
    if (!h.transporter_name || !h.transporter_id || !h.placa || !h.dest_name || !h.dest_id) {
      return alert("Completa transportista, placa y destinatario");
    }
    await act(() => createWaybill({
      ...h,
      num_doc_sustento: h.num_doc_sustento || null,
      fecha_doc_sustento: h.fecha_doc_sustento || null,
      items: items.filter((it) => it.description).map((it) => ({
        description: it.description, quantity: Number(it.quantity) || 1,
      })),
    }));
    setOpen(false);
  }

  async function xml(g: Waybill) {
    setBusy(true);
    try {
      const txt = await getWaybillXml(g.id);
      if (!txt) return alert("No se pudo obtener el XML");
      const blob = new Blob([txt], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${g.access_key}.xml`; a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  }

  const field = (label: string, key: keyof typeof h, opts: { type?: string; w?: number } = {}) => (
    <label className="field">
      <span>{label}</span>
      <input type={opts.type ?? "text"} value={h[key]}
        onChange={(e) => setH((p) => ({ ...p, [key]: e.target.value }))}
        style={opts.w ? { width: opts.w } : undefined} />
    </label>
  );

  return (
    <>
      {canWrite ? (
        <div className="card rise section-gap">
          <div className="head">
            <h2>Nueva guía de remisión</h2>
            <button className="btn ghost" onClick={() => setOpen((o) => !o)}>{open ? "Cerrar" : "Emitir guía"}</button>
          </div>
          {open ? (
            <div className="card-pad stack">
              <div className="subhead"><h3>Transportista y ruta</h3></div>
              <div className="grid-2">
                {field("Razón social transportista", "transporter_name")}
                {field("RUC/ID transportista", "transporter_id")}
                <label className="field"><span>Tipo ID</span>
                  <select value={h.transporter_id_type} onChange={(e) => setH((p) => ({ ...p, transporter_id_type: e.target.value }))}>
                    {ID_TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
                  </select></label>
                {field("Placa", "placa")}
                {field("Dirección de partida", "dir_partida")}
                {field("Inicio transporte", "fecha_ini_transporte", { type: "date" })}
                {field("Fin transporte", "fecha_fin_transporte", { type: "date" })}
              </div>

              <div className="subhead"><h3>Destinatario</h3></div>
              <div className="grid-2">
                {field("Razón social destinatario", "dest_name")}
                {field("RUC/ID destinatario", "dest_id")}
                {field("Dirección destinatario", "dest_address")}
                {field("Motivo del traslado", "motivo_traslado")}
                {field("Doc. sustento (opcional)", "num_doc_sustento")}
                {field("Fecha doc. sustento", "fecha_doc_sustento", { type: "date" })}
              </div>

              <div className="subhead"><h3>Ítems</h3>
                <button type="button" className="btn ghost" onClick={() => setItems((p) => [...p, { description: "", quantity: "1" }])}>+ Ítem</button>
              </div>
              {items.map((it, i) => (
                <div className="form-row" key={i} style={{ paddingLeft: 0 }}>
                  <input type="text" placeholder="Descripción" value={it.description} onChange={(e) => setItem(i, "description", e.target.value)} style={{ flex: 1, minWidth: 200 }} />
                  <input type="text" placeholder="Cant." value={it.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} style={{ width: 80 }} />
                  {items.length > 1 ? <button type="button" className="btn ghost" onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}>✕</button> : null}
                </div>
              ))}
              <div><button className="btn" disabled={busy} onClick={create}>Emitir</button></div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="card rise">
        <div className="head"><h2>Guías de remisión</h2><span className="count">{waybills.length}</span></div>
        {waybills.length === 0 ? (
          <div className="empty">Sin guías emitidas.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr><th>N.º</th><th>Destinatario</th><th>Placa</th><th>Transporte</th><th>Estado</th><th></th></tr>
              </thead>
              <tbody>
                {waybills.map((g) => (
                  <tr key={g.id}>
                    <td className="mono" style={{ fontSize: 12 }}>{g.estab}-{g.pto_emi}-{g.secuencial}</td>
                    <td>{g.dest_name}<div className="tag mono">{g.dest_id}</div></td>
                    <td className="mono">{g.placa}</td>
                    <td className="mono" style={{ fontSize: 11 }}>{g.fecha_ini_transporte} → {g.fecha_fin_transporte}</td>
                    <td><span className={`pill ${einvoiceStatusClass(g.status)}`}>{g.status}</span></td>
                    <td>
                      <div className="actions">
                        {g.status !== "AUTHORIZED" && canWrite ? (
                          <button className="btn" disabled={busy} onClick={() => act(() => authorizeWaybill(g.id, "AUTHORIZE"))}>Autorizar</button>
                        ) : null}
                        <button className="btn ghost" disabled={busy} onClick={() => xml(g)}>XML</button>
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
