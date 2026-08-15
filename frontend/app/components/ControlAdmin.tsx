"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  createControlAuthority,
  createControlDocument,
  createLegalInstrument,
  createRestriction,
  deleteLegalInstrument,
  deleteRestriction,
} from "@/app/lib/actions";

interface Legal { id: string; kind: string; number: string; organism?: string | null; registro_oficial?: string | null }
interface Authority { id: string; code: string; name: string }
interface Doc { id: string; code: string; name: string; authority_id?: string | null }
interface Restriction {
  id: string; hs_prefix: string; kind: string; control_document_id?: string | null;
  authority_id?: string | null; requirement?: string | null; verification_status: string;
}

export function ControlAdmin({
  legalInstruments = [], authorities = [], documents = [], restrictions = [],
}: {
  legalInstruments?: Legal[]; authorities?: Authority[]; documents?: Doc[]; restrictions?: Restriction[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const refresh = () => router.refresh();
  const run = async (fn: () => Promise<{ ok: boolean; error?: string }>) => {
    setBusy(true);
    try { const r = await fn(); if (!r.ok) alert(r.error); else refresh(); } finally { setBusy(false); }
  };

  const [li, setLi] = useState({ kind: "RESOLUCION_COMEX", number: "", organism: "", registro_oficial: "" });
  const [au, setAu] = useState({ code: "", name: "" });
  const [dc, setDc] = useState({ code: "", name: "", authority_id: "" });
  const [rx, setRx] = useState({ hs_prefix: "", kind: "CONTROL_PREVIO", control_document_id: "", authority_id: "", requirement: "", effective_from: "" });

  const docName = (id?: string | null) => documents.find((d) => d.id === id)?.name ?? "—";
  const authName = (id?: string | null) => authorities.find((a) => a.id === id)?.name ?? "—";

  return (
    <div className="card rise section-gap">
      <div className="head"><h2>Base legal y control previo</h2></div>

      {/* Normas */}
      <div className="eyebrow" style={{ marginTop: 8 }}>Normas (resoluciones / decretos / Registro Oficial)</div>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 8 }}>
        <label className="field"><span>Tipo</span><input value={li.kind} onChange={(e) => setLi((p) => ({ ...p, kind: e.target.value }))} style={{ width: 150 }} /></label>
        <label className="field"><span>Número</span><input value={li.number} placeholder="002-2023" onChange={(e) => setLi((p) => ({ ...p, number: e.target.value }))} style={{ width: 110 }} /></label>
        <label className="field"><span>Organismo</span><input value={li.organism} onChange={(e) => setLi((p) => ({ ...p, organism: e.target.value }))} style={{ width: 120 }} /></label>
        <label className="field"><span>Registro Oficial</span><input value={li.registro_oficial} onChange={(e) => setLi((p) => ({ ...p, registro_oficial: e.target.value }))} style={{ width: 120 }} /></label>
        <button className="btn" disabled={busy || !li.number.trim()} onClick={() => run(() => createLegalInstrument({ ...li, organism: li.organism || null, registro_oficial: li.registro_oficial || null }))}>Agregar norma</button>
      </div>
      {legalInstruments.length ? (
        <div style={{ marginTop: 6, fontSize: 12, color: "var(--muted)" }}>
          {legalInstruments.map((x) => (
            <span key={x.id} style={{ display: "inline-block", marginRight: 10 }}>
              <span className="mono">{x.kind} {x.number}</span>
              <button className="btn ghost" style={{ marginLeft: 4, padding: "0 6px" }} disabled={busy} onClick={() => run(() => deleteLegalInstrument(x.id))}>✕</button>
            </span>
          ))}
        </div>
      ) : null}

      {/* Entidades + documentos */}
      <div className="grid2" style={{ marginTop: 14 }}>
        <div>
          <div className="eyebrow">Entidades de control</div>
          <div className="form-row" style={{ alignItems: "flex-end", gap: 8 }}>
            <label className="field"><span>Código</span><input value={au.code} placeholder="ARCSA" onChange={(e) => setAu((p) => ({ ...p, code: e.target.value }))} style={{ width: 90 }} /></label>
            <label className="field"><span>Nombre</span><input value={au.name} onChange={(e) => setAu((p) => ({ ...p, name: e.target.value }))} /></label>
            <button className="btn" disabled={busy || !au.code.trim()} onClick={() => run(() => createControlAuthority(au))}>+</button>
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{authorities.map((a) => a.code).join(", ") || "—"}</div>
        </div>
        <div>
          <div className="eyebrow">Documentos de control</div>
          <div className="form-row" style={{ alignItems: "flex-end", gap: 8 }}>
            <label className="field"><span>Código</span><input value={dc.code} onChange={(e) => setDc((p) => ({ ...p, code: e.target.value }))} style={{ width: 90 }} /></label>
            <label className="field"><span>Nombre</span><input value={dc.name} onChange={(e) => setDc((p) => ({ ...p, name: e.target.value }))} /></label>
            <label className="field"><span>Entidad</span>
              <select value={dc.authority_id} onChange={(e) => setDc((p) => ({ ...p, authority_id: e.target.value }))}>
                <option value="">—</option>{authorities.map((a) => <option key={a.id} value={a.id}>{a.code}</option>)}
              </select>
            </label>
            <button className="btn" disabled={busy || !dc.code.trim()} onClick={() => run(() => createControlDocument({ ...dc, authority_id: dc.authority_id || null }))}>+</button>
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{documents.map((d) => d.code).join(", ") || "—"}</div>
        </div>
      </div>

      {/* Restricciones */}
      <div className="eyebrow" style={{ marginTop: 14 }}>Restricciones por subpartida</div>
      <div className="form-row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: 8 }}>
        <label className="field"><span>Prefijo HS</span><input value={rx.hs_prefix} onChange={(e) => setRx((p) => ({ ...p, hs_prefix: e.target.value }))} style={{ width: 100 }} /></label>
        <label className="field"><span>Tipo</span>
          <select value={rx.kind} onChange={(e) => setRx((p) => ({ ...p, kind: e.target.value }))}>
            <option value="CONTROL_PREVIO">Control previo</option><option value="RESTRICCION">Restricción</option><option value="PROHIBICION">Prohibición</option>
          </select>
        </label>
        <label className="field"><span>Documento</span>
          <select value={rx.control_document_id} onChange={(e) => setRx((p) => ({ ...p, control_document_id: e.target.value }))}>
            <option value="">—</option>{documents.map((d) => <option key={d.id} value={d.id}>{d.code}</option>)}
          </select>
        </label>
        <label className="field"><span>Entidad</span>
          <select value={rx.authority_id} onChange={(e) => setRx((p) => ({ ...p, authority_id: e.target.value }))}>
            <option value="">—</option>{authorities.map((a) => <option key={a.id} value={a.id}>{a.code}</option>)}
          </select>
        </label>
        <label className="field" style={{ minWidth: 160 }}><span>Requisito</span><input value={rx.requirement} onChange={(e) => setRx((p) => ({ ...p, requirement: e.target.value }))} /></label>
        <label className="field"><span>Desde</span><input type="date" value={rx.effective_from} onChange={(e) => setRx((p) => ({ ...p, effective_from: e.target.value }))} /></label>
        <button className="btn" disabled={busy || !rx.hs_prefix.trim() || !rx.effective_from} onClick={() => run(() => createRestriction({ ...rx, control_document_id: rx.control_document_id || null, authority_id: rx.authority_id || null, requirement: rx.requirement || null }))}>Agregar</button>
      </div>
      {restrictions.length ? (
        <div style={{ marginTop: 10, overflowX: "auto" }}>
          <table className="tbl" style={{ width: "100%" }}>
            <thead><tr><th>Prefijo</th><th>Tipo</th><th>Documento</th><th>Entidad</th><th>Requisito</th><th></th></tr></thead>
            <tbody>
              {restrictions.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.hs_prefix}</td>
                  <td>{r.kind}</td>
                  <td>{docName(r.control_document_id)}</td>
                  <td>{authName(r.authority_id)}</td>
                  <td style={{ fontSize: 12, color: "var(--muted)" }}>{r.requirement || "—"}</td>
                  <td><button className="btn ghost" disabled={busy} onClick={() => run(() => deleteRestriction(r.id))}>✕</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
